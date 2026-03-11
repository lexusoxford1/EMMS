"""Authentication-related helper functions."""


def is_admin(user):
    """Treat Django superusers as the admin role for this project."""
    return user.is_superuser
