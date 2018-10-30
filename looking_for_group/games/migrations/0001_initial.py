# Generated by Django 2.1.1 on 2018-09-10 16:09

import uuid

import django.db.models.deletion
import django.utils.timezone
import model_utils.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('game_catalog', '0007_auto_20180830_1915'),
        ('gamer_profiles', '0014_auto_20180822_1307'),
    ]

    operations = [
        migrations.CreateModel(
            name='Character',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(help_text="What is this character's name?", max_length=100)),
                ('status', models.CharField(choices=[('pending', 'Submitted, pending approval'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('inactive', 'Inactive (or deceased)')], default='pending', max_length=15)),
                ('sheet', models.FileField(help_text='Upload your character sheet here.', upload_to='')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='GamePosting',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('game_type', models.CharField(choices=[('oneshot', 'One-Shot'), ('shortadv', 'Short Adventure (multiple sessions)'), ('campaign', 'Campaign')], db_index=True, default='oneshot', help_text='Is this a campaign or something shorter?', max_length=25)),
                ('title', models.CharField(help_text='What is the title of your campaign/game?', max_length=255)),
                ('mix_players', models.PositiveIntegerField(default=3, help_text='Minimum number of players needed to schedule this game, excluding the GM.')),
                ('max_players', models.PositiveIntegerField(default=1, help_text='Max number of players that will be in the game, excluding GM.')),
                ('adult_themes', models.BooleanField(default=False, help_text='Will this contain adult themes?')),
                ('content_warning', models.CharField(blank=True, help_text='Please include any content warnings your players should be aware of...', max_length=50, null=True)),
                ('privacy_level', models.CharField(choices=[('private', 'Only someone I explicitly share the link with can join.'), ('community', 'My friends and communities where I have posted this can see and join this game.'), ('public', 'Anyone can see this posting and apply to join.')], db_index=True, default='private', help_text='Choose the privacy level for this posting.', max_length=15)),
                ('game_frequency', models.CharField(choices=[('weekly', 'Every week'), ('biweekly', 'Every other week'), ('monthly', 'Every month'), ('na', 'N/A'), ('custom', 'Custom: See description for details')], db_index=True, default='weekly', help_text='How often will this be played?', max_length=15)),
                ('game_description', models.TextField(blank=True, help_text='Description of the game.', null=True)),
                ('game_description_rendered', models.TextField(blank=True, help_text='Automated rendering of markdown text as HTML.', null=True)),
                ('sessions', models.PositiveIntegerField(default=0)),
                ('communities', models.ManyToManyField(to='gamer_profiles.GamerCommunity')),
                ('game_system', models.ForeignKey(blank=True, help_text='What game system will you be using?', null=True, on_delete=django.db.models.deletion.SET_NULL, to='game_catalog.GameSystem')),
                ('gm', models.ForeignKey(blank=True, null=True, related_name='gmed_games', on_delete=django.db.models.deletion.SET_NULL, to='gamer_profiles.GamerProfile')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='GameSession',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('scheduled_time', models.DateTimeField()),
                ('gm_notes', models.TextField(blank=True, help_text='Any notes you would like to make here. Markdown can be used for formatting.', null=True)),
                ('gm_notes_rendered', models.TextField(blank=True, null=True)),
                ('game', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='games.GamePosting')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Player',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('sessions_attended', models.PositiveIntegerField(default=0)),
                ('sessions_missed', models.PositiveIntegerField(default=0)),
                ('game', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='games.GamePosting')),
                ('gamer', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='gamer_profiles.GamerProfile')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='gamesession',
            name='players_missing',
            field=models.ManyToManyField(help_text="Are there any players missing here for reasons that don't have to do with the story?", related_name='missed_sessions', to='games.Player'),
        ),
        migrations.AddField(
            model_name='gamesession',
            name='players_present',
            field=models.ManyToManyField(help_text='Players in attendance?', to='games.Player'),
        ),
        migrations.AddField(
            model_name='gameposting',
            name='players',
            field=models.ManyToManyField(through='games.Player', to='gamer_profiles.GamerProfile'),
        ),
        migrations.AddField(
            model_name='gameposting',
            name='published_game',
            field=models.ForeignKey(blank=True, help_text='What type of game are you playing, e.g. D&D5E? Leave blank for homebrew.', null=True, on_delete=django.db.models.deletion.SET_NULL, to='game_catalog.PublishedGame'),
        ),
        migrations.AddField(
            model_name='gameposting',
            name='published_module',
            field=models.ForeignKey(blank=True, help_text='Will this game be based on a published module? Leave blank for homebrew.', null=True, on_delete=django.db.models.deletion.SET_NULL, to='game_catalog.PublishedModule'),
        ),
        migrations.AddField(
            model_name='character',
            name='game',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='games.GamePosting'),
        ),
        migrations.AddField(
            model_name='character',
            name='player',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='games.Player'),
        ),
    ]