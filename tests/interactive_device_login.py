# encoding: utf-8
#
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#

from __future__ import absolute_import, division, unicode_literals

import os
import sys

from mo_auth.client import Auth0Client
from mo_files import URL
from mo_json import value2json
from mo_logs import startup, Log
from mo_testing.fuzzytestcase import FuzzyTestCase
from mo_threads import Process

PYTHONPATH = os.environ['PYTHONPATH']
SETUP_SERVICE = False


class TestDeviceLogin(FuzzyTestCase):
    """
    THIS TEST IS INTERACTIVE,
    IT REQUIRES YOU TO FOLLOW THE LINK, AND LOGIN
    """

    @classmethod
    def setUpClass(cls):
        TestDeviceLogin.config = startup.read_settings(filename="tests/config/client.json")
        if SETUP_SERVICE:
            cls.app_process = Process(
                "annotation server", [sys.executable, "annotations/server.py", "--config=tests/config/server.json"],
                env={str("PYTHONPATH"): PYTHONPATH},
                debug=True,
                shell=True
            )
            for line in cls.app_process.stderr:
                if line.startswith(" * Running on "):
                    break

    @classmethod
    def tearDownClass(cls):
        if SETUP_SERVICE:
            cls.app_process.stop()
            cls.app_process.join(raise_on_error=False)

    def test_login(self):
        client = Auth0Client(TestDeviceLogin.config.client)
        client.login()
        response = client.request(
            "POST",
            URL(client.config.service, path=TestDeviceLogin.config.annotation.endpoint),
            headers={"Content-Type": "application/json"},
            data=value2json({
                "from": "sample_data",
                "where": {"eq": {"revision12": "9e3ef2b6a889"}}
            })
        )

        Log.note("response {{json}}", json=response.json())


