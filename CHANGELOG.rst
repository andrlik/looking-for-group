Title: Release Notes Date: 2018-11-10 09:00:00 Slug: release-notes
Modified: 2019-11-09 01:45:00 feature_image:
kevin-ku-364843-unsplash.jpg feature_image_credit: Kevin Ku
feature_image_creditlink: https://unsplash.com/photos/w7ZyuGYNpRQ

[TOC]

You’ll find a changelog for our code updates here.

10.0.3 (2019-11-13)
___________________

- Bug Fixes
   - Solved for filtering logic that was interfering with Keybase proofs.

10.0.2 (2019-11-09)
-------------------

-  Bug Fixes

   -  Server configuration improvements for static files.

.. _section-1:

1.10.0 (2019-11-09)
-------------------

-  Enhancements

   -  Major updates to the underlying API for performance. (Thank you,
      past me, for the comprehensive test suite.)
   -  RPG catalog now uses slugs instead UUIDs in urls.
   -  Improved game statistics tracking.
   -  Improvements to Keybase integration.

.. _section-2:

1.9.6 (2019-10-20)
------------------

-  Bug Fixes

   -  There was an issue where in some cases the dynamic form for
      creating a new game would require you to specify a published
      module, even if it shouldn’t. This is now resolved.

.. _section-3:

1.9.5 (2019-10-13)
------------------

-  Enhancements

   -  Performance Improvements

.. _section-4:

1.9.4 (2019-10-09)
------------------

-  Bug Fixes

   -  Fix links in footers to point to correct URLs instead of legacy
      domain.

.. _section-5:

1.9.3 (2019-10-07)
------------------

-  Enhancments

   -  Added support for Two-Factor Authentication even if you don’t use
      a Discord account.

.. _section-6:

1.9.2 (2019-10-03)
------------------

-  Bug Fixes

   -  Fixed an issue where the “Your Open” label in the help desk would
      display the count of all your issues and not just the open ones.

.. _section-7:

1.9.1 (2019-10-03)
------------------

-  Bug Fixes

   -  There was an error in the JavaScript API configuration that caused
      some front-end queries to fail. This is now resolved.

.. _section-8:

1.9.0 (2019-10-02)
------------------

-  Enhancements

   -  Added a local interface for helpdesk so that users do not have to
      sign up for a gitlab account to file requests for help.
   -  Add experimental support for `Keybase <https://keybase.io>`__
      proofs.
   -  When selecting the system, game edition, and module for a game,
      the system now dynamically updates the selection list to prevent
      mismatches. While LFG always based the display of this data on the
      most specific/restrictive selection made, there is now front end
      logic to help prevent misentries of data.

-  Bug Fixes

   -  Dropdowns for game edition could have their values appear in the
      wrong order. This is now fixed.
   -  When viewing the details of a game system in the RPG catalog, the
      release date would not display. This is fixed.

.. _section-9:

1.8.2 (2019-09-22)
------------------

-  Enhancements

   -  Larger and prettier featured images on game details page.

.. _section-10:

1.8.1 (2019-08-30)
------------------

-  Bug Fixes

   -  Sometimes LFG would throw an error if you had enough game sessions
      to trigger pagination. It no longer does this.

.. _section-11:

1.8.0 (2019-08-30)
------------------

-  Enhancements

   -  Now supports IRL games. You can specify if your game is online, by
      post, or face-to-face. If the in-person, you can also specify the
      game location. Other users can only see the city of your game
      until they are officially accepted as players. Once players have
      applied and been accepted into your game, they will be able to see
      the address with a map to help them find it for the first session.
   -  Users can now optionally specify the city in which they live to
      help them find local games. Only their fellow private community
      members, friends, and players in the same game can see this
      information.
   -  Game search now supports filtering by venue, i.e. online, IRL, and
      the distance from your city (if specified in your profile).

-  Bug Fixes

   -  Some optimizations made to improve performance during heavy loads.

.. _section-12:

1.7.10 (2019-08-12)
-------------------

-  Enhancements

   -  New infrastructure with full support for geospatial libraries and
      immutable images to improve stability and prepare for IRL game
      features.

