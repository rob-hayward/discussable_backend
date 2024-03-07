# discussable_app/models.py

from django.db import models
from django.contrib.auth.models import User
from enum import Enum
from django.db.models import Count
from math import sqrt
from django.db.models.functions import Greatest
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

from authentech_app.models import UserProfile


class VoteType(Enum):
    POSITIVE = 1
    NEGATIVE = -1
    NO_VOTE = 0

    @classmethod
    def choices(cls):
        return [(key.value, key.name) for key in cls]

    @classmethod
    def default(cls):
        return cls.NO_VOTE.value


class VotableType(Enum):
    DISCUSSION = "Discussion"
    COMMENT = "Comment"

    @classmethod
    def choices(cls):
        return [(key.value, key.name) for key in cls]


class VisibilityStatus(Enum):
    VISIBLE = "visible"
    HIDDEN = "hidden"
    @classmethod
    def choices(cls):
        return [(key.value, key.name) for key in cls]


class Votable(models.Model):
    creator = models.ForeignKey(User, on_delete=models.CASCADE)
    creator_name = models.CharField(max_length=100, blank=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    total_votes = models.PositiveIntegerField(default=0)
    positive_votes = models.PositiveIntegerField(default=0)
    negative_votes = models.PositiveIntegerField(default=0)
    participation_percentage = models.DecimalField(max_digits=3, decimal_places=0, default=0)
    positive_percentage = models.DecimalField(max_digits=3, decimal_places=0, default=0)
    negative_percentage = models.DecimalField(max_digits=3, decimal_places=0, default=0)
    wilson_score = models.DecimalField(max_digits=10, decimal_places=8, default=0.0)
    visibility_status = models.CharField(max_length=20, choices=VisibilityStatus.choices(), default=VisibilityStatus.VISIBLE.value)
    VISIBILITY_THRESHOLD = 33  # Approval percentage below which content is hidden

    class Meta:
        abstract = True

    def get_vote_data(self):
        content_type = ContentType.objects.get_for_model(self)
        vote_data = Vote.objects.filter(content_type=content_type, object_id=self.id).aggregate(
            positive_votes=Count('id', filter=models.Q(vote=VoteType.POSITIVE.value)),
            negative_votes=Count('id', filter=models.Q(vote=VoteType.NEGATIVE.value)),
        )
        positive_votes = vote_data['positive_votes']
        negative_votes = vote_data['negative_votes']
        total_votes = positive_votes + negative_votes
        total_users = User.objects.count()
        z = 1.96  # For 95% confidence
        phat = positive_votes / total_votes if total_votes > 0 else 0
        wilson_nominator = phat + (z ** 2) / (2 * total_votes) - z * sqrt(
            (phat * (1 - phat) + (z ** 2) / (4 * total_votes)) / total_votes)
        wilson_denominator = 1 + (z ** 2) / total_votes

        self.participation_percentage = round((total_votes / total_users) * 100) if total_users > 0 else 0
        self.positive_percentage = round((positive_votes / total_votes) * 100) if total_votes > 0 else 0
        self.negative_percentage = round((negative_votes / total_votes) * 100) if total_votes > 0 else 0
        self.total_votes = total_votes
        self.positive_votes = positive_votes
        self.negative_votes = negative_votes
        self.wilson_score = wilson_nominator / wilson_denominator
        # Determine visibility status based on approval percentage
        approval_percentage = self.positive_percentage
        if approval_percentage is not None and approval_percentage < Votable.VISIBILITY_THRESHOLD:
            self.visibility_status = VisibilityStatus.HIDDEN.value
        else:
            self.visibility_status = VisibilityStatus.VISIBLE.value

        self.save()

        vote_data = {
            'total_votes': total_votes,
            'positive_percentage': self.positive_percentage,
            'negative_percentage': self.negative_percentage,
            'participation_percentage': self.participation_percentage,
            'positive_votes': positive_votes,
            'negative_votes': negative_votes,
        }

        return vote_data

    def save(self, *args, **kwargs):
        # Logic to set visibility status based on votes
        if self.total_votes > 0:
            approval_percentage = (self.positive_votes / float(self.total_votes)) * 100
            self.visibility_status = VisibilityStatus.HIDDEN.value if approval_percentage < self.VISIBILITY_THRESHOLD else VisibilityStatus.VISIBLE.value
        else:
            self.visibility_status = VisibilityStatus.VISIBLE.value

        # Fetch the preferred_name from UserProfile and assign it to creator_name
        # This is done every time a Votable object is saved to ensure the creator_name is always up to date
        user_profile = UserProfile.objects.filter(user=self.creator).first()
        if user_profile:
            self.creator_name = user_profile.preferred_name

        # Call the parent class's save method with all provided arguments
        super().save(*args, **kwargs)

    def get_votes(self):
        return Vote.objects.filter(votable=self)

    def get_user_vote(self, user):
        try:
            vote = Vote.objects.get(votable=self, user=user)
            if vote.vote == VoteType.POSITIVE.value:
                return 'Positive'
            elif vote.vote == VoteType.NEGATIVE.value:
                return 'Negative'
            else:
                return 'No Vote'
        except Vote.DoesNotExist:
            return 'No Vote'

    @staticmethod
    def get_all_votables():
        return Votable.objects.all().order_by('-created_at')

    @staticmethod
    def get_votables_by_votes():
        return Votable.objects.all().order_by('-total_votes')

    @staticmethod
    def get_votables_by_consensus():
        # Use the `Greatest` function to determine the highest percentage
        votables = Votable.objects.annotate(
            percentage_agreement=Greatest('positive_percentage', 'negative_percentage')
        )
        # Order by percentage of agreement and then total votes
        return votables.order_by('-percentage_agreement', '-total_votes')

    @staticmethod
    def get_votables_by_popularity():
        return Votable.objects.all().order_by('-wilson_score')


class Vote(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    vote = models.IntegerField(choices=VoteType.choices(), default=VoteType.default())
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'content_type', 'object_id')


class Discussion(Votable):
    subject = models.CharField(max_length=255)
    category = models.CharField(max_length=50, blank=True, null=True)  # Optional category or tag field

    # Additional Discussion-specific methods can be added here

    def __str__(self):
        return f"{self.subject} - {self.category if self.category else 'General'}"


class Comment(Votable):
    discussion = models.ForeignKey(Discussion, on_delete=models.CASCADE, related_name='comments')
    comment_content = models.TextField(blank=True, null=False)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, related_name='replies', null=True, blank=True)

    # Comment-specific methods can be added here

    def __str__(self):
        return f"Comment by {self.creator.username} on \"{self.discussion.subject}\""


class UserPreference(Enum):
    SHOW = "show"
    HIDE = "hide"
    NONE = "none"

    @classmethod
    def choices(cls):
        return [(key.value, key.name) for key in cls]


class UserContentPreference(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='content_preferences')
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=False)
    object_id = models.PositiveIntegerField(null=False)
    content_object = GenericForeignKey('content_type', 'object_id')
    preference = models.CharField(max_length=10, choices=UserPreference.choices(), default=UserPreference.NONE.value)

    class Meta:
        unique_together = ('user', 'content_type', 'object_id')

    def __str__(self):
        return f"{self.user.username}'s preference for {self.content_object}"


# Utility function to update user preferences
def update_user_content_preference(user, content_object, preference):
    content_type = ContentType.objects.get_for_model(content_object)
    obj, created = UserContentPreference.objects.update_or_create(
        user=user,
        content_type=content_type,
        object_id=content_object.id,
        defaults={'preference': preference}
    )
    return obj