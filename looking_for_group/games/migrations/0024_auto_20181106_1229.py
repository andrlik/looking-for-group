# Generated by Django 2.1.2 on 2018-11-06 17:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0023_auto_20181106_1053'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gameposting',
            name='game_description',
            field=models.TextField(help_text='Description of the game. You can used Markdown for formatting/link.'),
        ),
    ]