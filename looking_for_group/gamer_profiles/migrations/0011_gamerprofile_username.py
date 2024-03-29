# Generated by Django 2.1 on 2018-08-21 19:09

from django.db import migrations, models


def populate_usernames(apps, schema_editor):
    """
    Take the usernames from the existing user models and add them to gamerprofile
    """
    GamerProfile = apps.get_model("gamer_profiles", "GamerProfile")
    for gamer in GamerProfile.objects.all():
        if not gamer.username:
            gamer.username = gamer.user.username
            gamer.save()


class Migration(migrations.Migration):

    dependencies = [("gamer_profiles", "0010_auto_20180811_2124")]

    operations = [
        migrations.AddField(
            model_name="gamerprofile",
            name="username",
            field=models.TextField(
                help_text="Cached value from user.", null=True, blank=True
            ),
            preserve_default=False,
        ),
        migrations.RunPython(populate_usernames),
        migrations.AlterField(
            model_name="gamerprofile",
            name="username",
            field=models.TextField(
                help_text="Cached value from user.",
                null=False,
                blank=False,
                unique=True,
                db_index=True,
            ),
            preserve_default=False,
        ),
    ]
