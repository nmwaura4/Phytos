from django.urls import include, path
from rest_framework import routers

from phytoseilus.views import ReceivedPredatorViewSet

router = routers.DefaultRouter()
router.register(
    r'received-predators',
    ReceivedPredatorViewSet,
    basename='received-predator',
)

urlpatterns = [
    path('', include(router.urls)),
]
