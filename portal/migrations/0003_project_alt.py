# Generated by Django 5.1.1 on 2024-10-06 07:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0002_project_icon_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='alt',
            field=models.CharField(default='', max_length=25),
        ),
    ]