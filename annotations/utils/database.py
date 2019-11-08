# encoding: utf-8
#
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Author: Kyle Lahnakoski (kyle@lahnakoski.com)
#

from __future__ import absolute_import, division, unicode_literals

from jx_base.expressions import merge_types
from jx_python import jx
from jx_sqlite.container import Container
from jx_sqlite.query_table import QueryTable
from mo_auth.permissions import TABLE_OPERATIONS
from mo_dots import listwrap, join_field, split_field, wrap, is_data
from mo_json import python_type_to_json_type
from mo_kwargs import override
from mo_logs import Log
from pyLibrary.sql.sqlite import (
    json_type_to_sqlite_type,
    sql_query,
    sql_create,
    sql_insert,
    Sqlite)

IDS_TABLE = "meta.all_ids"
OK = {"ok": True}
NOT_ALLOWED = "{{user}} Not allowed"


class Database:
    @override
    def __init__(self, db, permissions, kwargs):
        self.db = db
        if is_data(db):
            self.db = Sqlite(db)

        if not isinstance(self.db, Sqlite):
            Log.error("Expecting Sqlite database config")

        if not self.db.about(IDS_TABLE):
            with self.db.transaction() as t:
                t.execute(
                    sql_create(
                        IDS_TABLE, {"_id": "INTEGER PRIMARY KEY", "table": "TEXT"}
                    )
                )
                t.execute(sql_insert(IDS_TABLE, {"_id": 0, "table": IDS_TABLE}))
        self.container = Container(db)
        self.permissions = permissions

    def safe_insert(self, table_name, records):
        """
        SIMPLIFY ADDING RECORDS INTO DATABASE

        :param table_name:
        :param records:
        """
        records = listwrap(records)
        keys = {"_id"}
        for r in records:
            keys.update(r.keys())
            if r._id == None:
                r._id = self.container.next_uid()
        keys = list(keys)
        try:
            with self.db.transaction() as t:
                exists = t.query(
                    sql_query(
                        {
                            "select": "name",
                            "from": "sqlite_master",
                            "where": {"eq": {"type": "table", "name": table_name}},
                        }
                    )
                )
                if not exists.data:
                    columns = {
                        col.name: json_type_to_sqlite_type[merge_types(descs.type)]
                        for col, descs in jx.groupby(
                            [
                                {"name": k, "type": python_type_to_json_type[type(v)]}
                                for r in records
                                for k, v in r.items()
                                if k != "_id"
                            ],
                            "name",
                        )
                    }
                    columns["_id"] = "INTEGER PRIMARY KEY"
                    t.execute(sql_create(table_name, columns))

                t.execute(
                    sql_insert(
                        IDS_TABLE,
                        [{"_id": r._id, "table": table_name} for r in records],
                    )
                )

                t.execute(sql_insert(table_name, records))

        except Exception as e:
            Log.error(
                "problem with inserting records: {{records}}", records=records, cause=e
            )

    def command(self, command, user):
        # PERFORM PERMISSION CHECK
        command = wrap(command)
        user = wrap(user)
        for op in TABLE_OPERATIONS:
            table_name = command[op]
            if table_name == None:
                continue

            if self.permissions:
                root_table = join_field(split_field(table_name)[:1])
                resource = self.permissions.find_resource(root_table, op)
                allowance = self.permissions.verify_allowance(user, resource)
                if allowance:
                    # EXECUTE
                    return getattr(self, op)(command, user)
        Log.error(NOT_ALLOWED, user=user.email)

    def create(self, command, user):
        command = wrap(command)
        resource = self.permissions.find_resource(".", "insert")
        allowance = self.permissions.verify_allowance(user, resource)

        if not allowance:
            Log.error(NOT_ALLOWED)

        table_name = command.create
        root_name = join_field(split_field(table_name)[0:1])
        try:
            with self.db.transaction() as t:
                result = t.query(
                    sql_query(
                        {
                            "select": "name",
                            "from": "sqlite_master",
                            "where": {"eq": {"type": "table", "name": root_name}},
                        }
                    )
                )
                if result.data:
                    Log.error("table {{table}} exists", table=root_name)

        except Exception as e:
            Log.error("problem with container creation", cause=e)

        self.container.create_or_replace_facts(root_name)
        self.permissions.create_table_resource(root_name, user)
        return OK

    def insert(self, command, user):
        command = wrap(command)
        table_name = command.insert
        root_name = join_field(split_field(table_name)[0:1])
        resource = self.permissions.find_resource(root_name, "insert")
        allowance = self.permissions.verify_allowance(user, resource)

        if not allowance:
            Log.error(NOT_ALLOWED, user=user)

        num_rows = len(command['values'])
        QueryTable(table_name, self.container).insert(command["values"])
        return {"ok": True, "count": num_rows}

    def update(self, command, user):
        command = wrap(command)
        table_name = command['update']
        root_name = join_field(split_field(table_name)[0:1])
        resource = self.permissions.find_resource(root_name, "update")
        allowance = self.permissions.verify_allowance(user, resource)

        if not allowance:
            Log.error(NOT_ALLOWED, user=user)

        QueryTable(table_name, self.container).update(command)
        return {"ok": True}

    def query(self, command, user):
        command = wrap(command)
        table_name = command["from"]
        root_name = join_field(split_field(table_name)[0:1])
        resource = self.permissions.find_resource(root_name, "from")
        if not resource:
            Log.error(NOT_ALLOWED, user=user)
        allowance = self.permissions.verify_allowance(user, resource)

        if not allowance:
            Log.error(NOT_ALLOWED, user=user)

        return QueryTable(table_name, self.container).query(command)

setattr(Database, "from", Database.query)