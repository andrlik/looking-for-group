from django.db import DEFAULT_DB_ALIAS, connections


def check_table_exists(table_name):
    connection = connections[DEFAULT_DB_ALIAS]
    with connection.cursor() as cursor:
        table_list = connection.introspection.get_table_list(cursor)
    return table_name in [i[0] for i in table_list]
