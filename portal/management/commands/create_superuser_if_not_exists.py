from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from portal.models import Project

class Command(BaseCommand):
    help = 'Create a superuser and a regular user if they do not exist'

    def add_arguments(self, parser):
        parser.add_argument('--superuser_email', type=str, help='superuser@example.com')
        parser.add_argument('--superuser_password', type=str, help='password')
        parser.add_argument('--user_email', type=str, default='user@example.com', help='Regular user email')
        parser.add_argument('--user_password', type=str, default='password', help='Regular user password')

    def handle(self, *args, **kwargs):
        User = get_user_model()

        superuser_email = kwargs['superuser_email']
        superuser_password = kwargs['superuser_password']
        user_email = kwargs['user_email']
        user_password = kwargs['user_password']

        # Create superuser
        if not User.objects.filter(email=superuser_email).exists():
            superuser = User.objects.create_superuser(email=superuser_email, password=superuser_password)
            self.stdout.write(self.style.SUCCESS('Superuser created.'))

            # Add all projects to the superuser
            all_projects = Project.objects.all()
            # all_projects = Project.objects.filter(name__in=['my-mp', 'investments'])
            superuser.projects.set(all_projects)
            superuser.save()

            self.stdout.write(self.style.SUCCESS('All projects assigned to the superuser.'))
        else:
            self.stdout.write(self.style.SUCCESS('Superuser already exists.'))

        # Create regular user
        if not User.objects.filter(email=user_email).exists():
            user = User.objects.create_user(email=user_email, password=user_password)
            self.stdout.write(self.style.SUCCESS('Regular user created.'))

            # Add "my-mp" and "investments" projects to the regular user
            projects_to_assign = Project.objects.filter(name__in=['my-mp', 'investment'])
            user.projects.set(projects_to_assign)
            user.save()

            self.stdout.write(self.style.SUCCESS('Projects "my-mp" and "investment" assigned to the regular user.'))
        else:
            self.stdout.write(self.style.SUCCESS('Regular user already exists.'))
