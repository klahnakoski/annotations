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

from mo_future import is_text, binary_type
from mo_future import text_type
from mo_logs import Log

DEBUG = True


class _Base(text_type):
    __slots__ = []

    @property
    def sql(self):
        return "".join(self)

    def __add__(self, other):
        if not isinstance(other, SQL):
            if DEBUG and is_text(other) and all(c not in other for c in ('"', "'", "`")):
                return _Concat((self, SQL(other)))
            Log.error("Can only concat other SQL")
        else:
            return _Concat((self, other))

    def __radd__(self, other):
        if not isinstance(other, SQL):
            if DEBUG and is_text(other) and all(c not in other for c in ('"', "'", "`")):
                return _Concat((SQL(other), self))
            Log.error("Can only concat other SQL")
        else:
            return _Concat((other, self))

    def join(self, list_):
        if not isinstance(list_, (list, tuple)):
            list_ = list(list_)
        return _Join(self, list_)

    def __data__(self):
        return self.sql


setattr(_Base, text_type.__name__, _Base.sql)
setattr(_Base, binary_type.__name__, lambda self: Log.error("do not do this"))


class SQL(_Base):
    """
    ACTUAL SQL, DO NOT QUOTE THIS STRING
    """
    __slots__ = ["value"]

    def __init__(self, value):
        text_type.__init__(self)
        if DEBUG and isinstance(value, SQL):
            Log.error("Expecting text, not SQL")
        self.value = value

    def __iter__(self):
        yield self.value


class _Join(_Base):
    __slots__ = ["sep", "concat"]

    def __init__(self, sep, concat):
        text_type.__init__(self)
        if DEBUG:
            if not isinstance(sep, SQL):
                Log.error("Expecting text, not SQL")
            if any(not isinstance(s, SQL) for s in concat):
                Log.error("Can only join other SQL")
        self.sep = sep
        self.concat = concat

    def __iter__(self):
        if not self.concat:
            return
        it = self.concat.__iter__()
        yield from it.__next__()
        for v in it:
            yield from self.sep
            yield from v


class _Concat(_Base):
    """
    ACTUAL SQL, DO NOT QUOTE THIS STRING
    """
    __slots__ = ["concat"]

    def __init__(self, concat):
        text_type.__init__(self)
        if DEBUG and any(not isinstance(s, SQL) for s in concat):
            Log.error("Can only join other SQL")
        self.concat = concat

    def __iter__(self):
        for c in self.concat:
            yield from c


SQL_STAR = SQL(" * ")

SQL_AND = SQL(" AND ")
SQL_OR = SQL(" OR ")
SQL_NOT = SQL(" NOT ")
SQL_ON = SQL(" ON ")

SQL_CASE = SQL(" CASE ")
SQL_WHEN = SQL(" WHEN ")
SQL_THEN = SQL(" THEN ")
SQL_ELSE = SQL(" ELSE ")
SQL_END = SQL(" END ")

SQL_COMMA = SQL(", ")
SQL_UNION_ALL = SQL("\nUNION ALL\n")
SQL_UNION = SQL("\nUNION\n")
SQL_LEFT_JOIN = SQL("\nLEFT JOIN\n")
SQL_INNER_JOIN = SQL("\nJOIN\n")
SQL_EMPTY_STRING = SQL("''")
SQL_TRUE = SQL(" 1 ")
SQL_FALSE = SQL(" 0 ")
SQL_ONE = SQL(" 1 ")
SQL_ZERO = SQL(" 0 ")
SQL_NEG_ONE = SQL(" -1 ")
SQL_NULL = SQL(" NULL ")
SQL_IS_NULL = SQL(" IS NULL ")
SQL_IS_NOT_NULL = SQL(" IS NOT NULL ")
SQL_SELECT = SQL("\nSELECT\n")
SQL_INSERT = SQL("\nINSERT INTO\n")
SQL_FROM = SQL("\nFROM\n")
SQL_WHERE = SQL("\nWHERE\n")
SQL_GROUPBY = SQL("\nGROUP BY\n")
SQL_ORDERBY = SQL("\nORDER BY\n")
SQL_VALUES = SQL("\nVALUES\n")
SQL_DESC = SQL(" DESC ")
SQL_ASC = SQL(" ASC ")
SQL_LIMIT = SQL("\nLIMIT\n")

SQL_CONCAT = SQL(" || ")
SQL_AS = SQL(" AS ")
SQL_SPACE = SQL(" ")
SQL_OP = SQL("(")
SQL_CP = SQL(")")


class DB(object):
    def quote_column(self, column_name, table=None):
        raise NotImplementedError()

    def db_type_to_json_type(self, type):
        raise NotImplementedError()


def sql_list(list_):
    list_ = list(list_)
    if not all(isinstance(s, SQL) for s in list_):
        Log.error("Can only join other SQL")
    return _Concat((SQL_SPACE, _Join(", ", list_), SQL_SPACE))


def sql_iso(sql):
    return _Concat((SQL_OP, sql, SQL_CP))


def sql_count(sql):
    return "COUNT(" + sql + ")"


def sql_concat(list_):
    return _Join(SQL_CONCAT, [sql_iso(l) for l in list_])


def sql_alias(value, alias):
    return _Concat((value.value, SQL_AS, alias.value))


def sql_coalesce(list_):
    return _Concat((SQL("COALESCE("), _Join(SQL_COMMA, list_), SQL_CP))
