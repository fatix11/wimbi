"""Makes the current SessionUser available to every template as
`session_user`, so base.html's sidebar doesn't need every view to pass it
explicitly."""

from .session import get_session_user


def session_user(request):
    return {"session_user": get_session_user(request)}
