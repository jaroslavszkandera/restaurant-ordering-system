from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("order/<int:order_id>/", views.order_detail, name="order_detail"),
    path("menu/", views.order_menu, name="order_menu"),
]
