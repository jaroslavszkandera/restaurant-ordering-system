from django import forms
from .models import MenuItem, Customer, Order


class OrderForm(forms.Form):
    name = forms.CharField(max_length=100, label="Your Name")
    phone = forms.CharField(max_length=15, label="Phone Number")
    items = forms.ModelMultipleChoiceField(
        queryset=MenuItem.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label="Select Menu Items",
    )
