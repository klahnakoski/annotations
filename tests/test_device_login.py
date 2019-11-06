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
from mo_logs import startup, constants, Log
from mo_testing.fuzzytestcase import FuzzyTestCase
from mo_threads import Process

PYTHONPATH = os.environ['PYTHONPATH']

config = startup.read_settings()
constants.set(config.constants)
Log.start(config.debug)


class TestDeviceLogin(FuzzyTestCase):

    @classmethod
    def setUpClass(cls):
        pass
        # cls.app_process = Process(
        #     "annotation server", [sys.executable, "annotations/server.py"],
        #     env={str("PYTHONPATH"): PYTHONPATH},
        #     debug=True,
        #     shell=True
        # )
        # for line in cls.app_process.stderr:
        #     if line.startswith(" * Running on "):
        #         break

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "app_process"):
            cls.app_process.stop()
            cls.app_process.join(raise_on_error=False)

    def test_login(self):
        client = Auth0Client(config.client)
        client.login()
        response = client.request(
            "POST",
            URL(client.config.service, path=config.annotation.endpoint),
            headers={"Content-Type": "application/json"},
            data=value2json({
                "from": "sample_data",
                "where": {"eq": {"revision12": "9e3ef2b6a889"}}
            })
        )

        Log.note("response {{json}}", json=response.json())


