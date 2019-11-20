.. :changelog:

+++++++++++++
Release Notes
+++++++++++++

You’ll find a changelog for our code updates here.

**************************
1.11.1 (2019-11-19)
**************************

- Enhancements
  + 🎨 Improve mobile version of release notes view.
  + ✅ ♿ Add accessibility tests for the release notes.

**************************
1.11.0 (2019-11-18)
**************************

- Enhancements
  + ✨ Release notes are now embedded into the app to reduce double documentation.
  + ✨ New updates are shown to a user on login based on the last set of release notes they saw.
  + 🚀 Update to Django 2.2.7 bugfix release.

**************************
1.10.4 (2019-11-14)
**************************

- Bug Fixes
  + 🐛 Addiitonal Keybase fixes as we move towards full integration with the Keybase production client.

**************************
1.10.3 (2019-11-13)
**************************

- Bug Fixes
  + 🐛 Solved for filtering logic that was interfering with Keybase proofs.

**************************
1.10.2 (2019-11-09)
**************************

- Bug Fixes
  + 🐛 Server configuration improvements for static files.

**************************
1.10.0 (2019-11-09)
**************************

- Enhancements
  + 🏗 Major updates to the underlying API for performance. (Thank you, past me, for the comprehensive test suite.)
  + ✨ RPG catalog now uses slugs instead UUIDs in urls.
  + ✨ Improved game statistics tracking.
  + ✨ Improvements to Keybase integration.


************************
1.9.6 (2019-10-20)
************************

- Bug Fixes
  + 🐛 There was an issue where in some cases the dynamic form for creating a new game would require you to specify a published module, even if it shouldn’t. This is now resolved.


**************************
1.9.5 (2019-10-13)
**************************

- Enhancements
  + ✨ Performance Improvements


**************************
1.9.4 (2019-10-09)
**************************

- Bug Fixes
  + 🐛 Fix links in footers to point to correct URLs instead of legacy domain.


**************************
1.9.3 (2019-10-07)
**************************

- Enhancments
  + ✨ Added support for Two-Factor Authentication even if you don’t use a Discord account.


************************
1.9.2 (2019-10-03)
************************

- Bug Fixes
  + 🐛 Fixed an issue where the “Your Open” label in the help desk would display the count of all your issues and not just the open ones.


************************
1.9.1 (2019-10-03)
************************

- Bug Fixes
  + 🐛 There was an error in the JavaScript API configuration that caused some front-end queries to fail. This is now resolved.


************************
1.9.0 (2019-10-02)
************************

- Enhancements
  + ✨ Added a local interface for helpdesk so that users do not have to sign up for a gitlab account to file requests for help.
  + ✨ Add experimental support for `Keybase <https://keybase.io>`__ proofs.
  + ✨ When selecting the system, game edition, and module for a game, the system now dynamically updates the selection list to prevent mismatches. While LFG always based the display of this data on the most specific/restrictive selection made, there is now front end logic to help prevent misentries of data.
- Bug Fixes
  + 🐛 Dropdowns for game edition could have their values appear in the wrong order. This is now fixed.
  + 🐛 When viewing the details of a game system in the RPG catalog, the release date would not display. This is fixed.


************************
1.8.2 (2019-09-22)
************************

- Enhancements
  + 🎨 Larger and prettier featured images on game details page.


************************
1.8.1 (2019-08-30)
************************

- Bug Fixes
  + 🐛 Sometimes LFG would throw an error if you had enough game sessions to trigger pagination. It no longer does this.


************************
1.8.0 (2019-08-30)
************************

- Enhancements
  + ✨ Now supports IRL games. You can specify if your game is online, by post, or face-to-face. If the in-person, you can also specify the game location. Other users can only see the city of your game until they are officially accepted as players. Once players have applied and been accepted into your game, they will be able to see the address with a map to help them find it for the first session.
  + ✨ Users can now optionally specify the city in which they live to help them find local games. Only their fellow private community members, friends, and players in the same game can see this information.
  + ✨ Game search now supports filtering by venue, i.e. online, IRL, and the distance from your city (if specified in your profile).
- Bug Fixes
  + 🐛 Some optimizations made to improve performance during heavy loads.


**************************
1.7.10 (2019-08-12)
**************************

