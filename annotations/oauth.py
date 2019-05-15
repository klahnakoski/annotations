"""Python Flask WebApp Auth0 integration example
"""
from functools import wraps

from flask import redirect, session, url_for
from six.moves.urllib.parse import urlencode

import constants


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if constants.PROFILE_KEY not in session:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated


def setup(auth0, CONFIG):
    def login():
        return auth0.authorize_redirect(
            redirect_uri=CONFIG.annotation.auth0.callback_url,
            audience=CONFIG.annotation.auth0.audience,
        )

    def logout():
        session.clear()
        params = {
            "returnTo": url_for("home", _external=True),
            "client_id": CONFIG.annotation.auth0.client.id,
        }
        return redirect(auth0.api_base_url + "/v2/logout?" + urlencode(params))

    def callback():
        auth0.authorize_access_token()
        resp = auth0.get("userinfo")
        userinfo = resp.json()

        session[constants.JWT_PAYLOAD] = userinfo
        session[constants.PROFILE_KEY] = {
            "user_id": userinfo["sub"],
            "name": userinfo["name"],
            "picture": userinfo["picture"],
        }
        return redirect("/dashboard")

    return login, logout, callback
