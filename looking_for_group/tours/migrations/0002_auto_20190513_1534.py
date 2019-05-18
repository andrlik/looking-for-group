# Generated by Django 2.1.8 on 2019-05-13 19:34

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tours', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='step',
            name='placement',
            field=models.CharField(choices=[('bottom', 'Bottom'), ('top', 'Top'), ('left', 'Left'), ('right', 'Right')], default='bottom', help_text='Where should this appear in relation to the target?', max_length=25),
        ),
        migrations.AlterField(
            model_name='tour',
            name='users_completed',
            field=models.ManyToManyField(blank=True, related_name='completed_tours', to=settings.AUTH_USER_MODEL),
        ),
    ]