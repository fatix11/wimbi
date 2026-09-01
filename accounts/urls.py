from django.urls import path

from . import views

urlpatterns = [
    path("dev-users/", views.list_dev_users, name="list_dev_users"),
    path("login/", views.login, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("me/", views.me, name="me"),
]
