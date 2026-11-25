from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from rest_framework_simplejwt.tokens import RefreshToken


def _normalize_email(email: str) -> str:
    """Trim whitespace and normalize the email domain consistently."""
    return User.objects.normalize_email(email.strip())


def _account_exists(email: str) -> bool:
    """Check both fields because the default User model doesn't unique email."""
    return (
        User.objects.filter(email__iexact=email).exists()
        or User.objects.filter(username__iexact=email).exists()
    )


def create_user(email: str, password: str) -> User:
    """Create a user whose username is their email, validating before saving.

    Raises ValueError for missing or already-used email addresses and Django's
    ValidationError when the email or password fails validation.
    """
    normalized_email = _normalize_email(email)
    if not normalized_email:
        raise ValueError("An email address is required.")
    if not password:
        raise ValueError("A password is required.")

    validate_email(normalized_email)
    if _account_exists(normalized_email):
        raise ValueError("An account with this email already exists.")

    candidate = User(username=normalized_email, email=normalized_email)
    validate_password(password, user=candidate)

    try:
        with transaction.atomic():
            return User.objects.create_user(
                username=normalized_email,
                email=normalized_email,
                password=password,
            )
    except IntegrityError as error:
        # The username uniqueness constraint also protects concurrent signups.
        if _account_exists(normalized_email):
            raise ValueError("An account with this email already exists.") from error
        raise


def get_user_by_email(email: str) -> User | None:
    """Return the unique matching user, or None if absent/ambiguous."""
    normalized_email = _normalize_email(email)
    if not normalized_email:
        return None

    try:
        return User.objects.get(email__iexact=normalized_email)
    except (User.DoesNotExist, User.MultipleObjectsReturned):
        return None


def require_authentication(email: str, password: str) -> dict[str, str] | None:
    """Authenticate by email and return a Simple JWT token pair on success."""
    user_record = get_user_by_email(email)
    if user_record is None or not user_record.is_active:
        return None

    user = authenticate(username=user_record.get_username(), password=password)
    if user is None:
        return None

    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }