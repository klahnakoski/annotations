# encoding: utf-8
#
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#

from __future__ import absolute_import, division, unicode_literals

from jx_sqlite.container import Container
from mo_logs import startup, constants, Log
from mo_testing.fuzzytestcase import FuzzyTestCase
from pyLibrary.sql.sqlite import Sqlite


class TestAlerts(FuzzyTestCase):

    def _add_alert(self):
        pass

    def create_new_table(self):
        c = Container(db=Sqlite(CONFIG.db))

        pass

    def test_get_alerts_by_revision(self):
        pass


CONFIG = startup.read_settings(filename="tests/config.json")
constants.set(CONFIG.constants)
Log.start(CONFIG.debug)
