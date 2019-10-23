import base64

from django.db import migrations, models


def generate_uuid_slug(uuidvalue):
    return base64.urlsafe_b64encode(uuidvalue.bytes).decode("utf-8").replace("=", "")


def populate_missing_slugs(apps, schema_editor):
    models_to_update = []
    x = 0
    models_to_update.append(apps.get_model("game_catalog", "GamePublisher"))
    models_to_update.append(apps.get_model("game_catalog", "GameSystem"))
    models_to_update.append(apps.get_model("game_catalog", "PublishedGame"))
    models_to_update.append(apps.get_model("game_catalog", "PublishedModule"))
    for model in models_to_update:
        for item in model.objects.all():
            item.slug = generate_uuid_slug(item.pk)
            item.save()
            x += 1
    print("Added slugs to {} records.".format(x))


def undo_slugs(apps, schema_editor):
    models_to_update = []
    x = 0
    models_to_update.append(apps.get_model("game_catalog", "GamePublisher"))
    models_to_update.append(apps.get_model("game_catalog", "GameSystem"))
    models_to_update.append(apps.get_model("game_catalog", "PublishedGame"))
    models_to_update.append(apps.get_model("game_catalog", "PublishedModule"))
    for model in models_to_update:
        x += model.objects.all().update(slug=None)
    print("Removed slugs from {} records".format(x))


class Migration(migrations.Migration):

    dependencies = [("game_catalog", "0023_auto_20191023_1019")]

    operations = [
        migrations.RunPython(populate_missing_slugs, reverse_code=undo_slugs),
        migrations.AlterField(
            "gamepublisher",
            "slug",
            field=models.CharField(
                blank=True, db_index=True, unique=True, max_length=50
            ),
        ),
        migrations.AlterField(
            "gamesystem",
            "slug",
            field=models.CharField(
                blank=True, db_index=True, unique=True, max_length=50
            ),
        ),
        migrations.AlterField(
            "publishedgame",
            "slug",
            field=models.CharField(
                blank=True, db_index=True, unique=True, max_length=50
            ),
        ),
        migrations.AlterField(
            "publishedmodule",
            "slug",
            field=models.CharField(
                blank=True, db_index=True, unique=True, max_length=50
            ),
        ),
    ]
