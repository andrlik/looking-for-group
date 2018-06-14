from rest_framework.routers import DefaultRouter
from looking_for_group.game_catalog import api_views as catalog_api_views


# API Router
router = DefaultRouter()
router.register(r'catalog/publishers', catalog_api_views.GamePublisherViewSet, base_name='api-publisher')
router.register(r'catalog/systems', catalog_api_views.GameSystemViewSet, base_name='api-system')
router.register(r'catalog/publishedgames', catalog_api_views.PublishedGameViewSet, base_name='api-publishedgame')
router.register(r'catalog/publishedmodules', catalog_api_views.PublishedModuleViewSet, base_name='api-publishedmodule')
