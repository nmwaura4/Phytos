from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from phytoseilus.auth import create_user, get_user_by_email

User = get_user_model()


class RegistrationForm(forms.Form):
    email = forms.EmailField(
        label="Email address",
        widget=forms.EmailInput(attrs={"autocomplete": "email", "autofocus": True}),
    )
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    password_confirm = forms.CharField(
        label="Confirm password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    def clean_email(self):
        email = User.objects.normalize_email(self.cleaned_data["email"].strip())
        if (
            User.objects.filter(email__iexact=email).exists()
            or User.objects.filter(username__iexact=email).exists()
        ):
            raise ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")
        email = cleaned_data.get("email")

        if password and password_confirm and password != password_confirm:
            self.add_error("password_confirm", "The passwords do not match.")

        if password and email:
            candidate = User(username=email, email=email)
            try:
                validate_password(password, user=candidate)
            except ValidationError as error:
                self.add_error("password", error)

        return cleaned_data

    def save(self):
        return create_user(
            self.cleaned_data["email"],
            self.cleaned_data["password"],
        )


class EmailLoginForm(forms.Form):
    email = forms.EmailField(
        label="Email address",
        widget=forms.EmailInput(attrs={"autocomplete": "email", "autofocus": True}),
    )
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    def __init__(self, *args, request=None, **kwargs):
        self.request = request
        self.user = None
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        password = cleaned_data.get("password")

        if email and password:
            email = User.objects.normalize_email(email.strip())
            user_record = get_user_by_email(email)
            if user_record is not None:
                self.user = authenticate(
                    request=self.request,
                    username=user_record.get_username(),
                    password=password,
                )

            if self.user is None:
                raise ValidationError("Email or password is incorrect.")

        return cleaned_data

    def get_user(self):
        return self.user
