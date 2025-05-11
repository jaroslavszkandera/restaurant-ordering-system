from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Customer, Order, MenuItem


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ["name", "phone", "email"]


class AddToCartForm(forms.Form):
    quantity = forms.IntegerField(
        min_value=1,
        max_value=10,
        initial=1,
        widget=forms.NumberInput(attrs={"class": "form-control quantity-input"}),
    )
    menu_item_id = forms.IntegerField(widget=forms.HiddenInput())


class CartUpdateForm(forms.Form):
    quantity = forms.IntegerField(
        min_value=0,  # 0 to remove item from cart
        max_value=10,
        widget=forms.NumberInput(attrs={"class": "form-control quantity-input"}),
    )
    cart_item_id = forms.IntegerField(widget=forms.HiddenInput())


class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["special_instructions"]
        widgets = {
            "special_instructions": forms.Textarea(
                attrs={"rows": 3, "placeholder": "Any special requests or allergies?"}
            ),
        }

    # If guest checkout
    name = forms.CharField(max_length=100, required=False)
    phone = forms.CharField(max_length=20, required=False)
    email = forms.EmailField(required=False)

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # If user is authenticated, pre-fill customer information
        if user and not user.is_anonymous:
            try:
                customer = user.customer
                self.fields["name"].initial = customer.name
                self.fields["phone"].initial = customer.phone
                self.fields["email"].initial = customer.email

                # Hide these fields if we already have customer data
                self.fields["name"].widget = forms.HiddenInput()
                self.fields["phone"].widget = forms.HiddenInput()
                self.fields["email"].widget = forms.HiddenInput()
            except:
                pass
