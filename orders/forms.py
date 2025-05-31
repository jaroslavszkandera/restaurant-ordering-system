from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Customer, Order, Reservation
import re
from orders.models import Branch

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(
        required=True, help_text="Required. Will be used for communication."
    )
    first_name = forms.CharField(max_length=30, required=False, help_text="Optional.")
    last_name = forms.CharField(max_length=150, required=False, help_text="Optional.")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + (
            "first_name",
            "last_name",
            "email",
        )

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
        min_value=0,  
        max_value=10,
        widget=forms.NumberInput(attrs={"class": "form-control quantity-input"}),
    )
    cart_item_id = forms.IntegerField(widget=forms.HiddenInput())


class CheckoutForm(forms.ModelForm):
    name = forms.CharField(
        max_length=100,
        required=True,
        min_length=2,
        error_messages={
            'required': 'Please enter your name.',
            'min_length': 'Name must be at least 2 characters.',
        },
        widget=forms.TextInput(attrs={
            "placeholder": "Full Name",
            "class": "form-control",
        }),
    )

    email = forms.EmailField(
        required=True,
        error_messages={
            'required': 'Please enter your email address.',
            'invalid': 'Enter a valid email address.',
        },
        widget=forms.EmailInput(attrs={
            "placeholder": "Email Address",
            "class": "form-control",
        }),
    )

    phone = forms.CharField(
        required=True,
        max_length=10,
        min_length=10,
        error_messages={
            'required': 'Please enter your phone number.',
            'min_length': 'Phone number must be exactly 10 digits.',
            'max_length': 'Phone number must be exactly 10 digits.',
        },
        widget=forms.TextInput(attrs={
            "placeholder": "Phone Number",
            "class": "form-control",
        }),
    )

    pickup_branch = forms.ModelChoiceField(
        queryset=Branch.objects.filter(is_orderable=True),
        required=True,
        empty_label="Select a pickup location",
        label="Pickup Branch",
        widget=forms.Select(attrs={
            "class": "dropdown-original d-none",  
        }),
        error_messages={
            "required": "Please select a pickup location.",
        },
    )

    class Meta:
        model = Order
        fields = ["special_instructions"]
        widgets = {
            "special_instructions": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "Any special requests or allergies?",
                "class": "form-control",
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if self.user and self.user.is_authenticated:
            customer = getattr(self.user, "customer", None)
            self.fields["name"].initial = (
                customer.name if customer and customer.name else self.user.get_full_name() or self.user.username
            )
            self.fields["email"].initial = (
                customer.email if customer and customer.email else self.user.email
            )
            self.fields["phone"].initial = (
                customer.phone if customer and customer.phone else ""
            )

    def clean_phone(self):
        phone = self.cleaned_data.get("phone")
        if not phone:
            raise forms.ValidationError("Please enter your phone number.")
        if not re.match(r'^\d{10}$', phone):
            raise forms.ValidationError("Phone number must be exactly 10 digits.")
        return phone

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if not email:
            raise forms.ValidationError("Please enter your email address.")
        return email

    def clean_name(self):
        name = self.cleaned_data.get("name")
        if not name:
            raise forms.ValidationError("Please enter your name.")
        if len(name) < 2:
            raise forms.ValidationError("Name must be at least 2 characters.")
        return name

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data

class ContactForm(forms.Form):
    name = forms.CharField(min_length=2, required=True, error_messages={'required': 'Please enter your name.', 'min_length': 'Name must be at least 2 characters.'})
    email = forms.EmailField(required=True, error_messages={'required': 'Please enter your email.', 'invalid': 'Enter a valid email address.'})
    phone = forms.CharField(required=False, max_length=10, min_length=10, error_messages={'min_length': 'Phone number must be exactly 10 digits.', 'max_length': 'Phone number must be exactly 10 digits.'})
    mobile = forms.CharField(required=True, max_length=10, min_length=10, error_messages={'required': 'Please enter your mobile number.', 'min_length': 'Mobile number must be exactly 10 digits.', 'max_length': 'Mobile number must be exactly 10 digits.'})
    message = forms.CharField(widget=forms.Textarea, min_length=10, required=True, error_messages={'required': 'Please enter your message.', 'min_length': 'Message must be at least 10 characters.'})

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '')
        if phone and not re.match(r'^[0-9]{10}$', phone):
            raise forms.ValidationError('Phone number must be exactly 10 digits.')
        return phone

    def clean_mobile(self):
        mobile = self.cleaned_data.get('mobile', '')
        if not re.match(r'^[0-9]{10}$', mobile):
            raise forms.ValidationError('Mobile number must be exactly 10 digits.')
        return mobile

class ReservationForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = ['guests', 'date', 'branch', 'time_slot', 'name', 'mobile', 'email']