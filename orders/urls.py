from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Main pages
    path("", views.index, name="index"),
    path("about", views.about, name="about"),
    path("contact", views.contact, name="contact"),
    path("menu/", views.menu, name="menu"),
    path("menu/category/<int:category_id>/", views.menu, name="menu_category"),
    # Cart and checkout
    path("cart/add/", views.add_to_cart, name="add_to_cart"),
    path("cart/", views.view_cart, name="view_cart"),
    path(
        "cart/update_and_checkout/",
        views.update_cart_and_checkout,
        name="update_cart_and_checkout",
    ),
    path("checkout/", views.checkout, name="checkout"),
    # Orders
    path("order/<int:order_id>/", views.order_detail, name="order_detail"),
    path(
        "order/<int:order_id>/confirmation/",
        views.order_confirmation,
        name="order_confirmation",
    ),
    path("orders/history/", views.order_history, name="order_history"),
    # Authentication
    path("register/", views.register, name="register"),
    path(
        "login/",
        auth_views.LoginView.as_view(),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(next_page="index"), name="logout"),
]
