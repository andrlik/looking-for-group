from django.db import migrations


def populate_missing_releasenotice_stubs(apps, schema_editor):
    User = apps.get_model("users", "User")
    RN = apps.get_model("releasenotes", "ReleaseNotice")
    x = 0
    print("Preparing to add stubs for users...")
    for u in User.objects.all():
        RN.objects.create(user=u)
        x += 1
    print("Added {} release notices stubs!".format(x))


def remove_releasenotice_slugs(apps, schema_editor):
    RN = apps.get_model("releasenotes", "ReleaseNotice")
    num_deleted, objecttypes = RN.objects.all().delete()
    print("Deleted {} release notice records.".format(num_deleted))


class Migration(migrations.Migration):
    dependencies = [("releasenotes", "0001_initial")]

    operations = [
        migrations.RunPython(
            populate_missing_releasenotice_stubs,
            reverse_code=remove_releasenotice_slugs,
        )
    ]
