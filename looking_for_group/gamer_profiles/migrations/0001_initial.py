# Generated by Django 2.0.6 on 2018-06-25 17:41

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('game_catalog', '0005_auto_20180623_1430'),
    ]

    operations = [
        migrations.CreateModel(
            name='BannedUser',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('reason', models.TextField(help_text='Why is this user being banned?')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='BlockedUser',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='CommunityApplication',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('message', models.TextField(blank=True, help_text='Any message to pass along with your application?', null=True)),
                ('status', models.CharField(choices=[('new', 'New'), ('review', 'In Review'), ('reject', 'Rejected'), ('approve', 'Approved'), ('hold', 'On Hold')], db_index=True, help_text='Application Status', max_length=30)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='CommunityMembership',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('community_role', models.CharField(choices=[('member', 'Member'), ('moderator', 'Moderator'), ('admin', 'Admin')], db_index=True, default='member', max_length=25)),
                ('avg_comm_rating', models.PositiveIntegerField(default=0, help_text='Average rating from other community members.', validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(5)])),
                ('median_comm_rating', models.PositiveIntegerField(default=0, help_text='Median rating from other community members.', validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(5)])),
                ('comm_reputation_score', models.IntegerField(default=0, help_text='Calculated reputation score within community.')),
                ('comm_games_joined', models.PositiveIntegerField(default=0, help_text='How many time has this user joined a game?')),
                ('comm_games_created', models.PositiveIntegerField(default=0, help_text='How many times has this user created a game?')),
                ('comm_games_applied', models.PositiveIntegerField(default=0, help_text='How many times has this user applied to join a game?')),
                ('comm_games_left', models.PositiveIntegerField(default=0, help_text='How many times has this user left a game before it was completed?')),
                ('comm_games_finished', models.PositiveIntegerField(default=0, help_text='How many finished games has this user participated in?')),
                ('comm_game_attendance_record', models.DecimalField(blank=True, decimal_places=4, help_text='Attendance percentage for sessions within community.', max_digits=4, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='GamerCommunity',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(help_text='Community Name', max_length=255)),
                ('description', models.TextField(blank=True, help_text='Describe your community. You can use Markdown for formatting.', null=True)),
                ('description_rendered', models.TextField(blank=True, help_text='HTML generated from the makdown description.', null=True)),
                ('url', models.URLField(blank=True, help_text='Link to the community web site, if applicable.', null=True)),
                ('linked_with_discord', models.BooleanField(default=False, help_text='Is this linked with a Discord server?')),
                ('private', models.BooleanField(default=True, help_text='Do users need to apply to join this community? If linked with Discord, users will automatically be added.')),
                ('application_approval', models.CharField(choices=[('member', 'Member'), ('moderator', 'Moderator'), ('admin', 'Admin')], db_index=True, default='admin', help_text='What is the minimum role required to approve a membership application?', max_length=25)),
                ('invites_allowed', models.CharField(choices=[('member', 'Member'), ('moderator', 'Moderator'), ('admin', 'Admin')], db_index=True, default='admin', help_text='What is the minimum role level required to invite others to the community?', max_length=25)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='GamerNote',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('title', models.CharField(help_text='Some helpful title for you.', max_length=255)),
                ('body', models.TextField(help_text='Your note (markdown ok, but html is naughty.)')),
                ('body_rendered', models.TextField(help_text='The actual rendered text derived from source markdown.')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='GamerProfile',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('rpg_experience', models.TextField(blank=True, help_text='A few words about your RPG experience. (Visible to GM.)', null=True)),
                ('ttgame_experience', models.TextField(blank=True, help_text='A few words about your non-RPG tabletop experience. (Visible to GM)', null=True)),
                ('playstyle', models.TextField(blank=True, help_text='A few words on the kinds of games you prefer to play, i.e. horror, silly, tactical, RP-heavy, etc.', max_length=500, null=True)),
                ('will_gm', models.BooleanField(db_index=True, default=False, help_text='Willing to be a GM?')),
                ('player_status', models.CharField(choices=[('all_full', 'All good, thanks.'), ('available', "I'm available, but not looking for anything."), ('searching', 'Looking for games.')], db_index=True, default='all_full', help_text='Are you looking for a group right now?', max_length=25)),
                ('adult_themes', models.BooleanField(db_index=True, default=False, help_text='Are you ok with 18+ themes/content/language in games?')),
                ('adventures', models.BooleanField(db_index=True, default=False, help_text='Interested in short multi-session games?')),
                ('campaigns', models.BooleanField(db_index=True, default=False, help_text='Interested in joining a campaign?')),
                ('online_games', models.BooleanField(db_index=True, default=False, help_text='Interested in online games, e.g. Roll20?')),
                ('local_games', models.BooleanField(db_index=True, default=False, help_text='Intested in local games?')),
                ('games_joined', models.PositiveIntegerField(default=0, help_text='How many time has this user joined a game?')),
                ('games_created', models.PositiveIntegerField(default=0, help_text='How many times has this user created a game?')),
                ('games_applied', models.PositiveIntegerField(default=0, help_text='How many times has this user applied to join a game?')),
                ('games_left', models.PositiveIntegerField(default=0, help_text='How many times has this user left a game before it was completed?')),
                ('games_finished', models.PositiveIntegerField(default=0, help_text='How many finished games has this user participated in?')),
                ('avg_gamer_rating', models.PositiveIntegerField(default=0, help_text='Average overall rating from other players.', validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(5)])),
                ('median_gamer_rating', models.PositiveIntegerField(default=0, help_text='Median overall rating from other players.', validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(5)])),
                ('reputation_score', models.IntegerField(default=0, help_text='Calculated overall reputation score.')),
                ('attendance_record', models.DecimalField(blank=True, decimal_places=4, help_text='Overall attendance record for games sessions.', max_digits=4, null=True)),
                ('communities', models.ManyToManyField(blank=True, through='gamer_profiles.CommunityMembership', to='gamer_profiles.GamerCommunity')),
                ('preferred_games', models.ManyToManyField(blank=True, help_text='Do you have any preferred games you like to play?', to='game_catalog.PublishedGame')),
                ('preferred_systems', models.ManyToManyField(blank=True, help_text='Do you have any preferred systems you like to play?', to='game_catalog.GameSystem')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='GamerRating',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('rating', models.PositiveIntegerField(default=0, help_text='How are they rated?', validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(5)])),
                ('gamer', models.ForeignKey(help_text='Which gamer is being rated?', on_delete=django.db.models.deletion.CASCADE, to='gamer_profiles.GamerProfile')),
                ('rater', models.ForeignKey(help_text='Who is rating this user?', on_delete=django.db.models.deletion.CASCADE, related_name='raters', to='gamer_profiles.GamerProfile')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='KickedUser',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('end_date', models.DateTimeField(blank=True, help_text='Earliest date that user can reapply.', null=True)),
                ('reason', models.TextField(help_text='Why is the user kicked from this community?')),
                ('community', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='gamer_profiles.GamerCommunity')),
                ('kicked_user', models.ForeignKey(help_text='User who was kicked.', on_delete=django.db.models.deletion.CASCADE, to='gamer_profiles.GamerProfile')),
                ('kicker', models.ForeignKey(help_text='User who initated kick.', on_delete=django.db.models.deletion.CASCADE, related_name='kicked_by_users', to='gamer_profiles.GamerProfile')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='MutedUser',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('mutee', models.ForeignKey(help_text='User who has been muted.', on_delete=django.db.models.deletion.CASCADE, to='gamer_profiles.GamerProfile')),
                ('muter', models.ForeignKey(help_text='User who initiated mute.', on_delete=django.db.models.deletion.CASCADE, related_name='muted_by_users', to='gamer_profiles.GamerProfile')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='gamernote',
            name='author',
            field=models.ForeignKey(help_text='Who wrote this note?', on_delete=django.db.models.deletion.CASCADE, related_name='authored_notes', to='gamer_profiles.GamerProfile'),
        ),
        migrations.AddField(
            model_name='gamernote',
            name='gamer',
            field=models.ForeignKey(help_text='Whom is this note about?', on_delete=django.db.models.deletion.CASCADE, to='gamer_profiles.GamerProfile'),
        ),
        migrations.AddField(
            model_name='communitymembership',
            name='community',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='members', to='gamer_profiles.GamerCommunity'),
        ),
        migrations.AddField(
            model_name='communitymembership',
            name='gamer',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='gamer_profiles.GamerProfile'),
        ),
        migrations.AddField(
            model_name='communityapplication',
            name='community',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='gamer_profiles.GamerCommunity'),
        ),
        migrations.AddField(
            model_name='communityapplication',
            name='gamer',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='gamer_profiles.GamerProfile'),
        ),
        migrations.AddField(
            model_name='blockeduser',
            name='blockee',
            field=models.ForeignKey(help_text='User who has been blocked.', on_delete=django.db.models.deletion.CASCADE, to='gamer_profiles.GamerProfile'),
        ),
        migrations.AddField(
            model_name='blockeduser',
            name='blocker',
            field=models.ForeignKey(help_text='User who initiated block.', on_delete=django.db.models.deletion.CASCADE, related_name='blocked_by_users', to='gamer_profiles.GamerProfile'),
        ),
        migrations.AddField(
            model_name='banneduser',
            name='banned_user',
            field=models.ForeignKey(help_text='User who was banned.', on_delete=django.db.models.deletion.CASCADE, to='gamer_profiles.GamerProfile'),
        ),
        migrations.AddField(
            model_name='banneduser',
            name='banner',
            field=models.ForeignKey(help_text='User who initated ban.', on_delete=django.db.models.deletion.CASCADE, related_name='banned_by_users', to='gamer_profiles.GamerProfile'),
        ),
        migrations.AddField(
            model_name='banneduser',
            name='community',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='gamer_profiles.GamerCommunity'),
        ),
        migrations.AlterUniqueTogether(
            name='communitymembership',
            unique_together={('gamer', 'community')},
        ),
    ]
