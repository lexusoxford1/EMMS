"""Authentication-related helper functions."""


def is_admin(user):
    """Return True when the supplied user should be treated as an administrator."""
    """Treat Django superusers as the admin role for this project."""
    return user.is_superuser


