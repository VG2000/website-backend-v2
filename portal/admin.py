from django.contrib import admin
from .models import User, Project
from django.contrib.auth.admin import UserAdmin

admin.site.register(User, UserAdmin)
admin.site.register(Project)
