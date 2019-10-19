from mo_future import first

from jx_sqlite.expressions import AndOp, EqOp, Variable, Literal
from mo_logs import Log
from pyLibrary.sql import sql_list, SQL_SELECT, SQL_FROM, SQL_WHERE, sql_iso, SQL_STAR, SQL_AND
from pyLibrary.sql.sqlite import quote_column, quote_value

ROOT = 1
VERSION_TABLE = "security.version"
GROUP_TABLE = "security.groups"
USER_TABLE = "security.users"
PERMISSION_TABLE = "security.permissions"
RESOURCE_TABLE = "security.resources"
TABLE_OPERATIONS = ["insert", "update", "from"]


class Permissions:
    def __init__(self, db):
        self.db = db
        if not self.db.about(VERSION_TABLE):
            self.setup()

    def setup(self):
        db = self.db

        version = (
            db.query("SELECT version FROM " + quote_column(VERSION_TABLE))
            .first()
            .version
        )
        if version:
            Log.error("already exists")

        db.raw_insert(VERSION_TABLE, {"version": 1})

        db.raw_insert(
            USER_TABLE,
            [{"_id": 1, "name": "root", "description": "access for security system"}],
        )

        db.raw_insert(
            GROUP_TABLE,
            [
                {
                    "_id": 11,
                    "name": "public",
                    "description": "everyone with confirmed email",
                    "owner": 1,
                },
                {
                    "_id": 12,
                    "name": "mozillians",
                    "description": "people that mozilla authentication has recongized as mozillian",
                    "owner": 1,
                },
                {
                    "_id": 13,
                    "name": "moz-employee",
                    "description": "people that mozilla authentication has recongized as employee",
                    "owner": 1,
                },
            ],
        )

        db.raw_insert(
            PERMISSION_TABLE,
            [
                {"user": 11, "resource": 11, "owner": 1},
                {"user": 10, "resource": 11, "owner": 1},
                {"user": 12, "resource": 11, "owner": 1},
                {"user": 12, "resource": 12, "owner": 1},
                {"user": 13, "resource": 12, "owner": 1},
                {"user": 13, "resource": 13, "owner": 1},
            ],
        )

        db.raw_insert(
            RESOURCE_TABLE,
            [{"_id": 102, "table": ".", "operation": "insert", "owner": 1}],
        )

        with db.transaction() as t:
            t.execute(
                "CREATE UNIQUE INDEX "
                + quote_column("security.resources.to_index")
                + " ON "
                + quote_column(RESOURCE_TABLE)
                + sql_iso(sql_list(["table", "operation"]))
            )

    def create_table_resource(self, table_name, owner):
        """
        :param table_name:  Create resources for given table
        :param owner: assign this user as owner
        :return:
        """
        new_resources = [
            {"table": table_name, "operation": op, "owner": 1}
            for op in TABLE_OPERATIONS
        ]

        self.db.raw_insert(RESOURCE_TABLE, new_resources)

        self.db.raw_insert(
            PERMISSION_TABLE,
            [{"user": owner, "resource": r._id, "owner": 1} for r in new_resources],
        )

    def get_or_create_user(self, id_token):
        Log.warning("did not confirm email")

        email = id_token.claims.email
        if not email:
            Log.error("Expecting id_token to have claims.email propert")

        existing = first(
            self.db.query(
                SQL_SELECT
                + "_id, email"
                + SQL_FROM
                + quote_column(USER_TABLE)
                + SQL_WHERE
                + "email = "
                + quote_value(email)
            )
        )

        if existing:
            return existing

        new_user = {"email": email}
        self.db.raw_insert(USER_TABLE, new_user)
        return new_user

    def get_resource(self, table, operation):
        existing = first(
            self.db.query(
                SQL_SELECT
                + "_id"
                + SQL_FROM
                + quote_column(USER_TABLE)
                + SQL_WHERE
                + SQL_AND.join(
                    [
                        "table = " + quote_value(table),
                        "operation = " + quote_value(operation),
                    ]
                )
            )
        )

        if not existing:
            Log.error("Expecting to find a resource")

        return existing

    def add_permission(self, user, resource, owner):
        """
        :param user:
        :param resource:
        :param owner:
        :return:
        """

        # DOES owner HAVE ACCESS TO resource?
        if not self.allow_resource(owner, resource):
            Log.error("not allowed to assign resource")

        # DOES THIS PERMISSION EXIST ALREADY
        allowance = self.allow_resource(user, resource)
        if allowance:
            if any(r.owner == owner for r in allowance):
                Log.error("already allowed via {{allowance}}", allowance=allowance)
            # ALREADY ALLOWED, BUT MULTIPLE PATHS MAY BE OK
        self.db.raw_insert(
            PERMISSION_TABLE, {"user": user, "resource": resource, "owner": owner}
        )

    def allow_resource(self, user, resource):

        resources = self.db.execute(
            SQL_SELECT
            + sql_list(["resource", "owner"])
            + SQL_FROM
            + quote_column(PERMISSION_TABLE)
            + SQL_WHERE
            + "user = "
            + quote_value(user)
        )

        for r in resources:
            if r.resource == resource:
                if r.owner == ROOT:
                    return [{"resource": resource, "user": user, "owner": r.owner}]
                else:
                    cascade = self.allow_resource(r.owner, resource)
                    if cascade:
                        cascade.append(
                            {"resource": resource, "user": user, "owner": r.owner}
                        )
                    return cascade
            else:
                group = r.resource
                cascade = self.allow_resource(group, resource)
                if cascade:
                    cascade.append({"group": group, "user": user, "owner": r.owner})
                return cascade

        return []

    # permissions on a property
    # permissions on rows in nested table
    # {where: {in: {"_id": [42, 24]}}}
    # nested documents have _id too (maybe coordinates into the database)
    # all rows in table, vs just some subset, vs some rule
    # a table is a row, and a column
    # columns access is a rule
    """
    {
        "user":"public", 
        "resource":{
            "allow":"read", 
            "where":{"exists":"unittest"}
        }
    }
    """

    def find_resource(self, table, operation):
        return self.db.query(
            SQL_SELECT
            + SQL_STAR
            + SQL_FROM
            + quote_column(RESOURCE_TABLE)
            + SQL_WHERE
            + AndOp(
                [
                    EqOp([Variable("operation"), Literal(operation)]),
                    EqOp([Variable("table"), +Literal(table)]),
                ]
            ).to_sql()
        ).first()
