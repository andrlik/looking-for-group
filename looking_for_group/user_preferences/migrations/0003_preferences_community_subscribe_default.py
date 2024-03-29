# Generated by Django 2.1.8 on 2019-05-06 13:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user_preferences', '0002_preferences_email_messages'),
    ]

    operations = [
        migrations.AddField(
            model_name='preferences',
            name='community_subscribe_default',
            field=models.BooleanField(default=False, help_text='When joining a community, receive notifications of new games being posted there by default. (You can also edit this for individual communities.)', verbose_name='Default for community subscriptions'),
        ),
    ]
