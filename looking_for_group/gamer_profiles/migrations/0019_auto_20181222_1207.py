# Generated by Django 2.1.4 on 2018-12-22 17:07

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('gamer_profiles', '0018_auto_20181114_1437'),
    ]

    operations = [
        migrations.AlterField(
            model_name='banneduser',
            name='banned_user',
            field=models.ForeignKey(help_text='User who was banned.', on_delete=django.db.models.deletion.CASCADE, related_name='bans', to='gamer_profiles.GamerProfile'),
        ),
        migrations.AlterField(
            model_name='banneduser',
            name='banner',
            field=models.ForeignKey(help_text='User who initated ban.', on_delete=django.db.models.deletion.CASCADE, related_name='banned_users', to='gamer_profiles.GamerProfile'),
        ),
    ]
