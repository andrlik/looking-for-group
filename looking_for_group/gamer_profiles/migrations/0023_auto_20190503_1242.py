# Generated by Django 2.1.8 on 2019-05-03 16:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gamer_profiles', '0022_gm_finished_games'),
    ]

    operations = [
        migrations.AddField(
            model_name='gamerprofile',
            name='submitted_additions',
            field=models.PositiveIntegerField(default=0, help_text='How may additions has this user submitted to the catalog?'),
        ),
        migrations.AddField(
            model_name='gamerprofile',
            name='submitted_additions_approved',
            field=models.PositiveIntegerField(default=0, help_text='How many additions has this user submitted which were approved?'),
        ),
        migrations.AddField(
            model_name='gamerprofile',
            name='submitted_additions_rejected',
            field=models.PositiveIntegerField(default=0, help_text='How many additions has this user submitted which were rejected?'),
        ),
        migrations.AddField(
            model_name='gamerprofile',
            name='submitted_corrections',
            field=models.PositiveIntegerField(default=0, help_text='How many corrections has this user submitted to the catalog?'),
        ),
        migrations.AddField(
            model_name='gamerprofile',
            name='submitted_corrections_approved',
            field=models.PositiveIntegerField(default=0, help_text='How many corrections has this user submitted that were approved?'),
        ),
        migrations.AddField(
            model_name='gamerprofile',
            name='submitted_corrections_rejected',
            field=models.PositiveIntegerField(default=0, help_text='How many corrections has this user submitted that were rejected?'),
        ),
    ]