# Generated by Django 2.1.1 on 2018-09-10 16:10

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('gamer_profiles', '0014_auto_20180822_1307'),
        ('games', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='gameposting',
            name='gm',
        ),
        migrations.AddField(
            model_name='gameposting',
            name='gm',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='gmed_games', to='gamer_profiles.GamerProfile'),
            preserve_default=False,
        ),
    ]
