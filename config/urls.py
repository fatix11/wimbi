"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
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
from django.urls import include, path
from django.views.generic.base import RedirectView

from accounts import views as account_views
from farmers import views as farmer_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
    path('api/farmers/', include('farmers.urls')),

    # HTML pages (ADR-010) — additive to the JSON API above, same views'
    # underlying RBAC/session helpers, server-rendered + HTMX instead of JSON.
    path('', RedirectView.as_view(pattern_name='dashboard_page', permanent=False)),
    path('login/', account_views.login_page, name='login_page'),
    path('logout/', account_views.logout_page, name='logout_page'),
    path('dashboard/', farmer_views.dashboard_page, name='dashboard_page'),
    path('search/', farmer_views.search_page, name='search_page'),
    path('farmers/<str:gl_client_id>/', farmer_views.farmer_profile_page, name='farmer_profile_page'),
    path('farmers/<str:gl_client_id>/journey/', farmer_views.journey_partial, name='journey_partial'),
    path('farmers/<str:gl_client_id>/sales/', farmer_views.sales_partial, name='sales_partial'),
    path('uploads/', include('bulk_uploader.urls')),
]
