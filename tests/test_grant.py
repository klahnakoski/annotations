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
from tests import TEST_DATA


class TestDBActions(FuzzyTestCase):

    def __init__(self, *args, **kwargs):
        FuzzyTestCase.__init__(self, *args, **kwargs)
        self.db = None
        self.table = None
        self.user = None

    def setUp(self):
        """
        ENSURE WE HAVE A USER AND A TABLE: WHICH WE TRY TO CRACK
        """
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
                "values": TEST_DATA
            },
            user
        )

        self.db = db
        self.user = user
        self.table = "temp"

    def try_to_insert(self, new_user):
        self.db.insert({"insert": self.table, "values": [{"val": 20}]}, new_user)

        # ENSURE INSERT WORKS (USING OWNER)
        result = self.db.query({"from": self.table, "select": "val"}, self.user)
        self.assertEqual(result.data, {10, 20, "10"})

    def try_to_update(self, new_user):
        self.db.update({"update": self.table, "set": {"val": 10}}, new_user),

        # ENSURE UPDATE WORKS (USING OWNER)
        self.assertEqual(
            self.db.query({"from": self.table}, self.user).data,
            [{"val": 10}, {"val": 10}]
        )

    def try_to_query(self, new_user):
        self.assertEqual(
            self.db.query({"from": self.table, "select": ["val"]}, new_user).data,
            TEST_DATA
        )

    def test_can_insert(self):
        # MAKE A USER
        p = self.db.permissions
        new_user = p.get_or_create_user({"claims": {"email": "new_user@mozilla.com"}})
        resource = p.find_resource(table=self.table, operation="insert")

        p.add_permission(user=new_user, resource=resource, owner=self.user)

        self.try_to_insert(new_user)

    def test_can_update(self):
        p = self.db.permissions
        new_user = p.get_or_create_user({"claims": {"email": "new_user@mozilla.com"}})
        resource = p.find_resource(table=self.table, operation="update")

        p.add_permission(user=new_user, resource=resource, owner=self.user)

        self.try_to_update(new_user)

    def test_can_query(self):
        p = self.db.permissions
        new_user = p.get_or_create_user({"claims": {"email": "new_user@mozilla.com"}})
        resource = p.find_resource(table=self.table, operation="from")

        p.add_permission(user=new_user, resource=resource, owner=self.user)

        self.try_to_query(new_user)


CONFIG = startup.read_settings(filename="tests/config.json")
constants.set(CONFIG.constants)
Log.start(CONFIG.debug)
