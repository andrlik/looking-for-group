"""
An app for managing release notes. It reads in a configured release notes file from the source directory
(so that you don't have to do double documentation), then generates JSON and Atom feeds based on those.
It also has the ability to check to see if a given user has already seen a release notes entry which can be
 used to selectively trigger showing them the relevant release notes on login.
"""
