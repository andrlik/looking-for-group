# Generated by Django 2.1.8 on 2019-05-10 20:06

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Step',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('step_order', models.PositiveIntegerField(default=0, help_text='The order of this step. Note that the number must be unique for the tour.')),
                ('target_id', models.CharField(help_text='The id of the html element target for this step.', max_length=100)),
                ('step_title', models.CharField(help_text='The title that should appear for this step.', max_length=50)),
                ('guide_text', models.TextField(help_text='The Markdown version of the explanation that you want to appear in the guide box for this step of the tour.')),
            ],
            options={
                'ordering': ['tour', 'step_order'],
            },
        ),
        migrations.CreateModel(
            name='Tour',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('slug', models.CharField(blank=True, db_index=True, max_length=50, unique=True)),
                ('name', models.CharField(db_index=True, max_length=50, unique=True)),
                ('description', models.TextField()),
                ('enabled', models.BooleanField(default=False)),
                ('users_completed', models.ManyToManyField(related_name='completed_tours', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.AddField(
            model_name='step',
            name='tour',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='steps', to='tours.Tour'),
        ),
        migrations.AlterUniqueTogether(
            name='step',
            unique_together={('tour', 'step_order')},
        ),
    ]