from django.urls import path
from star_ratings.views import Rate

app_name = 'ratings'
urlpatterns = [
    path('<int:content_type_id>/<uuid:object_id>/', view=Rate.as_view(), name='rate'),
]
