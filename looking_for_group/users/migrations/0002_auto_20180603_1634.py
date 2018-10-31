# Generated by Django 2.0.6 on 2018-06-03 20:34

import django.utils.timezone
import model_utils.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='user',
            options={},
        ),
        migrations.AddField(
            model_name='user',
            name='bio',
            field=models.CharField(blank=True, help_text='A few words about you.', max_length=255, null=True, verbose_name='Bio'),
        ),
        migrations.AddField(
            model_name='user',
            name='created',
            field=model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created'),
        ),
        migrations.AddField(
            model_name='user',
            name='display_name',
            field=models.CharField(blank=True, help_text="🎶 What's your name, son? ALEXANDER HAMILTON", max_length=255, null=True, verbose_name='Display Name'),
        ),
        migrations.AddField(
            model_name='user',
            name='homepage_url',
            field=models.URLField(blank=True, help_text='Your home on the web.', null=True, verbose_name='Homepage'),
        ),
        migrations.AddField(
            model_name='user',
            name='modified',
            field=model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified'),
        ),
    ]
