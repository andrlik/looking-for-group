# Generated by Django 2.2.5 on 2019-09-30 18:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('helpdesk', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='issuecommentlink',
            name='system_comment',
            field=models.BooleanField(default=False),
        ),
    ]