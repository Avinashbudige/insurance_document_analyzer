from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DocumentViewSet, ExtractedEntityViewSet

router = DefaultRouter()
router.register(r'documents', DocumentViewSet, basename='document')
router.register(r'entities', ExtractedEntityViewSet, basename='entity')

urlpatterns = [
    path('', include(router.urls)),
]