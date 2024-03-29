# Generated by Django 2.1.8 on 2019-04-07 13:29

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='Book',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('slug', models.CharField(blank=True, db_index=True, max_length=50, unique=True)),
                ('in_print', models.BooleanField(default=False, help_text='In print?')),
                ('in_pdf', models.BooleanField(default=False, help_text='In PDF?')),
                ('object_id', models.CharField(help_text='ID of the related object.', max_length=70)),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.ContentType')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='GameLibrary',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('slug', models.CharField(blank=True, db_index=True, max_length=50, unique=True)),
                ('num_titles', models.PositiveIntegerField(default=0)),
                ('num_pdf', models.PositiveIntegerField(default=0)),
                ('num_print', models.PositiveIntegerField(default=0)),
                ('distinct_game_editions', models.PositiveIntegerField(default=0)),
                ('distinct_sourcebooks', models.PositiveIntegerField(default=0)),
                ('distinct_modules', models.PositiveIntegerField(default=0)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='book',
            name='library',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='rpgcollections.GameLibrary'),
        ),
    ]
