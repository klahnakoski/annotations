from jx_sqlite.expressions import AndOp, EqOp, Variable, Literal
from mo_future import first
from mo_dots import split_field
from pyLibrary.sql import sql_list, SQL_SELECT, SQL_FROM, SQL_WHERE, sql_iso, SQL_STAR
from pyLibrary.sql.sqlite import quote_column, quote_value
from mo_logs import Log


ROOT = 1


class Permissions:
    def __init__(self, db):
        self.db = db

    def setup(self):
        db = self.db

        version = (
            db.query("SELECT version FROM " + quote_column("security.version"))
            .first()
            .version
        )
        if version:
            Log.error("already exists")

        db.insert("security.version", {"version": 1})

        db.insert(
            "security.users",
            [{"_id": 1, "name": "root", "description": "access for security system"}],
        )

        db.insert(
            "security.groups",
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

        db.insert(
            "security.permissions",
            [
                {"user": 11, "resource": 11, "owner": 1},
                {"user": 10, "resource": 11, "owner": 1},
                {"user": 12, "resource": 11, "owner": 1},
                {"user": 12, "resource": 12, "owner": 1},
                {"user": 13, "resource": 12, "owner": 1},
                {"user": 13, "resource": 13, "owner": 1},
            ],
        )

        db.insert(
            "security.resources",
            [
                {"_id": 102, "table": ".", "operation":"insert", "owner": 1},
                {"_id": 103, "table": ".", "operation":"update", "owner": 1},
                {"_id": 104, "table": ".", "operation":"from", "owner": 1},
            ],
        )

        with db.transaction() as t:
            t.execute("CREATE UNIQUE INDEX "+quote_column("security.resources.to_index")+
                      " ON " + quote_column("security.resources")+
                      sql_iso(sql_list(["table", "operation"])))


    def add_resource(self, resource):
        


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
        self.db.insert("security.permissions", {
            "user": user,
            "resource": resource,
            "owner": owner
        })

    def allow_resource(self, user, resource):

        resources = self.db.execute(
            SQL_SELECT +
            sql_list(["resource", "owner"]) +
            SQL_FROM + quote_column("security.permissions") +
            SQL_WHERE + "user = " + quote_value(user)
        )

        for r in resources:
            if r.resource == resource:
                if r.owner == ROOT:
                    return [{"resource": resource, "user": user, "owner": r.owner}]
                else:
                    cascade = self.allow_resource(r.owner, resource)
                    if cascade:
                        cascade.append({"resource": resource, "user": user, "owner": r.owner})
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
            SQL_SELECT + SQL_STAR +
            SQL_FROM + quote_column("security.resources") +
            SQL_WHERE + AndOp([
                EqOp([Variable("operation"), Literal(operation)]),
                EqOp([Variable("table"), + Literal(table)])
            ]).to_sql()
        ).first()

    # every record has an owner
    # security system points to objects to determine owner

    def allow_create(self, command, user):
        """
        Verify user can submit create statement
        :param command:  {"create": table_name}
        :param user:
        :return: authorization chain
        """
        resource = self.find_resource(None, "create")
        return self.allow_resource(user, resource.id)


    def allow_insert(self, command, user):
        """
        verify user can submit insert
        :param command:
        :param user:
        :return: authorization chain
        """
        table_name = command.insert
        resource = self.find_resource(table_name, "insert")
        return self.allow_resource(user, resource.id)


    def allow_update(self, command, user):
        """
        verify user can submit insert
        :param command:
        :param user:
        :return: authorization chain
        """
        table_name = command.insert
        resource = self.find_resource(table_name, "update")
        return self.allow_resource(user, resource.id)



    def allow_query(self, query, user):
        """
        verify query can be performed by user
        :param query:
        :param user:
        :return: authorization chain
        """
        table_name = first(split_field(query['from']))
        resource = self.find_resource(table_name, "query")
        return self.allow_resource(user, resource.id)
