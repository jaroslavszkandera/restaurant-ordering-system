from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .views import logout_view
from .views import branch_schedule

urlpatterns = [
    # Main pages
    path("", views.index, name="index"),
    path("menu/", views.menu, name="menu"),
    path("menu/category/<str:category_id>/", views.menu, name="menu_category"),
    # Cart and checkout
    path("cart/add/", views.add_to_cart, name="add_to_cart"),
    path("cart/", views.view_cart, name="view_cart"),
    path("cart/add-random/", views.add_random_to_cart, name="add_random_to_cart"),
    path(
        "cart/update_and_checkout/",
        views.update_cart_and_checkout,
        name="update_cart_and_checkout",
    ),
    path("checkout/", views.checkout, name="checkout"),
    # Orders
    path('get_available_order_slots/', views.get_available_order_slots, name='get_available_order_slots'),
    path("order/<int:order_id>/", views.order_detail, name="order_detail"),
    path(
        "order/<int:order_id>/confirmation/",
        views.order_confirmation,
        name="order_confirmation",
    ),
    path("orders/history/", views.order_history, name="order_history"),
    # Authentication
    path("register/", views.register, name="register"),
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", logout_view, name="logout"),
    path('contact/', views.contact_view, name='contact'),
    path('reservation/', views.reservation, name='reservation'),
    path('reservation/confirmation/<int:id>/', views.reservation_confirmation, name='reservation_confirmation'),
    path('api/fetch_time_slots/', views.fetch_available_time_slots, name='fetch_time_slots'),
    path('branch_schedule/', branch_schedule, name='branch_schedule'),
    path("reorder/<int:order_id>/", views.reorder_view, name="reorder"),
    path("check-cart/", views.check_cart_empty, name="check_cart_empty"),
    path("reservation/history/", views.reservation_history, name="reservation_history"),
    path("reservation/<int:reservation_id>/", views.reservation_detail, name="reservation_detail"),
]
