from django.db import migrations


def add_missing_commlinks(apps, schema_editor):
    Community = apps.get_model('gamer_profiles', 'GamerCommunity')
    CDL = apps.get_model('discord', 'CommunityDiscordLink')
    existing_communities = Community.objects.all()
    new_links_added = 0
    for comm in existing_communities:
        link, created = CDL.objects.get_or_create(community=comm)
        if created:
            new_links_added += 1
    print("{} new community links created".format(new_links_added))


class Migration(migrations.Migration):

    dependencies = [
        ('discord', '0002_auto_20180826_1335'),
    ]

    operations = [
        migrations.RunPython(add_missing_commlinks, reverse_code=migrations.RunPython.noop)
    ]
