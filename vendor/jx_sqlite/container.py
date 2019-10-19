from jx_sqlite.namespace import Namespace
from jx_sqlite.query_table import QueryTable
from mo_future import first
from mo_kwargs import override
from pyLibrary.sql import sql_iso, SQL_INSERT, sql_list, SQL, SQL_ZERO, SQL_VALUES, SQL_SELECT, SQL_FROM, SQL_UPDATE, \
    SQL_SET
from pyLibrary.sql.sqlite import Sqlite, quote_column, quote_value, sql_eq

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
        self.next_uid = self._gen_ids().__next__  # A DELIGHTFUL SOURCE OF UNIQUE INTEGERS

    def _gen_ids(self):
        while True:
            with self.db.transaction() as t:
                top_id = first(first(t.query(
                    SQL_SELECT + quote_column("next_id") +SQL_FROM + quote_column(ABOUT_TABLE)
                ).data))
                max_id = top_id + 1000
                t.execute(
                    SQL_UPDATE + quote_column(ABOUT_TABLE) + SQL_SET + sql_eq(next_id=max_id)
                )
            while top_id < max_id:
                yield top_id
                top_id += 1

    def setup(self):
        if not self.db.about(ABOUT_TABLE):
            with self.db.transaction() as t:
                t.execute(
                    "CREATE TABLE"
                    + quote_column(ABOUT_TABLE)
                    + "(version TEXT, next_id INTEGER)"
                )
                t.execute(
                    SQL_INSERT
                    + quote_column(ABOUT_TABLE)
                    + SQL_VALUES
                    + sql_iso(sql_list([SQL("1.0"), quote_value(1000)]))
                )
                t.execute(
                    "CREATE TABLE" + quote_column(DIGITS_TABLE) + "(value INTEGER)"
                )
                t.execute(
                    SQL_INSERT
                    + quote_column(DIGITS_TABLE)
                    + SQL_VALUES
                    + sql_list(sql_iso(quote_value(i)) for i in range(10))
                )
