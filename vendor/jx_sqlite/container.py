import mo_json
from jx_base import Column, Facts
from jx_sqlite import UID, typed_column, quoted_UID, quoted_GUID, GUID
from jx_sqlite.expressions import json_type_to_sql_type
from jx_sqlite.namespace import Namespace
from jx_sqlite.query_table import QueryTable
from jx_sqlite.snowflake import Snowflake
from mo_dots import listwrap, split_field
from mo_future import first
from mo_kwargs import override
from mo_logs import Log
from mo_times import Date
from pyLibrary.sql import (
    sql_iso,
    SQL_INSERT,
    sql_list,
    SQL,
    SQL_VALUES,
    SQL_SELECT,
    SQL_FROM,
    SQL_UPDATE,
    SQL_SET,
)
from pyLibrary.sql.sqlite import (
    Sqlite,
    quote_column,
    quote_value,
    sql_eq,
    json_type_to_sqlite_type,
    sql_create,
    sql_insert,
)

DIGITS_TABLE = "__digits__"
ABOUT_TABLE = "meta.about"

_config = None


class Container(object):
    @override
    def __init__(self, db=None):
        global _config
        if isinstance(db, Sqlite):
            self.db = db
        else:
            self.db = db = Sqlite(db)

        if not _config:
            # REGISTER sqlite AS THE DEFAULT CONTAINER TYPE
            from jx_base.container import config as _config

            if not _config.default:
                _config.default = {"type": "sqlite", "settings": {"db": db}}

        self.setup()
        self.ns = Namespace(db=db)
        self.about = QueryTable("meta.about", self)
        self.next_uid = (
            self._gen_ids().__next__
        )  # A DELIGHTFUL SOURCE OF UNIQUE INTEGERS

    def _gen_ids(self):
        while True:
            with self.db.transaction() as t:
                top_id = first(
                    first(
                        t.query(
                            SQL_SELECT
                            + quote_column("next_id")
                            + SQL_FROM
                            + quote_column(ABOUT_TABLE)
                        ).data
                    )
                )
                max_id = top_id + 1000
                t.execute(
                    SQL_UPDATE
                    + quote_column(ABOUT_TABLE)
                    + SQL_SET
                    + sql_eq(next_id=max_id)
                )
            while top_id < max_id:
                yield top_id
                top_id += 1

    def setup(self):
        if not self.db.about(ABOUT_TABLE):
            with self.db.transaction() as t:
                t.execute(
                    sql_create(ABOUT_TABLE, {"version": "TEXT", "next_id": "INTEGER"})
                )
                t.execute(sql_insert(ABOUT_TABLE, {"version": "1.0", "next_id": 1000}))
                t.execute(sql_create(DIGITS_TABLE, {"value": "INTEGER"}))
                t.execute(sql_insert(DIGITS_TABLE, [{"value": i} for i in range(10)]))

    def create_or_replace_table(self, fact_name, uid=UID):
        """
        MAKE NEW TABLE, REPLACE OLD ONE IF EXISTS
        :param fact_name:  NAME FOR THE CENTRAL FACTS
        :param uid: name, or list of names, for the GUID
        :return: Facts
        """
        self.ns.remove_snowflake(fact_name)
        self.ns.columns._snowflakes[fact_name] = ["."]

        if uid != UID:
            Log.error("do not know how to handle yet")

        command = sql_create(fact_name, {UID: "INTEGER PRIMARY KEY", GUID: "TEXT"}, unique=UID)

        with self.db.transaction() as t:
            t.execute(command)

        snowflake = Snowflake(fact_name, self.ns)
        return Facts(self, snowflake)

    def get_table(self, table_name):
        return QueryTable(table_name, self)