-  Bug Fixes

   -  Fix for fragment of template code in editing publisher view title.
      #\ `151 <https://gitlab.com/andrlik/django-looking-for-group/issues/151>`__

.. _section-13:

1.7.8 (2019-07-15)
------------------

-  Bug Fixes

   -  Sometimes, canceling the game itself, and not just an individual
      session, would leave the game on you and your player’s calendars.
      This has been corrected.

.. _section-14:

1.7.7 (2019-07-01)
------------------

-  Enhancements

   -  Shared public community membership no longer counts as a personal
      connection for the purposes of viewing profile and messaging.

-  Bug Fixes

   -  Update to Django 2.2.3 for security release

.. _section-15:

1.7.6 (2019-06-25)
------------------

-  Bug Fixes

   -  Search page was throwing a 500 error. This is now fixed.

.. _section-16:

1.7.4 (2019-06-11)
------------------

-  Enhancements

   -  Performance improvements

.. _section-17:

1.7.3 (2019-06-05)
------------------

-  Enhancements

   -  Added ability for users to use formatting within profile free text
      fields.

-  Bug Fixes

   -  Fixed a number of small accessibility issues.

.. _section-18:

1.7.2 (2019-05-31)
------------------

-  Bug Fixes

   -  Fix erroneous color coding in dashboard stats

.. _section-19:

1.7.1 (2019-05-29)
------------------

-  Enhancements

   -  Display GM timezone on game listings
   -  Add timezone to game time displays to make it clear to the user
      that all times are displayed in their local timezone

.. _section-20:

1.7.0 (2019-05-26)
------------------

-  Enhancements

   -  Improved Accessibility (WCAG AA Compliance)

      -  Fixed header ordering
      -  Upped color contrasts
      -  Audit and update ARIA tags
      -  Add ability to users to add descriptive text to uploaded images
         for the visually disabled.

.. _section-21:

1.6.5 (2019-05-17)
------------------

-  Enhancements

   -  Added breadcrumb navigation to every page.
   -  Improvements to top bar menu

.. _section-22:

1.6.4 (2019-05-15)
------------------

-  Enhancements

   -  Added site tours for key pages. Tour only runs for the first time
      it is loaded for a user. However, the user can restart the tour
      using the “Start Guide” button that’s been added to each page with
      a tour.

-  Bug Fixes

   -  Improved scrolling on iOS devices

.. _section-23:

1.6.3 (2019-05-10)
------------------

-  Bug Fixes

   -  Fix to ensure datepicker is applied to fields on suggested
      correction and addition forms in the RPG DB.

.. _section-24:

1.6.2 (2019-05-09)
------------------

-  Enhancements

   -  Add ability to receive notifications when games are added to your
      community. This is controlled on a per community basis.

-  Bug Fixes

   -  It was once possible for people to add a game to a community while
      still having it set to private/unlisted. This didn’t make sense
      because no one in the community could see the game. The
      application now prevents you from making this mistake.
   -  There was an issue where if you had more than 20 unread
      notifications, the pagination would cause an error on the page.
      This is now fixed.

.. _section-25:

1.6.0 (2019-05-05)
------------------

-  Enhancements

   -  Add ability for users to suggest corrections to RPG DB listings.
   -  Add ability for users to suggest additions to the RPG DB listings.
   -  Add ability for site editors to review, edit, and approve
      submitted corrections and additions.

-  Bug Fixes

   -  There was an issue causing search requests to fail. This is now
      fixed.

.. _section-26:

1.5.6 (2019-05-01)
------------------

Happy May!

-  Enhancements

   -  Improved performance for dashboard loading.
   -  Improved display of gamer library collection on small screens.

.. _section-27:

1.5.5 (2019-04-27)
------------------

-  Enhancements

   -  Improved organization of media uploads on AWS S3
   -  Added additional tests for the user rpg collections functions to
      help protect against regressions.

