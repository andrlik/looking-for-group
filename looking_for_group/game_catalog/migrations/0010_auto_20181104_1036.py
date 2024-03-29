# Generated by Django 2.1.2 on 2018-11-04 15:36

from django.db import migrations


def remove_redundant_games(apps, schema_editor):
    Game = apps.get_model('game_catalog', 'PublishedGame')
    Edition = apps.get_model('game_catalog', 'GameEdition')
    editions = Edition.objects.all()
    redundant_games = Game.objects.exclude(id__in=[e.game.id for e in editions])
    print("Found {} duplicate games to remove".format(redundant_games.count()))
    del_g, obj_dict = redundant_games.delete()
    print("Deleted {} games".format(del_g))


class Migration(migrations.Migration):

    dependencies = [
        ('game_catalog', '0009_auto_20181104_1033'),
    ]

    operations = [
        migrations.RemoveField(model_name='publishedmodule', name='parent_game'),
        migrations.RunPython(remove_redundant_games, reverse_code=migrations.RunPython.noop),
    ]
