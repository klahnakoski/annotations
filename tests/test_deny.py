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
        self.assertRaises(
            "not allowed",
            lambda: self.db.insert({"insert": self.table, "values": {"val": 10}}, new_user)
        )

    def try_to_update(self, new_user):
        self.assertRaises(
            "not allowed",
            lambda: self.db.update({"update": self.table, "set": {"val": 10}}, new_user)
        )

    def try_to_query(self, new_user):
        self.assertRaises(
            "not allowed",
            lambda: self.db.query({"from": self.table}, new_user)
        )

    def test_can_not_insert(self):
        db = self.db

        # MAKE A USER
        new_user = db.permissions.get_or_create_user({"claims": {"email": "cracker@mozilla.com"}})
        self.try_to_insert(new_user)

        query_resource = db.permissions.get_resource(self.table, "from")
        db.permissions.add_permission(user=new_user, resource=query_resource, owner=self.user)
        self.try_to_insert(new_user)

        query_resource = db.permissions.get_resource(self.table, "update")
        db.permissions.add_permission(user=new_user, resource=query_resource, owner=self.user)
        self.try_to_insert(new_user)

    def test_can_not_update(self):
        db = self.db

        # MAKE A USER
        new_user = db.permissions.get_or_create_user({"claims": {"email": "cracker@mozilla.com"}})
        self.try_to_update(new_user)

        query_resource = db.permissions.get_resource(self.table, "from")
        db.permissions.add_permission(user=new_user, resource=query_resource, owner=self.user)
        self.try_to_update(new_user)

        query_resource = db.permissions.get_resource(self.table, "insert")
        db.permissions.add_permission(user=new_user, resource=query_resource, owner=self.user)
        self.try_to_update(new_user)

    def test_can_not_query(self):
        db = self.db

        # MAKE A USER
        new_user = db.permissions.get_or_create_user({"claims": {"email": "cracker@mozilla.com"}})
        self.try_to_query(new_user)

        query_resource = db.permissions.get_resource(self.table, "insert")
        db.permissions.add_permission(user=new_user, resource=query_resource, owner=self.user)
        self.try_to_query(new_user)

        query_resource = db.permissions.get_resource(self.table, "update")
        db.permissions.add_permission(user=new_user, resource=query_resource, owner=self.user)
        self.try_to_query(new_user)


CONFIG = startup.read_settings(filename="tests/config.json")
constants.set(CONFIG.constants)
Log.start(CONFIG.debug)
