from django import forms
from django.contrib.auth import authenticate
from decimal import Decimal, ROUND_HALF_UP

from .models import Bill, Budget, CustomUser, Expense, Income


class RegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = CustomUser
        fields = ["name", "email", "password", "confirm_password"]

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password") != cleaned.get("confirm_password"):
            raise forms.ValidationError("Passwords do not match.")
        return cleaned

    def save(self, commit=True):
        user = CustomUser(name=self.cleaned_data["name"], email=self.cleaned_data["email"])
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        cleaned = super().clean()
        email = cleaned.get("email")
        password = cleaned.get("password")
        if email and password:
            user = authenticate(username=email, password=password)
            if not user:
                raise forms.ValidationError("Invalid email or password.")
            cleaned["user"] = user
        return cleaned


class IncomeForm(forms.ModelForm):
    class Meta:
        model = Income
        fields = ["source", "amount", "date"]
        widgets = {
            "amount": forms.TextInput(attrs={"inputmode": "decimal", "autocomplete": "off"}),
            "date": forms.DateInput(attrs={"type": "date"}),
        }

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        return amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ["name", "amount", "category", "date"]
        widgets = {
            "amount": forms.TextInput(attrs={"inputmode": "decimal", "autocomplete": "off"}),
            "date": forms.DateInput(attrs={"type": "date"}),
        }

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        return amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


class BillForm(forms.ModelForm):
    class Meta:
        model = Bill
        fields = ["name", "service", "amount", "due_date", "category", "is_recurring"]
        widgets = {
            "amount": forms.TextInput(attrs={"inputmode": "decimal", "autocomplete": "off"}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
        }

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        return amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


class BudgetForm(forms.ModelForm):
    class Meta:
        model = Budget
        fields = ["category", "amount", "month"]
        widgets = {
            "amount": forms.TextInput(attrs={"inputmode": "decimal", "autocomplete": "off"}),
            "month": forms.DateInput(attrs={"type": "month"}),
        }

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        return amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


class ProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ["name", "email"]
