from django.db import migrations
from django.db.models import F


def populate_missing_gm_finished_count(apps, schema_editor):
    GamerProfile = apps.get_model('gamer_profiles', 'GamerProfile')
    x = 0
    for g in GamerProfile.objects.filter(games_created__gte=1):
        g.gm_games_finished = g.gmed_games.filter(status='closed').count()
        g.save()
        if g.gm_games_finished > 0:
            x += 1
    print("Updated finished games records for {} GMs".format(x))


def remove_gm_finished_count(apps, schema_editor):
    GamerProfile = apps.get_model('gamer_profiles', 'GamerProfile')
    gamers = GamerProfile.objects.all()
    x = gamers.update(gm_games_finished=0)
    print("Cleared gm games finished for {} records".format(x))


class Migration(migrations.Migration):

    dependencies = [
        ("gamer_profiles", "0021_auto_20190426_0923"),
    ]

    operations = [
        migrations.RunPython(populate_missing_gm_finished_count, reverse_code=remove_gm_finished_count)
    ]
