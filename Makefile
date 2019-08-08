TAG_TO_USE=master
WORKERS=4

.PHONY: help prep_static ace_test test devserver shell web worker amis
.DEFAULT_GOAL := help

install_dev_deps: package-lock.json package.json poetry.lock ## Install development AND production requirements using poetry
	@poetry install
	@npm install

install_prod_deps: package-lock.json package.json poetry.lock ## Only install production dependencies
	@poetry install --no-dev
	@npm install --only-prod
	@npm prune --production

prep_static: ## Collect and compress static files accordingly (uses poetry)
	@poetry run ./manage.py collectstatic --noinput
	@poetry run ./manage.py compress --force
	@poetry run ./manage.py collectstatic --noinput

ace_test: ## Run accessiblity tests
	@poetry run pytest -n $(WORKERS) --a11y --driver=Firefox

test: ## Run non-accessiblity tests
	@poetry run pytest -n $(WORKERS)

devserver: ## Run development server
	@poetry run npm run dev

shell: ## Load python shell
	@poetry run ./manage.py shell_plus

web: ## Build a web ami image
	@cd utility/packerscripts
	@packer build -var "tag_to_use=${TAG_TO_USE}" web-template.json
	@cd ../../

worker: ## Build a worker ami image
	@cd utility/packerscripts
	@packer build -var "tag_to_use=${TAG_TO_USE}" worker-template.json
	@cd ../../

amis: web worker ## Build both a web and worker image

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
