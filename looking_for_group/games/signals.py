from django.dispatch import Signal

player_kicked = Signal(providing_args=["player"])  # pragma: no cover
player_left = Signal(providing_args=["player"])  # pragma: no cover
