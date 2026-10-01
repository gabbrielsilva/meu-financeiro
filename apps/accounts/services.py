from django.contrib.auth import get_user_model
from django.db import transaction
from apps.categories.defaults import create_defaults


@transaction.atomic
def register_user(email, password):
    user = get_user_model().objects.create_user(email=email, password=password)
    create_defaults(user)
    return user
