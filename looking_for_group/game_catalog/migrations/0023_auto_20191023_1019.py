# Generated by Django 2.2.6 on 2019-10-23 14:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("game_catalog", "0022_auto_20190502_1428")]

    operations = [
        migrations.AddField(
            model_name="gamepublisher",
            name="slug",
            field=models.CharField(blank=True, db_index=True, max_length=50),
        ),
        migrations.AddField(
            model_name="gamesystem",
            name="slug",
            field=models.CharField(blank=True, db_index=True, max_length=50),
        ),
        migrations.AddField(
            model_name="publishedgame",
            name="slug",
            field=models.CharField(blank=True, db_index=True, max_length=50),
        ),
        migrations.AddField(
            model_name="publishedmodule",
            name="slug",
            field=models.CharField(blank=True, db_index=True, max_length=50),
        ),
    ]