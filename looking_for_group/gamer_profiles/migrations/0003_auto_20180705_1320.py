# Generated by Django 2.0.7 on 2018-07-05 17:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gamer_profiles', '0002_auto_20180705_1313'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gamerprofile',
            name='friends',
            field=models.ManyToManyField(blank=True, help_text='Other friends.', related_name='_gamerprofile_friends_+', to='gamer_profiles.GamerProfile'),
        ),
    ]
