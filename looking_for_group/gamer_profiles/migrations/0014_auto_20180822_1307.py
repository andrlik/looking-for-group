# Generated by Django 2.1 on 2018-08-22 17:07

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gamer_profiles', '0013_auto_20180822_1156'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='gamerrating',
            name='gamer',
        ),
        migrations.RemoveField(
            model_name='gamerrating',
            name='rater',
        ),
        migrations.RemoveField(
            model_name='gamerprofile',
            name='avg_gamer_rating',
        ),
        migrations.RemoveField(
            model_name='gamerprofile',
            name='median_gamer_rating',
        ),
        migrations.DeleteModel(
            name='GamerRating',
        ),
    ]