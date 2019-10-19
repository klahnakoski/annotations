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

from annotations.utils.permissions import TABLE_OPERATIONS, Permissions
from jx_base.expressions import merge_types
from jx_python import jx
from jx_sqlite.container import Container
from jx_sqlite.query_table import QueryTable
from mo_dots import listwrap, join_field, split_field, wrap
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
    SQL,
)
from pyLibrary.sql.sqlite import (
    json_type_to_sqlite_type,
    quote_column,
    quote_value,
    sql_eq,
    quote_list,
)

IDS_TABLE = "meta.all_ids"


class Database:
    @override
    def __init__(self, db):
        self.db = db
        if not db.about(IDS_TABLE):
            with self.db.transaction() as t:
                t.execute(
                    "CREATE TABLE "
                    + quote_column(IDS_TABLE)
                    + sql_iso(
                        sql_list([SQL("_id INTEGER PRIMARY KEY"), SQL('"table" TEXT')])
                    )
                )
                t.execute(
                    SQL_INSERT
                    + quote_column(IDS_TABLE)
                    + SQL_VALUES
                    + quote_list([0, IDS_TABLE])
                )
        self.container = Container(db)
        self.permissions = Permissions(self, db)

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
        keys = list(keys)
        try:
            with self.db.transaction() as t:
                exists = t.query(
                    SQL_SELECT
                    + "name"
                    + SQL_FROM
                    + "sqlite_master"
                    + SQL_WHERE
                    + sql_eq(type="table", name=table_name)
                )
                if not exists.data:
                    columns = [
                        (col.name, json_type_to_sqlite_type[merge_types(descs.type)])
                        for col, descs in jx.groupby(
                            [
                                {"name": k, "type": python_type_to_json_type[type(v)]}
                                for r in records
                                for k, v in r.items()
                                if k != "_id"
                            ],
                            "name",
                        )
                    ]
                    t.execute(
                        "CREATE TABLE "
                        + quote_column(table_name)
                        + sql_iso(
                            sql_list(
                                [SQL("_id INTEGER PRIMARY KEY")]
                                + [quote_column(n) + " " + t for n, t in columns]
                            )
                        )
                    )

                t.execute(
                    SQL_INSERT
                    + quote_column(IDS_TABLE)
                    + SQL_VALUES
                    + sql_list([quote_list([r._id, table_name]) for r in records])
                )

                t.execute(
                    SQL_INSERT
                    + quote_column(table_name)
                    + sql_iso(sql_list(map(quote_column, keys)))
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
                    + sql_eq(_id=id)
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
                + sql_eq(_id=id)
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
        command = wrap(command)
        resource = self.permissions.find_resource(".", "insert")
        allowance = self.permissions.allow_resource(user, resource)

        if not allowance:
            Log.error("not allowed")

        table_name = command.create
        root_name = join_field(split_field(table_name)[0:1])
        try:
            with self.db.transaction() as t:
                result = t.query(
                    SQL_SELECT
                    + "name"
                    + SQL_FROM
                    + "sqlite_master"
                    + SQL_WHERE
                    + sql_eq(type="table", name=root_name)
                )
                if result.data:
                    Log.error("table {{table}} exists", table=root_name)

        except Exception as e:
            Log.error("problem with container creation", cause=e)

        self.permissions.create_table_resource(root_name, user)

    def insert(self, command, user):
        command = wrap(command)
        table_name = command.insert
        root_name = join_field(split_field(table_name)[0:1])
        resource = self.permissions.find_resource(root_name, "insert")
        allowance = self.permissions.allow_resource(user, resource)

        if not allowance:
            Log.error("not allowed")

        QueryTable(table_name, self.container).insert(command['values'])

    def update(self, command, user):
        command = wrap(command)
        table_name = command.update
        root_name = join_field(split_field(table_name)[0:1])
        resource = self.permissions.find_resource(root_name, "update")
        allowance = self.permissions.allow_resource(user, resource)

        if not allowance:
            Log.error("not allowed")

        QueryTable(table_name, self.container).update(command)

    def query(self, command, user):
        command = wrap(command)
        table_name = command["from"]
        root_name = join_field(split_field(table_name)[0:1])
        resource = self.permissions.find_resource(root_name, "from")
        allowance = self.permissions.allow_resource(user, resource)

        if not allowance:
            Log.error("not allowed")

        QueryTable(table_name, self.container).query(command)
