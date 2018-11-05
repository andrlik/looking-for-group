# Generated by Django 2.1.2 on 2018-11-05 22:48

import uuid

import django.db.models.deletion
import django.utils.timezone
import model_utils.fields
from django.db import migrations, models


def populate_missing_settings(apps, schema_editor):
    Preferences = apps.get_model('user_preferences', 'Preferences')
    Gamer = apps.get_model('gamer_profiles', 'GamerProfile')
    objects_added = 0
    gamers_to_add = Gamer.objects.exclude(id__in=[p.gamer.id for p in Preferences.objects.all()])
    for gamer in gamers_to_add:
        Preferences.objects.create(gamer=gamer)
        objects_added += 1
    print("{} new settings objects added!".format(objects_added))


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('gamer_profiles', '0014_auto_20180822_1307'),
    ]

    operations = [
        migrations.CreateModel(
            name='Preferences',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('news_emails', models.BooleanField(default=False, help_text='Send me occasionally news about the site. NOTE: We will still send you essential notices such as privacy policy and terms of service information, etc.')),
                ('notification_digest', models.BooleanField(default=False, help_text='Send me email digests of unread notifications.')),
                ('feedback_volunteer', models.BooleanField(default=False, help_text='Is it ok if we occasionally reach out to directly to solicit site feedback?')),
                ('gamer', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='gamer_profiles.GamerProfile')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.RunPython(populate_missing_settings, reverse_code=migrations.RunPython.noop),
    ]
