"""
URL configuration for drug_box project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, re_path
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from box.views import AddUserFromDeviceAPIView, HandleRequestAPIView

# Swagger schema configuration
schema_view = get_schema_view(
    openapi.Info(
        title="Drug Box API",
        default_version='v1',
        description="Interactive API documentation for Drug Box Management System",
        terms_of_service="https://drug-box.com/terms/",
        contact=openapi.Contact(email="farid@gmail.com"),
        license=openapi.License(name="AUT License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/add-user/', AddUserFromDeviceAPIView.as_view(), name='add-user'),
    path('api/v1/handle-request/', HandleRequestAPIView.as_view(), name='handle-request'),

    # Swagger docs routes
    re_path(r'^swagger(?P<format>\.json|\.yaml)$',
            schema_view.without_ui(cache_timeout=0),
            name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0),
         name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0),
         name='schema-redoc'),
]
