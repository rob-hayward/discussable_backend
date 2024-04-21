# discussable_app/management/commands/populate_content.py
from django.core.management.base import BaseCommand
import json
from random import shuffle, randint, sample, random
from discussable_app.models import Discussion, Comment, Vote, VoteType
from django.contrib.auth.models import User
from authentech_app.models import UserProfile


class Command(BaseCommand):
    help = 'Populates the database with sample discussions and comments'

    def handle(self, *args, **kwargs):
        with open('sample_content.json', 'r') as file:
            data = json.load(file)

        users = list(User.objects.all())

        for user in users:
            # Create a UserProfile for each user if it doesn't exist
            UserProfile.objects.get_or_create(user=user, defaults={'preferred_name': user.username})

        for item in data:
            subject = item["subject"]

            # Check if a discussion with the same subject already exists
            existing_discussion = Discussion.objects.filter(subject=subject).first()
            if existing_discussion:
                self.stdout.write(
                    self.style.WARNING(f"Discussion with subject '{subject}' already exists. Skipping creation..."))
                discussion = existing_discussion
            else:
                creator = users.pop(0) if users else User.objects.first()  # Cycle through users
                discussion = Discussion.objects.create(
                    creator=creator,
                    subject=subject,
                    category=item["category"]
                )

            # Assign votes to the discussion
            self.assign_votes(discussion, users)

            for comment_data in item["comments"]:
                existing_comment = Comment.objects.filter(discussion=discussion,
                                                          comment_content=comment_data["comment_content"]).first()
                if existing_comment:
                    self.stdout.write(self.style.WARNING(
                        f"Comment '{comment_data['comment_content']}' already exists. Skipping creation..."))
                    comment = existing_comment
                else:
                    comment = Comment.objects.create(
                        discussion=discussion,
                        creator=users.pop(0) if users else User.objects.first(),
                        comment_content=comment_data["comment_content"]
                    )

                # Assign votes to the comment
                self.assign_votes(comment, users)

                for reply_data in comment_data.get("replies", []):
                    existing_reply = Comment.objects.filter(discussion=discussion, parent=comment,
                                                            comment_content=reply_data["comment_content"]).first()
                    if existing_reply:
                        self.stdout.write(self.style.WARNING(
                            f"Reply '{reply_data['comment_content']}' already exists. Skipping creation..."))
                        reply = existing_reply
                    else:
                        reply = Comment.objects.create(
                            discussion=discussion,
                            creator=users.pop(0) if users else User.objects.first(),
                            comment_content=reply_data["comment_content"],
                            parent=comment
                        )

                    # Assign votes to the reply
                    self.assign_votes(reply, users)

            # Ensure we do not run out of users
            shuffle(users)  # Re-shuffle the main list for the next discussion

        self.stdout.write(self.style.SUCCESS('Successfully populated discussions and comments'))

    def assign_votes(self, votable, users):
        # Randomly select a subset of users to assign votes
        num_voters = randint(1, len(users))
        voters = sample(users, num_voters)

        for user in voters:
            # Randomly determine the vote type
            vote_type = VoteType.POSITIVE.value if random() < 0.8 else VoteType.NEGATIVE.value

            # Check if the user has already voted on the votable
            existing_vote = Vote.objects.filter(user=user, content_object=votable).first()
            if existing_vote:
                # Update the existing vote
                existing_vote.vote = vote_type
                existing_vote.save()
            else:
                # Create a new vote
                Vote.objects.create(
                    user=user,
                    content_object=votable,
                    vote=vote_type
                )

        # Update vote data for the votable
        votable.get_vote_data()