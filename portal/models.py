from django.db import models
from django.contrib.auth.models import UserManager, AbstractUser, PermissionsMixin

class Project(models.Model):
    name = models.CharField(max_length=100, unique=True)
    alt = models.CharField(max_length=25, default='')
    is_public = models.BooleanField(default=False)
    icon_url = models.URLField(max_length=500,blank=True, null=True)
    description = models.TextField(max_length=500, default='')

    def __str__(self):
        return self.name

class UserManager(UserManager):
    """Manager for users"""

    def create_user(self, email, password, **extra_fields):
        """Create, save, and return a new user"""
        if not email:
            raise ValueError('Email must be included')
        if not password:
            raise ValueError('Password must be provided')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        """Create and return a new superuser"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if not password:
            raise ValueError('Password must be provided')
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser, PermissionsMixin):
    # Existing fields...
    email = models.EmailField(max_length=255, unique=True)
    username = models.CharField(max_length=255)
    # Other fields...

    projects = models.ManyToManyField('Project', related_name='users')

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email