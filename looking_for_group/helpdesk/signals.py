from django.dispatch import Signal

issue_state_changed = Signal(
    providing_args=["issue", "user", "old_status", "new_status"]
)
