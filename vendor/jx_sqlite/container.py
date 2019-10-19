from mo_kwargs import override

from jx_sqlite.namespace import Namespace
from jx_sqlite.query_table import QueryTable
from pyLibrary.sql import sql_iso, SQL_INSERT, sql_list
from pyLibrary.sql.sqlite import Sqlite, quote_column, quote_value

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

        self.ns = Namespace(db=db)
        self.about = QueryTable("meta.about", self)
        self.next_uid = self._gen_ids()  # A DELIGHTFUL SOURCE OF UNIQUE INTEGERS
        self.setup()

    def _gen_ids(self):
        while True:
            with self.about.transaction() as t:
                top_id = t.query({"select": "next_id"}).first().next_id
                max_id = top_id + 1000
                t.update({"set": {"next_id": max_id}})
            while top_id < max_id:
                yield top_id
                top_id += 1

    def setup(self):
        if not self.db.about(ABOUT_TABLE):
            about = QueryTable("meta.about", self)
            about.insert({"version": 1, "next_id": 1})

            with self.db.transaction() as t:
                t.execute(
                    "CREATE TABLE" + quote_column(DIGITS_TABLE) + "(value INTEGER)"
                )
                t.execute(
                    SQL_INSERT
                    + quote_column(DIGITS_TABLE)
                    + sql_list(sql_iso(quote_value(i)) for i in range(10))
                )