-  Bug Fixes

   -  When editing a session to change it from complete to incomplete,
      the attendance statistics and session count for the game was not
      updating properly. This is now fixed.
   -  When marking a game as complete, the gm would have both their gm
      completed games count and their player completed games count
      increase. Now, the gm only has the gm-specific count increase.

.. _section-28:

1.5.0 (2019-04-21)
------------------

-  Adds support for gamer collections. Now you can mark sourcebooks,
   modules, and base game-system references as part of your personal
   library at home.

.. _section-29:

1.4.12 (2019-04-16)
-------------------

-  Bugfix for community member list pagination

.. _section-30:

1.4.11 (2019-04-14)
-------------------

-  Bug fixes for recurring events when they span across DST changes.
   There was an issue where these occurrences would have the time shown
   incorrectly in both the primary interface as well as the calendar.
   This is now fixed.

.. _section-31:

1.4.10 (2019-04-08)
-------------------

-  Bug fixes for display of game and community applicants on dashboard.

.. _section-32:

1.4.9 (2019-04-07)
------------------

-  Active active game count to GM profile.

.. _section-33:

1.4.8 (2019-04-03)
------------------

-  Updated for Django bugfix release 2.1.8

.. _section-34:

1.4.7 (2019-03-28)
------------------

-  Updated for Django security bugfix release 2.1.7

1.4.5 / v1.4.6 (2019-01-02)
---------------------------

-  Bugfix for session creation page to handle cases where previous
   sessions have been cancelled.
-  Added improvements to error logging
-  Updated for Django bugfix release 2.1.5

.. _section-35:

1.4.4 (2018-12-27)
------------------

-  Improve overall display formatting for RPG Database pages
-  Improve meta tags for pages
-  Allow markdown parsing in message of the day values.

.. _section-36:

1.4.3 (2018-12-20)
------------------

-  Improve look and feel of user facing forms.
-  Bugfix for community detail views.
-  Bugfix for proper timezone display of player available times.

.. _section-37:

1.4.1/1.4.2 (2018-12-19)
------------------------

-  Backend bugfixes

.. _section-38:

1.4.0 (2018-12-18)
------------------

-  Add ability for players to indicate their times available to play.
-  Added conflict checking functions to session scheduling so that GMs
   can know about issues with player availability or conflicting games.

.. _section-39:

1.3.0 (2018-12-15)
------------------

-  Added in-app messaging between players and GMs.
-  Added functionality to mute users so their messages are silently
   ignored.
-  Added Code of Conduct to site.
-  Added option to have messages forwarded to user’s email.

.. _section-40:

1.2.11 (2018-12-12)
-------------------

-  Added new admin utilities for managing the RPG Database records

1.2.7 - v.1.2.10 (2018-12-10)
-----------------------------

-  Migration changes required for moving from Heroku to AWS Elastic
   Beanstalk.

.. _section-41:

1.2.6 (2018-12-07)
------------------

-  Add tooltips for calendar and dashboard view.
-  Improvements to in-app notifications.

1.2.4/v1.2.5 (2018-12-06)
-------------------------

-  Bugfix for upcoming session display in dashboard.
-  Add links to games from upcoming sessions in dashboard.
-  Add links from calendar entries to games.
-  Fixes for iCal subscription feed.

.. _section-42:

1.2.3 (2018-12-01)
------------------

-  Add support for exporting user data.

.. _section-43:

1.2.2 (2018-11-30)
------------------

-  Bugfix for dashboard display

.. _section-44:

1.2.1 (2018-11-29)
------------------

-  Add support for side sessions and instant invites.

.. _section-45:

1.2.0 (2018-11-18)
------------------

-  Add support for featured images in communities.
-  Add support for featured images in game postings.
-  Added live-preview markdown editor with autosave for all user-facing
   description form fields.
-  Improvements to Discord syncing.
-  Bugfix: Game count for communities.
-  Bugfix: Datepicker date formatting conflicts.

.. _section-46:

1.1.0 (2018-11-15)
------------------

-  Major bugfixes for calendar behavior.
-  Added a number of critical performance-related features to the
   backend.

.. _section-47:

1.0.0 (2018-11-10)
------------------

-  Initial Release
