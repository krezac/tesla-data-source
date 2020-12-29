import os
import psycopg2
from psycopg2 import pool
from collections import namedtuple
import datetime

from ds_types import CarStatus, Configuration

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
                                                   user=os.environ.get("TM_DB_USER", "teslamate"),
                                                   password=os.environ.get("TM_DB_PASS", "secret"),
                                                   host=os.environ.get("TM_DB_HOST", "127.0.0.1"),
                                                   port=os.environ.get("TM_DB_PORT", "5432"),
                                                   database=os.environ.get("TM_DB_NAME", "teslamate"))

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

    def get_car_status(self, configuration: Configuration) -> CarStatus:
        """
        note there are two types of rows, one contains all but elevation, the other one altitude.
        That's why we need two reads
        """
        status = None
        try:
            ps_connection = TeslamateDataSource.postgreSQL_pool.getconn()
            if ps_connection:
                # get the one containing most of the values
                pos_cursor_1 = ps_connection.cursor()
                pos_cursor_1.execute("select car.name, pos.* from positions pos JOIN cars car on pos.car_id = car.id WHERE car_id = %s::integer AND usable_battery_level IS NOT NULL order by date desc limit 1",
                                   (configuration.carId,))
                out_data = self._cursor_one_to_dict(pos_cursor_1)
                pos_cursor_1.close()

                # get the one most recent one containing elevation (take other fields as well)
                pos_cursor_2 = ps_connection.cursor()
                pos_cursor_2.execute("select latitude, longitude, speed, power, odometer, elevation from positions WHERE car_id = %s::integer AND elevation IS NOT NULL order by date desc limit 1",
                                   (configuration.carId,))
                out_data_2 = self._cursor_one_to_dict(pos_cursor_2)
                out_data.update(out_data_2)  # just add the extra fields
                pos_cursor_2.close()

                TeslamateDataSource.postgreSQL_pool.putconn(ps_connection)
                status = CarStatus(**out_data)
            else:
                raise Exception("no connection from pool")

        except (Exception, psycopg2.DatabaseError) as error:
            print("Error while connecting to PostgreSQL", error)
        return status

    def get_car_positions(self, configuration: Configuration):
        out_data = []
        try:
            ps_connection = TeslamateDataSource.postgreSQL_pool.getconn()
            if ps_connection:
                pos_cursor = ps_connection.cursor()
                pos_cursor.execute("SELECT * FROM positions where date >= %s::timestamptz AND date <= (%s::timestamptz + '%s hour'::interval) AND car_id = %s::integer AND usable_battery_level IS NOT NULL ORDER BY date",
                            (datetime.datetime.fromtimestamp(configuration.startTime.timestamp()) if configuration.startTime else datetime.datetime.now(tz="utc").timestamp(),
                             datetime.datetime.fromtimestamp(configuration.startTime.timestamp()) if configuration.startTime else datetime.datetime.now(tz="utc").timestamp(),
                             configuration.hours,
                             configuration.carId))
                print(pos_cursor.query)
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
