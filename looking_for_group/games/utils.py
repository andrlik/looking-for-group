import datetime

from django.db import DEFAULT_DB_ALIAS, connections


def check_table_exists(table_name):
    connection = connections[DEFAULT_DB_ALIAS]
    with connection.cursor() as cursor:
        table_list = connection.introspection.get_table_list(cursor)
    return table_name in [i[0] for i in table_list]


def mkDateTime(datestring, date_format="%Y-%m-%d %z"):
    return datetime.datetime.strptime(datestring, date_format)


def mkfirstOfmonth(dtDateTime):
    return mkDateTime(dtDateTime.strftime("%Y-%m-01 %z"))


def mkLastOfMonth(dtDateTime):
    start_of_month = mkfirstOfmonth(dtDateTime)
    dYear = start_of_month.strftime("%Y")
    dMonth = str(int(dtDateTime.strftime("%m")) % 12 + 1)
    dt_timezone = dtDateTime.strftime("%z")
    next_month = mkDateTime("{}-{}-01 {}".format(dYear, dMonth, dt_timezone))
    return next_month - datetime.timedelta(seconds=1)
