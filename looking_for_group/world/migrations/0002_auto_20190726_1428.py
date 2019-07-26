# Generated by Django 2.2.3 on 2019-07-26 18:28

from django.core.management import call_command
from django.db import migrations


def load_world_borders(apps, schema_editor):
    call_command("loaddata", "worldborder.json", verbosity=0)


def remove_world_borders(apps, schema_editor):
    WorldBorder = apps.get_model("world", "WorldBorder")
    deleted_records = WorldBorder.objects.all().delete()
    print("Deleted {} records".format(deleted_records))


class Migration(migrations.Migration):

    dependencies = [("world", "0001_initial")]

    operations = [
        migrations.RunPython(load_world_borders, reverse_code=remove_world_borders)
    ]
