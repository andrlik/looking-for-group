# Generated by Django 2.1.3 on 2018-11-18 20:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0028_auto_20181114_1329'),
    ]

    operations = [
        migrations.AddField(
            model_name='gamesession',
            name='session_type',
            field=models.CharField(choices=[('normal', 'Normal'), ('adhoc', 'Ad hoc')], db_index=True, default='normal', max_length=20),
        ),
    ]
