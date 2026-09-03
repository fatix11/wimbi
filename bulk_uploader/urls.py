from django.urls import path

from . import views

urlpatterns = [
    path("", views.dataset_list, name="dataset_list"),
    path("new/", views.upload_new, name="upload_new"),
    path("<int:pk>/edit/", views.dataset_edit, name="dataset_edit"),
    path("<int:pk>/map/", views.dataset_map, name="dataset_map"),
    path("<int:pk>/preview/", views.dataset_preview, name="dataset_preview"),
]
