# Generated by Django 2.1.3 on 2018-11-10 05:20

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gamer_profiles', '0015_auto_20181107_2038'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='gamercommunity',
            options={'ordering': ['name'], 'verbose_name': 'Community', 'verbose_name_plural': 'Communities'},
        ),
    ]
