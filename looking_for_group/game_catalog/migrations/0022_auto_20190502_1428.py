# Generated by Django 2.1.8 on 2019-05-02 18:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('game_catalog', '0021_auto_20190502_1427'),
    ]

    operations = [
        migrations.AlterField(
            model_name='suggestedaddition',
            name='ogl_license',
            field=models.BooleanField(default=False, help_text='Is this released under an OGL license?'),
        ),
    ]
