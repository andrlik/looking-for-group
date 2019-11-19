from django.dispatch import Signal

user_specific_notes_displayed = Signal(providing_args=["user", "note_list", "request"])
