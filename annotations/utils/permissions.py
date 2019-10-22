from mo_dots import wrap, Data

from mo_future import first

from mo_logs import Log
from pyLibrary.sql import sql_list, sql_iso
from pyLibrary.sql.sqlite import quote_column, sql_query

ROOT_USER = wrap({"_id": 1})
VERSION_TABLE = "security.version"
GROUP_TABLE = "security.groups"
USER_TABLE = "security.users"
PERMISSION_TABLE = "security.permissions"
RESOURCE_TABLE = "security.resources"
TABLE_OPERATIONS = ["insert", "update", "from"]


class Permissions:
    def __init__(self, container, db):
        self.container = container
        self.db = db
        if not self.db.about(PERMISSION_TABLE):
            self.setup()

    def setup(self):
        db = self.container

        db.safe_insert(VERSION_TABLE, {"version": "1.0"})

        db.safe_insert(
            USER_TABLE,
            [
                {
                    "_id": 1,
                    "name": "root",
                    "email": "nobody@mozilla.com",
                    "description": "access for security system",
                }
            ],
        )

        db.safe_insert(
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

        db.safe_insert(
            RESOURCE_TABLE,
            [
                {"_id": 100, "table": ".", "operation": "insert", "owner": 1},
                {"_id": 101, "table": ".", "operation": "update", "owner": 1},
                {"_id": 102, "table": ".", "operation": "from", "owner": 1},
            ],
        )

        db.safe_insert(
            PERMISSION_TABLE,
            [
                {"user": 12, "resource": 11, "owner": 1},
                {"user": 13, "resource": 11, "owner": 1},
                {"user": 13, "resource": 12, "owner": 1},
                {"user": 1, "resource": 100, "owner": 1},
                {"user": 1, "resource": 101, "owner": 1},
                {"user": 1, "resource": 102, "owner": 1},
            ],
        )

        with self.db.transaction() as t:
            t.execute(
                "CREATE UNIQUE INDEX "
                + quote_column("security.resources.to_index")
                + " ON "
                + quote_column(RESOURCE_TABLE)
                + sql_iso(sql_list([quote_column("table"), quote_column("operation")]))
            )

    def create_table_resource(self, table_name, owner):
        """
        CREATE A TABLE, CREATE RESOURCES FOR OPERATIONS, ENSURE CREATOR HAS CONTROL OVER TABLE

        :param table_name:  Create resources for given table
        :param owner: assign this user as owner
        :return:
        """
        new_resources = wrap(
            [
                {"table": table_name, "operation": op, "owner": 1}
                for op in TABLE_OPERATIONS
            ]
        )
        self.container.safe_insert(RESOURCE_TABLE, new_resources)
        self.container.safe_insert(
            PERMISSION_TABLE,
            [
                {"user": owner._id, "resource": r._id, "owner": ROOT_USER._id}
                for r in new_resources
            ],
        )

    def get_or_create_user(self, id_token):
        Log.warning("did not confirm email")

        email = wrap(id_token).claims.email
        if not email:
            Log.error("Expecting id_token to have claims.email propert")

        result = self.db.query(
            sql_query(
                {
                    "select": ["_id", "email"],
                    "from": USER_TABLE,
                    "where": {"eq": {"email": email}},
                }
            )
        )

        if result.data:
            return Data(zip(result.header, first(result.data)))

        new_user = wrap({"email": email})
        self.container.safe_insert(USER_TABLE, new_user)
        return new_user

    def get_resource(self, table, operation):
        result = self.db.query(
            sql_query(
                {
                    "select": "_id",
                    "from": RESOURCE_TABLE,
                    "where": {"eq": {"table": table, "operation": operation}},
                }
            )
        )
        if not result.data:
            Log.error("Expecting to find a resource")

        return Data(zip(result.header, first(result.data)))

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
        self.container.safe_insert(
            PERMISSION_TABLE,
            {"user": user._id, "resource": resource._id, "owner": owner._id},
        )

    def allow_resource(self, user, resource):
        """
        VERIFY IF user CAN ACCESS resource
        :param user:
        :param resource:
        :return: ALLOWANCE CHAIN
        """
        resources = self.db.query(
            sql_query(
                {
                    "select": ["resource", "owner"],
                    "from": PERMISSION_TABLE,
                    "where": {"eq": {"user": user._id}},
                }
            )
        )

        for r in resources.data:
            record = Data(zip(resources.header, r))
            if record.resource == resource._id:
                if record.owner == ROOT_USER._id:
                    return [{"resource": resource, "user": user, "owner": ROOT_USER}]
                else:
                    cascade = self.allow_resource(wrap({"_id": record.owner}), resource)
                    if cascade:
                        cascade.append(
                            {"resource": resource, "user": user, "owner": record.owner}
                        )
                    return cascade
            else:
                group = record.resource
                cascade = self.allow_resource(wrap({"_id": group}), resource)
                if cascade:
                    cascade.append(
                        {"group": group, "user": user, "owner": record.owner}
                    )
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
        result = self.db.query(
            sql_query(
                {
                    "from": RESOURCE_TABLE,
                    "where": {"eq": {"table": table, "operation": operation}},
                }
            )
        )

        return Data(zip(result.header, first(result.data)))
