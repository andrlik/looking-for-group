# Generated by Django 2.2.7 on 2019-11-15 14:33

from django.db import migrations, models
import django.utils.timezone
import model_utils.fields
import semantic_version.django_fields
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('releasenotes', '0002_add_missing_releasenote_stubs'),
    ]

    operations = [
        migrations.CreateModel(
            name='ReleaseNote',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', semantic_version.django_fields.VersionField(coerce=False, help_text='Semantic version for the update.', max_length=200, partial=False, unique=True)),
                ('notes', models.TextField(help_text='The notes for the release. This should be stored in Markdown.')),
                ('notes_rendered', models.TextField(blank=True, help_text='HTML rendered version of the notes field. Precalculated at creation to reduce template processing.', null=True)),
            ],
            options={
                'ordering': ['-version'],
            },
        ),
    ]