- Enhancements
  + 🚀 New infrastructure with full support for geospatial libraries and immutable images to improve stability and prepare for IRL game features.
- Bug Fixes
  + 🐛 Fix for fragment of template code in editing publisher view title. `151 <https://gitlab.com/andrlik/django-looking-for-group/issues/151>`__


************************
1.7.8 (2019-07-15)
************************

- Bug Fixes
  + 🐛 Sometimes, canceling the game itself, and not just an individual session, would leave the game on you and your player’s calendars. This has been corrected.


************************
1.7.7 (2019-07-01)
************************

- Enhancements
  + ✨ Shared public community membership no longer counts as a personal connection for the purposes of viewing profile and messaging.
- Bug Fixes
  + 🐛 Update to Django 2.2.3 for security release


************************
1.7.6 (2019-06-25)
************************

- Bug Fixes
  + 🐛 Search page was throwing a 500 error. This is now fixed.


************************
1.7.4 (2019-06-11)
************************

- Enhancements
  + Performance improvements


************************
1.7.3 (2019-06-05)
************************

- Enhancements
  + ✨ Added ability for users to use formatting within profile free text fields.
- Bug Fixes
  + 🐛 ♿ Fixed a number of small accessibility issues.


************************
1.7.2 (2019-05-31)
************************

- Bug Fixes
  + 🐛 Fix erroneous color coding in dashboard stats


************************
1.7.1 (2019-05-29)
************************

- Enhancements
  + ✨ Display GM timezone on game listings
  + ✨ Add timezone to game time displays to make it clear to the user that all times are displayed in their local timezone


************************
1.7.0 (2019-05-26)
************************

- Enhancements
  + ♿ Improved Accessibility (WCAG AA Compliance)
  + ♿ Fixed header ordering
  + ♿ Upped color contrasts
  + ♿ Audit and update ARIA tags
  + ♿ Add ability to users to add descriptive text to uploaded images for the visually disabled.


************************
1.6.5 (2019-05-17)
************************

- Enhancements
  + ✨ Added breadcrumb navigation to every page.
  + ✨ Improvements to top bar menu


************************
1.6.4 (2019-05-15)
************************

- Enhancements
  + ✨ Added site tours for key pages. Tour only runs for the first time it is loaded for a user. However, the user can restart the tour using the “Start Guide” button that’s been added to each page with a tour.
- Bug Fixes
  + 🐛 Improved scrolling on iOS devices


************************
1.6.3 (2019-05-10)
************************

- Bug Fixes
  + 🐛 Fix to ensure datepicker is applied to fields on suggested correction and addition forms in the RPG DB.


************************
1.6.2 (2019-05-09)
************************

- Enhancements
  + ✨ Add ability to receive notifications when games are added to your community. This is controlled on a per community basis.
- Bug Fixes
  + 🐛 It was once possible for people to add a game to a community while still having it set to private/unlisted. This didn’t make sense because no one in the community could see the game. The application now prevents you from making this mistake.
  + 🐛 There was an issue where if you had more than 20 unread notifications, the pagination would cause an error on the page. This is now fixed.


************************
1.6.0 (2019-05-05)
************************

- Enhancements
  + ✨ Add ability for users to suggest corrections to RPG DB listings.
  + ✨ Add ability for users to suggest additions to the RPG DB listings.
  + ✨ Add ability for site editors to review, edit, and approve submitted corrections and additions.
- Bug Fixes
  + 🐛 There was an issue causing search requests to fail. This is now fixed.


************************
1.5.6 (2019-05-01)
************************

- Enhancements
  + ✨ Improved performance for dashboard loading.
  + ✨ Improved display of gamer library collection on small screens.


************************
1.5.5 (2019-04-27)
************************

- Enhancements
  + ✨ Improved organization of media uploads on AWS S3
  + ✨ Added additional tests for the user rpg collections functions to help protect against regressions.
- Bug Fixes
  + 🐛 When editing a session to change it from complete to incomplete, the attendance statistics and session count for the game was not updating properly. This is now fixed.
  + 🐛 When marking a game as complete, the gm would have both their gm completed games count and their player completed games count increase. Now, the gm only has the gm-specific count increase.


************************
1.5.0 (2019-04-21)
************************

- Enhancements
  + ✨ Adds support for gamer collections. Now you can mark sourcebooks, modules, and base game-system references as part of your personal library at home.


