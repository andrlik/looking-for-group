# Generated by Django 2.1 on 2018-08-21 20:58
import itertools

from django.db import migrations, models
from django.utils.text import slugify


def generate_slugs(apps, schema_editor):
    """
    Generate the slugs for any pre-existing communities.
    """
    GamerCommunity = apps.get_model("gamer_profiles", "GamerCommunity")
    for comm in GamerCommunity.objects.all():
        if not comm.slug:
            max_length = 50
            temp_slug = slugify(comm.name, allow_unicode=True)[:max_length]
            for x in itertools.count(1):
                if not GamerCommunity.objects.filter(slug=temp_slug).exists():
                    break

                temp_slug = "{}-{}".format(temp_slug[:max_length - len(str(x)) - 1], x)
            comm.slug = temp_slug
            comm.save()


class Migration(migrations.Migration):

    dependencies = [("gamer_profiles", "0011_gamerprofile_username")]

    operations = [
        migrations.AddField(
            model_name="gamercommunity",
            name="slug",
            field=models.SlugField(null=True, blank=True, db_index=False),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="gamercommunity",
            name="name",
            field=models.CharField(
                db_index=True,
                help_text="Community Name (must be unique)",
                max_length=255,
                unique=True,
            ),
        ),
        migrations.RunPython(generate_slugs),
        migrations.AlterField(
            model_name="gamercommunity",
            name="slug",
            field=models.SlugField(
                null=False, blank=False, unique=True, db_index=True, max_length=50
            ),
            preserve_default=False,
        ),
    ]
