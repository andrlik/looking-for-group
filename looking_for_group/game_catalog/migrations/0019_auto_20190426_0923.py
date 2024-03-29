# Generated by Django 2.1.8 on 2019-04-26 13:23

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('game_catalog', '0018_auto_20190425_1333'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sourcebook',
            name='publisher',
            field=models.ForeignKey(help_text='Publisher of this sourcebook.', on_delete=django.db.models.deletion.CASCADE, to='game_catalog.GamePublisher'),
        ),
    ]
