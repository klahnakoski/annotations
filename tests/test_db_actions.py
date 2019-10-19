# encoding: utf-8
#
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#

from __future__ import absolute_import, division, unicode_literals

from annotations.utils.database import Database
from annotations.utils.permissions import ROOT_USER
from mo_logs import startup, constants, Log
from mo_testing.fuzzytestcase import FuzzyTestCase
from pyLibrary.sql.sqlite import Sqlite


class TestDBActions(FuzzyTestCase):

    def test_create_new_table(self):
        db = Database(db=Sqlite(CONFIG.db))

        # MAKE A USER
        user = db.permissions.get_or_create_user({"claims": {"email": "klahnakoski@mozilla.com"}})

        # FIND RESOURCE THAT REPRESENTS CREATION OF TABLE
        make_table = db.permissions.get_resource(".", "insert")

        # GIVE USER PERMISSIONS TO MAKE TABLE
        db.permissions.add_permission(user, make_table, ROOT_USER)

        # HAVE USER MAKE A TABLE
        db.create({"create": "temp"}, user)

        # ADD SOME DATA
        db.insert(
            {
                "insert": "temp",
                "values": [
                    {"example": 10},
                    {"example": "10"}
                ]
            },
            user
        )

        # QUERY OUT DATA
        result = db.query({
            "from": "temp",
            "select": "example"
        }, user)

        self.assertAlmostEqual(
            result,
            [
                {"example": 10},
                {"example": "10"}
            ]
        )


CONFIG = startup.read_settings(filename="tests/config.json")
constants.set(CONFIG.constants)
Log.start(CONFIG.debug)
