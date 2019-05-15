"""Python Flask WebApp Auth0 integration example
"""
from http.client import HTTPException
import json

import flask
from flask import Flask, Response, render_template, session
from flask.json import jsonify

from annotations import oauth
from annotations.oauth import JWT_PAYLOAD, PROFILE_KEY
from annotations.utils import record_request
from mo_logs import constants, startup
from mo_logs.strings import unicode2utf8, utf82unicode
from mo_threads.threads import register_thread
from vendor.mo_files import File
from vendor.mo_json import json2value
from vendor.mo_logs import Log

QUERY_SIZE_LIMIT = 10000
ERROR_CONTENT = unicode2utf8(File("public/error.html").read())


@register_thread
def home():
    return render_template("home.html")


@register_thread
def dashboard():
    return render_template(
        "dashboard.html",
        userinfo=session[PROFILE_KEY],
        userinfo_pretty=json.dumps(session[JWT_PAYLOAD], indent=4),
    )


@register_thread
def annotation():
    if flask.request.headers.get("content-length", "") in ["", "0"]:
        # ASSUME A BROWSER HIT THIS POINT, SEND text/html RESPONSE BACK
        return Response(ERROR_CONTENT, status=400, headers={"Content-Type": "text/html"})
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
    app.secret_key = CONFIG.annotation.secret_key
    app.debug = True

    requires_auth, login, logout, callback = oauth.setup(app, CONFIG.annotation.auth0)

    app.add_url_rule("/home", None, requires_auth(home))
    app.add_url_rule("/dashboard", None, requires_auth(dashboard))
    app.add_url_rule("/annotation", None, requires_auth(annotation))

    app.add_url_rule("/callback", None, callback)
    app.add_url_rule("/login", None, login)
    app.add_url_rule("/logout", None, logout)


    @app.errorhandler(Exception)
    def handle_auth_error(ex):
        response = jsonify(message=str(ex))
        response.status_code = (ex.code if isinstance(ex, HTTPException) else 500)
        return response

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
