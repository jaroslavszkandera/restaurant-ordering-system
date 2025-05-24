from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Customer, Order, MenuItem


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField()

    # FIX:
    # "Meta" overrides symbol of same name in class "BaseUserCreationForm"
    #  "orders.forms.UserRegistrationForm.Meta" is not assignable to "django.contrib.auth.forms.BaseUserCreationForm.Meta"
    class Meta:
        model = User
        fields = ["username", "email", "password", "password2"]


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ["name", "phone", "email"]


class AddToCartForm(forms.Form):
    quantity = forms.IntegerField(
        min_value=1,
        max_value=25,
        initial=1,
        widget=forms.NumberInput(attrs={"class": "form-control quantity-input"}),
    )
    menu_item_id = forms.IntegerField(widget=forms.HiddenInput())


class CartUpdateForm(forms.Form):
    quantity = forms.IntegerField(
        min_value=0,  # 0 to remove item from cart
        max_value=25,
        widget=forms.NumberInput(attrs={"class": "form-control quantity-input"}),
    )
    cart_item_id = forms.IntegerField(widget=forms.HiddenInput())


class CheckoutForm(forms.ModelForm):
    name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Full Name"}),
    )
    email = forms.EmailField(
        required=False, widget=forms.EmailInput(attrs={"placeholder": "Email Address"})
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Phone Number"}),
    )

    class Meta:
        model = Order
        fields = ["special_instructions"]
        widgets = {
            "special_instructions": forms.Textarea(
                attrs={"rows": 3, "placeholder": "Any special requests or allergies?"}
            ),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)  # User passed from the view
        super().__init__(*args, **kwargs)

        if self.user and self.user.is_authenticated:
            customer = getattr(self.user, "customer", None)
            if customer:
                self.fields["name"].initial = customer.name
                self.fields["email"].initial = customer.email
                self.fields["phone"].initial = customer.phone
            else:  # admin
                self.fields["name"].initial = (
                    self.user.get_full_name() or self.user.username
                )
                self.fields["email"].initial = self.user.email
            # optional fields with authenticated users?
            # self.fields["name"].required = False
            # self.fields["email"].required = False
            # self.fields["phone"].required = False
        else:  # guest users
            self.fields["name"].required = True
            self.fields["email"].required = True
            self.fields["phone"].required = True

    def clean(self):
        cleaned_data = super().clean()
        if not (self.user and self.user.is_authenticated):
            if not cleaned_data.get("name"):
                self.add_error("name", "This field is required for guest checkout.")
            if not cleaned_data.get("email"):
                self.add_error("email", "This field is required for guest checkout.")
            if not cleaned_data.get("phone"):
                self.add_error("phone", "This field is required for guest checkout.")
        return cleaned_data

    """
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
    """
