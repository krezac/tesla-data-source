import os
import psycopg2
from psycopg2 import pool
from collections import namedtuple
import datetime

from ds_types import CarStatus

_car_data = {}


# NOTE using pandas:
# cur.execute(q)
# import pandas as pd
# pd.DataFrame.from_records(cur, columns=[i[0] for i in cur.description])

# pd.read_sql( Q , connection)

class TeslamateDataSource:
    postgreSQL_pool = None

    def __init__(self):
        if not TeslamateDataSource.postgreSQL_pool:
            TeslamateDataSource.postgreSQL_pool = \
                psycopg2.pool.SimpleConnectionPool(1, 10,
                                                   user = os.environ.get("TM_DB_USER", "teslamate"),
                                                   password = os.environ.get("TM_DB_PASS", "secret"),
                                                   host = os.environ.get("TM_DB_HOST", "127.0.0.1"),
                                                   port = os.environ.get("TM_DB_PORT", "5432"),
                                                   database = os.environ.get("TM_DB_NAME", "teslamate"))

    def _cursor_to_list(self, cursor):
        out_data = []
        rdef = namedtuple('dataset', ' '.join([x[0] for x in cursor.description]))
        for row in map(rdef._make, cursor.fetchall()):
            out_data.append(row)
            row = cursor.fetchone()
        return out_data

    def _cursor_one_to_dict(self, cursor):
        out_data = {}
        column_names = [i[0] for i in cursor.description]
        row = cursor.fetchone()
        return dict(zip(column_names, row))

    def get_car_status(self) -> CarStatus:
        status = None
        try:
            ps_connection = TeslamateDataSource.postgreSQL_pool.getconn()
            if ps_connection:
                pos_cursor = ps_connection.cursor()
                pos_cursor.execute("select * from positions order by date desc limit 1")
                out_data = self._cursor_one_to_dict(pos_cursor)
                pos_cursor.close()
                TeslamateDataSource.postgreSQL_pool.putconn(ps_connection)

                status = CarStatus(**out_data)
            else:
                raise Exception("no connection from pool")

        except (Exception, psycopg2.DatabaseError) as error:
            print("Error while connecting to PostgreSQL", error)
        return status


    def get_car_positions(self, config):
        out_data = []
        try:
            ps_connection = TeslamateDataSource.postgreSQL_pool.getconn()
            if ps_connection:
                pos_cursor = ps_connection.cursor()
                if config["from_time"] is not None:
                    pos_cursor.execute("SELECT * FROM positions where date >= %s::timestamptz ORDER BY date",
                                (datetime.datetime.fromtimestamp(config['from_time'].in_tz('utc').timestamp()),))
                else:
                    pos_cursor.execute(
                        "SELECT * FROM positions where date between (now() - '%s hour'::interval) and (now() - '%s hour'::interval) ORDER BY date",
                        (config['hours'], 0))
                print("The number of parts: ", pos_cursor.rowcount)

                rdef = namedtuple('dataset', ' '.join([x[0] for x in pos_cursor.description]))
                for row in map(rdef._make, pos_cursor.fetchall()):
                    out_data.append(row)
                    row = pos_cursor.fetchone()
                pos_cursor.close()

                TeslamateDataSource.postgreSQL_pool.putconn(ps_connection)

            else:
                raise Exception("no connection from pool")

        except (Exception, psycopg2.DatabaseError) as error:
            print("Error while connecting to PostgreSQL", error)
        return out_data


#def register_job(scheduler):
#    scheduler.add_job(update_car_data, 'interval', seconds=10)
