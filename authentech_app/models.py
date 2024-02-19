# authentech_app/models.py
from django.db import models
from django.contrib.auth.models import User
import uuid

from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    # Link to the User model with additional user information
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    preferred_name = models.CharField(max_length=100)


class EmailVerificationToken(models.Model):
    # Represents an email verification token for a user
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)


class WebAuthnCredential(models.Model):
    # Stores WebAuthn credentials for user authentication
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    credential_id = models.BinaryField(unique=True)
    public_key = models.BinaryField()
    sign_count = models.IntegerField()


@receiver(post_save, sender=UserProfile)
def update_votable_creator_name(sender, instance, **kwargs):
    from discussable_app.models import Discussion, Comment  # Import here to avoid circular import
    Discussion.objects.filter(creator=instance.user).update(creator_name=instance.preferred_name)
    Comment.objects.filter(creator=instance.user).update(creator_name=instance.preferred_name)
