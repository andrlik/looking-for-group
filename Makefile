TAG_TO_USE=master
WORKERS=4
PYEXEC="poetry run"
ifneq ($(PYCOMMAND),)
	PYEXEC="$(PYCOMMAND)"
endif

.PHONY: help prep_static ace_test test devserver shell web worker amis
.DEFAULT_GOAL := help

install_dev_deps: package-lock.json package.json poetry.lock ## Install development AND production requirements using poetry
	@echo "Installing development python requirements..."; poetry install
	@echo "Installing development node requirements..."; npm install

install_prod_deps: package-lock.json package.json poetry.lock ## Only install production dependencies
	@echo "Installing production python requirements..."; poetry install --no-dev
	@echo "Installing production node requirements..."; npm install --only-prod
	@npm prune --production

prep_static: ## Collect and compress static files accordingly (uses poetry)
	@echo "Running initial collect static..."; "$(PYEXEC)" ./manage.py collectstatic --noinput
	@echo "Compressing static blocks..."; "$(PYEXEC)" ./manage.py compress --force
	@echo "Running collect static again to grab compressed blocks..."; "$(PYEXEC)" ./manage.py collectstatic --noinput

ace_test: ## Run accessiblity tests
	@echo "Running accessibility tests..."; "$(PYEXEC)" pytest -n $(WORKERS) --a11y --driver=Firefox

test: ## Run non-accessiblity tests
	@echo "Running test suite..."; "$(PYEXEC)" pytest -n $(WORKERS)

devserver: ## Run development server
	@echo "Running development server..."; poetry run npm run dev

prodserver: ## Run production server using waitress
	@echo "Starting production server using waitress..."; "$(PYEXEC)" config/run.py

qcluster: ## Run the django_q worker cluster
	@echo "Starting workers with django_q..."; "$(PYEXEC)" ./manage.py qcluster

shell: ## Load python shell
	@echo "Loading interactive python shell..."; "$(PYEXEC)" ./manage.py shell_plus

db: ## Load DB Shell
	@echo "Connecting to DB shell..."; "$(PYEXEC)" ./manage.py dbshell

migrations: ## Make any migration files for schema changes
	@echo "Creating migration files..."; "$(PYEXEC)" ./manage.py makemigrations

migrate: ## Apply any pending migrations
	@echo "Applying pending migrations..."; "$(PYEXEC)" ./manage.py migrate

web: ## Build a web ami image
	@cd packerscripts; packer build -var "tag_to_use=${TAG_TO_USE}" web-template.json

worker: ## Build a worker ami image
	@cd packerscripts; packer build -var "tag_to_use=${TAG_TO_USE}" worker-template.json

amis: web worker ## Build both a web and worker image

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
