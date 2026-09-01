from django.urls import path

from . import views

urlpatterns = [
    path("", views.search_farmers, name="search_farmers"),
    path("<str:gl_client_id>/", views.get_farmer, name="get_farmer"),
    path("<str:gl_client_id>/journey/", views.get_journey, name="get_journey"),
]
