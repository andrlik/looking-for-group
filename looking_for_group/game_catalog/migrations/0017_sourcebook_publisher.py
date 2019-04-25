from django.db import migrations


def populate_missing_publishers_in_sourcebook(apps, schema_editor):
    SourceBook = apps.get_model('game_catalog', 'SourceBook')
    x = 0
    for sb in SourceBook.objects.all():
        sb.publisher = sb.edition.publisher
        sb.save()
        x += 1
    print("Updated publishers in {} sourcebooks".format(x))


def undo_populate_publishers_in_sourcebook(apps, schema_editor):
    SourceBook = apps.get_model('game_catalog', 'SourceBook')
    updated_rows = SourceBook.objects.all().update(publisher=None)
    print("Removed publisher data for {} sourcebooks.".format(updated_rows))


class Migration(migrations.Migration):

    dependencies = [
        ('game_catalog', '0016_sourcebook_publisher'),
    ]

    operations = [
        migrations.RunPython(populate_missing_publishers_in_sourcebook, reverse_code=undo_populate_publishers_in_sourcebook),
    ]
