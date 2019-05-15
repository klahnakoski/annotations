# encoding: utf-8
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Author: Kyle Lahnakoski (kyle@lahnakoski.com)
#
from __future__ import absolute_import, division, unicode_literals

from mo_dots import wrap
from mo_files import File
from mo_json import value2json
from mo_logs import Log
from mo_times.dates import Date

request_log_queue = None

OVERVIEW = File("active_data/public/index.html").read()


def record_request(request, query_, data, error):
    try:
        if request_log_queue == None:
            return

        if data and len(data) > 10000:
            data = data[:10000]

        log = wrap(
            {
                "timestamp": Date.now(),
                "http_user_agent": request.headers.get("user_agent"),
                "http_accept_encoding": request.headers.get("accept_encoding"),
                "path": request.headers.environ["werkzeug.request"].full_path,
                "content_length": request.headers.get("content_length"),
                "remote_addr": request.remote_addr,
                "query_text": value2json(query_),
                "data": data,
                "error": value2json(error),
            }
        )
        log["from"] = request.headers.get("from")
        request_log_queue.add({"value": log})
    except Exception as e:
        Log.warning("Can not record", cause=e)
