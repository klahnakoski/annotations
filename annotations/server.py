"""Python Flask WebApp Auth0 integration example
"""
import json

from authlib.flask.client import OAuth
import flask
from flask import Flask, Response, render_template, session

from annotations.oauth import requires_auth
from annotations.utils import record_request
import constants
from mo_logs import startup
from mo_logs.strings import unicode2utf8, utf82unicode
from mo_threads.threads import RegisterThread
from vendor.mo_files import File
from vendor.mo_json import json2value
from vendor.mo_logs import Log

CONFIG = None

QUERY_SIZE_LIMIT = 10000
BLANK = unicode2utf8(File("public/error.html").read())

app = None


def home():
    return render_template("home.html")


@requires_auth
def dashboard():
    return render_template(
        "dashboard.html",
        userinfo=session[constants.PROFILE_KEY],
        userinfo_pretty=json.dumps(session[constants.JWT_PAYLOAD], indent=4),
    )


@requires_auth
def annotation():
    with RegisterThread():
        if flask.request.headers.get("content-length", "") in ["", "0"]:
            # ASSUME A BROWSER HIT THIS POINT, SEND text/html RESPONSE BACK
            return Response(BLANK, status=400, headers={"Content-Type": "text/html"})
        elif int(flask.request.headers["content-length"]) > QUERY_SIZE_LIMIT:
            Log.error("Query is too large to parse")

        request_body = flask.request.get_data().strip()
        text = utf82unicode(request_body)
        data = json2value(text)

        try:
            record_request(flask.request, data, None, None)
        except Exception as e:
            Log.error("Problem processing request {{request}}")


if __name__ == "__main__":
    CONFIG = startup.read_settings()
    constants.set(CONFIG.constants)
    Log.start(CONFIG.debug)

    app = Flask(
        __name__, static_url_path="/public", static_folder="./public", root_path="."
    )
    app.secret_key = constants.SECRET_KEY
    app.debug = True

    oauth = OAuth(app)

    auth0 = oauth.register(
        "auth0",
        client_id=CONFIG.annotation.auth0.client.id,
        client_secret=CONFIG.annotation.auth0.secret,
        api_base_url=CONFIG.annotation.auth0.domain,
        access_token_url=CONFIG.annotation.auth0.domain + "/oauth/token",
        authorize_url=CONFIG.annotation.auth0.domain + "/authorize",
        client_kwargs={"scope": "openid profile"},
    )

    app.add_url_rule("/dashboard", None, dashboard)
    app.add_url_rule("/home", None, home)
    app.add_url_rule("/annotation", None, annotation)

    login, logout, callback = oauth.setup(auth0, CONFIG)

    app.add_url_rule("/callback", None, callback)
    app.add_url_rule("/login", None, login)
    app.add_url_rule("/logout", None, logout)

    app.run(
        **{
            "host": "0.0.0.0",
            "port": 443,
            "debug": False,
            "threaded": True,
            "processes": 1,
            "ssl_context": "adhoc",
        }
    )
