"""
URL configuration for crm project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
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
from django.urls import path, include

from . import views

urlpatterns = [
    path('', views.swarm_info, name='swarm_info'),
    path('admin/', admin.site.urls),
    path('customers/', include('customers.urls')),
    path('accounts/', include('accounts.urls')),
    path('departments/', include('departments.urls')),
    path('employees/', include('employees.urls')),
    path('organizations/', include('organizations.urls')),
    path('positions/', include('positions.urls')),
    path('units/', include('units.urls')),
    path('proxies/', include('proxies.urls')),
    path('products/', include('products.urls')),
    path('brigadiers/', include('brigadiers.urls')),
    path('nariad/', include('nariad.urls')),
    path('dropbox/', include('cloud_storage.urls')),
    path('journal/', include('activity_log.urls')),
]
