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

from typing import Dict

from jx_sqlite.namespace import Namespace
from mo_future import text_type

from jx_sqlite import Container
from mo_kwargs import override

from jx_base.expressions import merge_types
from jx_python import jx
from mo_dots import listwrap, Null, join_field, split_field
from mo_json import python_type_to_json_type
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
from pyLibrary.sql.sqlite import (
    Sqlite,
    json_type_to_sqlite_type,
    quote_column,
    quote_value,
)

IDS = "meta.all_ids"
COMMANDS = ["create", "insert", "update", "from"]


class Database(Sqlite):
    @override
    def __init__(
        self,
        filename=None,
        db=None,
        get_trace=None,
        upgrade=True,
        load_functions=False,
        kwargs=None,
    ):
        Sqlite.__init__(kwargs)
        self.insert(IDS, {"_id": 0, "table": IDS})
        self.insert("meta.about", {"version": 1, "next_id": 1})
        self.id = self._gen_ids()
        self.permissions = Null
        self.ns = Namespace(self)
        self._load_facts()

    def _load_facts(self):



    def _gen_ids(self):
        while True:
            with self.db.transaction() as t:
                top_id = (
                    t.execute("SELECT next_id FROM " + quote_column("meta.about"))
                    .first()
                    .next_id
                )
                max_id = top_id + 1000
                t.execute(
                    "UPDATE "
                    + quote_column("meta.about")
                    + " SET next_id="
                    + quote_value(max_id)
                )
            while top_id < max_id:
                yield top_id
                top_id += 1

    def insert(self, table_name, records):
        """
        :param table_name:
        :param records:
        """
        records = listwrap(records)
        keys = {"_id"}
        for r in records:
            keys.update(r.keys())
            if r._id == None:
                r._id = self.id.__next__()

        keys = list({r.keys() for r in records})

        try:
            with self.transaction() as t:
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
                    + quote_column(IDS)
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
                    + quote_column(IDS)
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
        op = ""
        for c in COMMANDS:
            table_name = command[c]
            if table_name == None:
                continue

            op = c
            if self.permissions:
                root_table = join_field(split_field(table_name)[:1])
                resource = self.permissions.find_resource(root_table, c)
                allowance = self.permissions.allow_resource(user, resource)
                if allowance:
                    break
        else:
            Log.error("Not allowed")

        # EXECUTE
        getattr(self, op)(command, user)

    def create(self, command, user):
        resource = self.permissions.find_resource(".", "update")
        allowance = self.permissions.allow_resource(user, resource.id)

        if not allowance:
            Log.error("not allowed")

        # CREATE TABLE
        table_name = command.create
        root_name = join_field(split_field(table_name)[0:1])
        try:
            with self.transaction() as t:
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

                self.facts[root_name] = Container(table_name, self)

        except Exception as e:
            Log.error("problem with container creation", cause=e)


    def insert(self, command, user):
        table_name = command['insert']
        root_name = join_field(split_field(table_name)[0:1])
        resource = self.permissions.find_resource(root_name, "insert")
        allowance = self.permissions.allow_resource(user, resource.id)

        if not allowance:
            Log.error("not allowed")

        self.facts[root_name].insert(command)

    def update(self, command, user):
        table_name = command.update
        root_name = join_field(split_field(table_name)[0:1])
        resource = self.permissions.find_resource(root_name, "update")
        allowance = self.permissions.allow_resource(user, resource.id)

        if not allowance:
            Log.error("not allowed")

        self.facts[root_name].update(command)

    def query(self, command, user):
        table_name = command['from']
        root_name = join_field(split_field(table_name)[0:1])
        resource = self.permissions.find_resource(root_name, "from")
        allowance = self.permissions.allow_resource(user, resource.id)

        if not allowance:
            Log.error("not allowed")

        self.facts[root_name].query(command)

