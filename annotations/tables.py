from mo_kwargs import override

from mo_threads.threads import register_thread

from pyLibrary.env.flask_wrappers import cors_wrapper



@register_thread
@cors_wrapper
@override
def create(**command):
    """
    :param command:
    :return:

    {
        "insert": "meta.tables",
        "values" : {
            "name": table_name,
            "owner": owner,
            "expire":{"add":["last_used", {"date":"year"}]}
        }
    }
    """

    # REGISTER OWNER
    # grants to others
    # VERIFY TABLE DOES NOT EXIST

    # VERIFY USER IS ALLOWED TO MAKE A TABLE
    # KEEP TRACK OF EXPIRE
    # SET LAST USED DATE
    # TABLES ARE JUST COLUMNS IN A DATABASE OBJECT


def insert(command):
    """

    :param command:
    :return:



    {
        "table":table_name,
        "values": []
    }
    """

    # VERIFY WRITE ACCESS TO TABLE
    #




def update(**command):
    """

    :param command:
    :return:

    REMOVE METADATA OF TABLE

    {
        "update": "meta.tables",
        "clear": ".",
        "where": {"eq":{"name":table_name}}
    }

    SAME AS REMOVING PROPERTY FROM DATABASE

    {
        "update": ".",
        "clear": table_name
    }

    """


def query(query):
    """

    :param query:
    :return:

    """


    # VERIFY READ ACCESS TO TABLE

    # VERIFY READ ACCESS TO COLUMNS







    # HOW TO DELETE A COLUMN?