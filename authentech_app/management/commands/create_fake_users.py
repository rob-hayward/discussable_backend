# authentech_app/management/commands/create_fake_users.py
from django.core.management.base import BaseCommand
from faker import Faker
from django.contrib.auth.models import User
from authentech_app.models import UserProfile


class Command(BaseCommand):
    help = 'Generate fake users'

    def add_arguments(self, parser):
        parser.add_argument('total', type=int, help='Indicate the number of fake users to create')

    def handle(self, *args, **options):
        total = options['total']
        faker = Faker()

        for _ in range(total):
            username = faker.user_name()
            # Ensure username is unique
            while User.objects.filter(username=username).exists():
                username = faker.user_name()

            name = faker.name().split()
            first_name = name[0]
            last_name = name[-1] if len(name) > 1 else ''
            email = faker.email()
            password = User.objects.make_random_password()

            user = User.objects.create_user(username=username, email=email, first_name=first_name, last_name=last_name,
                                            password=password)

            # Create a UserProfile for the user
            UserProfile.objects.create(user=user, preferred_name=faker.name())

            self.stdout.write(self.style.SUCCESS(f'User {username} created successfully'))