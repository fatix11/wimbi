from django.http import HttpRequest

from .dev_users import DevUser, find_dev_user

SESSION_KEY = "wimbi_user_email"


def login_dev_user(request: HttpRequest, email: str) -> DevUser | None:
    user = find_dev_user(email)
    if user is not None:
        request.session[SESSION_KEY] = user.email
    return user


def logout(request: HttpRequest) -> None:
    request.session.pop(SESSION_KEY, None)


def get_session_user(request: HttpRequest) -> DevUser | None:
    email = request.session.get(SESSION_KEY)
    if not email:
        return None
    return find_dev_user(email)
