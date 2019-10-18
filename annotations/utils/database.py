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

from annotations.utils.permissions import TABLE_OPERATIONS
from jx_base.expressions import merge_types
from jx_python import jx
from jx_sqlite.container import IDS_TABLE, Container
from jx_sqlite.query_table import QueryTable
from mo_dots import listwrap, Null, join_field, split_field
from mo_json import python_type_to_json_type
from mo_kwargs import override
from mo_logs import Log
from pyLibrary.sql import (
    sql_iso,
    sql_list,
    SQL_VALUES,
    SQL_INSERT,
    SQL_SELECT,
    SQL_FROM,
    SQL_WHERE,
    SQL_STAR,
)
from pyLibrary.sql.sqlite import json_type_to_sqlite_type, quote_column, quote_value


class Database:
    @override
    def __init__(self, db):
        self.db = db
        self.container = Container(db)
        self.permissions = Null

        if not self.db.about(IDS_TABLE):
            self.insert(IDS_TABLE, {"_id": 0, "table": IDS_TABLE})

    def raw_insert(self, table_name, records):
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

        try:
            with self.db.transaction() as t:
                exists = t.query(
                    SQL_SELECT
                    + "name"
                    + SQL_FROM
                    + "sqlite_master"
                    + SQL_WHERE
                    + "type='table' AND name="
                    + quote_column(table_name)
                )
                if not exists:
                    columns = [
                        (k, json_type_to_sqlite_type[merge_types(types)])
                        for k, types in jx.groupby(
                            [
                                (k, python_type_to_json_type[type(v)])
                                for r in records
                                for k, v in r.items()
                            ],
                            0,
                        )
                    ]
                    t.execute(
                        "CREATE TABLE "
                        + quote_column(table_name)
                        + sql_iso(
                            sql_list(quote_column(n) + " " + t for n, t in columns)
                        )
                    )

                    t.execute(
                        "CREATE UNIQUE INDEX "
                        + quote_column(table_name + ".id_index")
                        + " ON "
                        + quote_column(table_name)
                        + sql_iso("_id")
                    )

                t.execute(
                    SQL_INSERT
                    + quote_column(IDS_TABLE)
                    + SQL_VALUES
                    + sql_list(sql_iso(sql_list([r._id, table_name])) for r in records)
                )

                t.execute(
                    SQL_INSERT
                    + quote_column(table_name)
                    + sql_iso(sql_list([quote_column(k) for k in keys]))
                    + SQL_VALUES
                    + sql_list(
                        sql_iso(sql_list([quote_value(r[k]) for k in keys]))
                        for r in records
                    )
                )

        except Exception as e:
            Log.error(
                "problem with inserting records: {{records}}", records=records, cause=e
            )

    def get(self, id):
        """
        GET OBJECT BY ID, OVER ALL TABLES
        :param id:
        :return: RECORD FROM ANY OF THE TABLES
        """
        with self.db.transaction() as t:
            table_name = (
                t.query(
                    SQL_SELECT
                    + "table"
                    + SQL_FROM
                    + quote_column(IDS_TABLE)
                    + SQL_WHERE
                    + "_id="
                    + quote_value(id)
                )
                .first()
                .table
            )

            return t.query(
                SQL_SELECT
                + SQL_STAR
                + SQL_FROM
                + quote_column(table_name)
                + SQL_WHERE
                + "_id="
                + quote_value(id)
            )

    def command(self, command, user):
        # PERFORM PERMISSION CHECK
        for op in TABLE_OPERATIONS:
            table_name = command[op]
            if table_name == None:
                continue

            if self.permissions:
                root_table = join_field(split_field(table_name)[:1])
                resource = self.permissions.find_resource(root_table, op)
                allowance = self.permissions.allow_resource(user, resource)
                if allowance:
                    # EXECUTE
                    getattr(self, op)(command, user)
        Log.error("Not allowed")

    def create(self, command, user):
        resource = self.permissions.find_resource(".", "update")
        allowance = self.permissions.allow_resource(user, resource.id)

        if not allowance:
            Log.error("not allowed")

        table_name = command.create
        root_name = join_field(split_field(table_name)[0:1])
        try:
            with self.db.transaction() as t:
                exists = t.query(
                    SQL_SELECT
                    + "name"
                    + SQL_FROM
                    + "sqlite_master"
                    + SQL_WHERE
                    + "type='table' AND name="
                    + quote_column(root_name)
                )
                if exists:
                    Log.error("table {{table}} exists", table=root_name)

        except Exception as e:
            Log.error("problem with container creation", cause=e)

        self.permissions.create_table_resource(root_name, user)

    def insert(self, command, user):
        table_name = command["insert"]
        root_name = join_field(split_field(table_name)[0:1])
        resource = self.permissions.find_resource(root_name, "insert")
        allowance = self.permissions.allow_resource(user, resource.id)

        if not allowance:
            Log.error("not allowed")

        QueryTable(table_name, self.container).insert(command)

    def update(self, command, user):
        table_name = command["update"]
        root_name = join_field(split_field(table_name)[0:1])
        resource = self.permissions.find_resource(root_name, "update")
        allowance = self.permissions.allow_resource(user, resource.id)

        if not allowance:
            Log.error("not allowed")

        QueryTable(table_name, self.container).update(command)

    def query(self, command, user):
        table_name = command["from"]
        root_name = join_field(split_field(table_name)[0:1])
        resource = self.permissions.find_resource(root_name, "from")
        allowance = self.permissions.allow_resource(user, resource.id)

        if not allowance:
            Log.error("not allowed")

        QueryTable(table_name, self.container).query(command)
