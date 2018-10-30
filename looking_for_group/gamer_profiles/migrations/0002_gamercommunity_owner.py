# Generated by Django 2.0.6 on 2018-07-05 15:30

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gamer_profiles', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='gamercommunity',
            name='owner',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='gamer_profiles.GamerProfile'),
            preserve_default=False,
        ),
    ]
