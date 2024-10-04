# urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProjectViewSet

# Create a router and register the ProjectViewSet
router = DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='project')

# Include the router's URLs in the urlpatterns
urlpatterns = [
    path('', include(router.urls)),
]
