"""Python Flask WebApp Auth0 integration example
"""

import flask
from flask import Flask, Response

from annotations.utils import record_request
from annotations.utils.database import Database, NOT_ALLOWED
from mo_auth.auth0 import Authenticator, verify_user
from mo_auth.flask_session import setup_flask_session
from mo_auth.permissions import Permissions, ROOT_USER, CREATE_TABLE
from mo_dots import coalesce
from mo_logs import constants, startup, Except
from mo_logs.strings import utf82unicode
from mo_threads.threads import register_thread
from mo_times.dates import parse
from pyLibrary.env.flask_wrappers import cors_wrapper, setup_flask_ssl, limit_body, add_flask_rule
from vendor.mo_json import json2value, value2json
from vendor.mo_logs import Log

QUERY_SIZE_LIMIT = 10000

db = None


@register_thread
@cors_wrapper
def _default(path=None):
    return Response(
        b"nothing to see here",
        status=200,
        headers={
            "Content-Type": "text/html"
        }
    )


@register_thread
@cors_wrapper
@limit_body(QUERY_SIZE_LIMIT)
@verify_user
def annotation(user):
    request_body = flask.request.get_data().strip()
    text = utf82unicode(request_body)
    command = json2value(text)

    try:
        record_request(flask.request, command, None, None)
    except Exception as e:
        Log.error("Problem processing request {{request}}")

    result = db.command(command, user)
    return Response(value2json(result), status=200)


if __name__ == "__main__":
    config = startup.read_settings()
    constants.set(config.constants)
    Log.start(config.debug)

    flask_app = Flask(__name__)
    session_manager = setup_flask_session(flask_app, config.session)
    permissions = Permissions(config.permissions)
    Authenticator(flask_app, permissions=permissions, session_manager=session_manager, kwargs=config)

    db = Database(db=config.annotation.db, permissions=permissions)
    add_flask_rule(flask_app, config.annotation.endpoint, annotation)
    add_flask_rule(flask_app, "/", _default)

    # ENSURE SAMPLE DATA IS IN DATABASE
    kyle = permissions.get_or_create_user({"email": "klahnakoski@mozilla.com", "issuer":"google-oauth2|109761343995243343044", "name": "Kyle Lahnakoski"})
    try:
        result = db.query({"from": "sample_data"}, kyle)
    except Exception as e:
        e = Except.wrap(e)
        if NOT_ALLOWED in e:
            permissions.add_permission(kyle, CREATE_TABLE, ROOT_USER)
            db.create({"create": "sample_data"}, kyle)
            db.insert(
                {
                    "insert": "sample_data",
                    "values": [{
                        "revision": "9e3ef2b6a8898c813666bd2e6c5f302dfde87653",
                        "revision12": "9e3ef2b6a889",
                        "push_date": parse("Oct 17, 2019"),
                        "description": "regression"
                    }]
                },
                kyle
            )
        else:
            Log.error("not Expected", cause=e)

    @flask_app.errorhandler(Exception)
    @register_thread
    @cors_wrapper
    def handle_auth_error(ex):
        ex = Except.wrap(ex)
        code = coalesce(ex.params.code, 401)
        Log.note("sending error to client\n{{error}}", {"error": ex})
        return Response(value2json(ex), status=code)

    Log.note("start servers")
    setup_flask_ssl(flask_app, config.flask)
    flask_app.run(**config.flask)


