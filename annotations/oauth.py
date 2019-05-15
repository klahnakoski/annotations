"""Python Flask WebApp Auth0 integration example
"""

from authlib.flask.client import OAuth
from flask import redirect, session, url_for
from six.moves.urllib.parse import urlencode

from mo_future import decorate
from mo_threads.threads import register_thread

PROFILE_KEY = "profile"
JWT_PAYLOAD = "jwt_payload"


def setup(app, config):

    oauth = OAuth(app)

    auth0 = oauth.register(
        "auth0",
        client_id=config.client.id,
        client_secret=config.client.secret,
        api_base_url=config.domain,
        access_token_url=config.domain + "/oauth/token",
        authorize_url=config.domain + "/authorize",
        client_kwargs={"scope": "openid profile"},
    )

    def requires_auth(f):
        @decorate(f)
        def decorated(*args, **kwargs):
            if PROFILE_KEY not in session:
                return redirect("/login")
            return f(*args, **kwargs)

        return decorated

    @register_thread
    def login():
        return auth0.authorize_redirect(
            redirect_uri=config.callback,
            audience=config.audience
        )

    @register_thread
    def logout():
        session.clear()
        params = {
            "returnTo": url_for("home", _external=True),
            "client_id": config.client.id,
        }
        return redirect(auth0.api_base_url + "/v2/logout?" + urlencode(params))

    @register_thread
    def callback():
        auth0.authorize_access_token()
        resp = auth0.get("userinfo")
        userinfo = resp.json()

        session[JWT_PAYLOAD] = userinfo
        session[PROFILE_KEY] = {
            "user_id": userinfo["sub"],
            "name": userinfo["name"],
            "picture": userinfo["picture"],
        }
        return redirect("/dashboard")

    return requires_auth, login, logout, callback