**************************
1.4.12 (2019-04-16)
**************************

- Bug Fixes
  + 🐛 Bugfix for community member list pagination


**************************
1.4.11 (2019-04-14)
**************************

- Bug Fixes
  + 🐛 Bug fixes for recurring events when they span across DST changes. There was an issue where these occurrences would have the time shown incorrectly in both the primary interface as well as the calendar. This is now fixed.


**************************
1.4.10 (2019-04-08)
**************************

- Bug Fixes
  + 🐛 Bug fixes for display of game and community applicants on dashboard.


************************
1.4.9 (2019-04-07)
************************
- Enhancements
  + ✨ Active active game count to GM profile.

************************
1.4.8 (2019-04-03)
************************

- Enhancements
  + Updated for Django bugfix release 2.1.8

************************
1.4.7 (2019-03-28)
************************

- Enhancements
  + Updated for Django security bugfix release 2.1.7


**************************
1.4.6 (2019-01-02)
**************************

- Enhancements
  + ✨ Added improvements to error logging
  + Updated for Django bugfix release 2.1.5
- Bug Fixes
  + 🐛 Bugfix for session creation page to handle cases where previous sessions have been cancelled.

************************
1.4.4 (2018-12-27)
************************

- Enhancements
  + 🎨 Improve overall display formatting for RPG Database pages
  + ✨ Improve meta tags for pages
  + ✨ Allow markdown parsing in message of the day values.


************************
1.4.3 (2018-12-20)
************************

- Enhancements
  + 🎨 Improve look and feel of user facing forms.
- Bug Fixes
  + 🐛 Bugfix for community detail views.
  + 🐛 Bugfix for proper timezone display of player available times.


************************
1.4.2 (2018-12-19)
************************

- Bug Fixes
  + 🐛 Backend bugfixes


************************
1.4.0 (2018-12-18)
************************

- Enhancements
  + ✨ Add ability for players to indicate their times available to play.
  + ✨ Added conflict checking functions to session scheduling so that GMs can know about issues with player availability or conflicting games.


************************
1.3.0 (2018-12-15)
************************

- Enhancements
  + ✨ Added in-app messaging between players and GMs.
  + ✨ Added functionality to mute users so their messages are silently ignored.
  + 📚 Added Code of Conduct to site.
  + ✨ Added option to have messages forwarded to user’s email.


**************************
1.2.11 (2018-12-12)
**************************

- Enhancements
  + ✨ Added new admin utilities for managing the RPG Database records


**************************
1.2.10 (2018-12-10)
**************************

- Enhancements
  + 🚀 Migration changes required for moving from Heroku to AWS Elastic Beanstalk.


************************
1.2.6 (2018-12-07)
************************

- Enhancements
  + ✨ Add tooltips for calendar and dashboard view.
  + ✨ Improvements to in-app notifications.


************************
1.2.5 (2018-12-06)
************************

- Enhancements
  + ✨ Add links to games from upcoming sessions in dashboard.
  + ✨ Add links from calendar entries to games.
- Bug Fixes
  + 🐛 Bugfix for upcoming session display in dashboard.
  + 🐛 Fixes for iCal subscription feed.


************************
1.2.3 (2018-12-01)
************************

- Enhancements
  + ✨ Add support for exporting user data.

************************
1.2.2 (2018-11-30)
************************

- Enhancements
  + 🐛 Bugfix for dashboard display


************************
1.2.1 (2018-11-29)
************************

- Enhancements
  + ✨ Add support for side sessions and instant invites.


************************
1.2.0 (2018-11-18)
************************

- Enhancements
  + ✨ Add support for featured images in communities.
  + ✨ Add support for featured images in game postings.
  + ✨ Added live-preview markdown editor with autosave for all user-facing description form fields.
  + ✨ Improvements to Discord syncing.
- Bug Fixes
  + 🐛 Bugfix: Game count for communities.
  + 🐛 Bugfix: Datepicker date formatting conflicts.


************************
1.1.0 (2018-11-15)
************************

- Enhancements
  + ✨ Added a number of critical performance-related features to the backend.
- Bug Fixes
  + 🐛 Major bugfixes for calendar behavior.

************************
1.0.0 (2018-11-10)
************************

- 🎉 Initial Release
