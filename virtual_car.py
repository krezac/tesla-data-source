import psycopg2
from psycopg2 import Error
from datetime import datetime, timezone
from time import sleep
import decimal

def _cursor_one_to_dict(cursor):
    column_names = [i[0] for i in cursor.description]
    row = cursor.fetchone()
    return dict(zip(column_names, row)) if row else None

CAR_ID = 1
POSITION_STEP = decimal.Decimal(0.0001)
date: datetime=datetime.now(tz=timezone.utc)

try:
    # Connect to an existing database
    ps_connection = psycopg2.connect(user="teslamate",
                                     password="secret",
                                     host="127.0.0.1",
                                     port="5432",
                                     database="teslamate")

    # Create a cursor to perform database operations
    cursor = ps_connection.cursor()

    pos_cursor_1 = ps_connection.cursor()
    pos_cursor_1.execute(
        "select car.name as car_name, pos.* from positions pos JOIN cars car on pos.car_id = car.id WHERE car_id = %s::integer AND usable_battery_level IS NOT NULL AND date < %s::timestamptz order by date desc limit 1",
        (CAR_ID, date))
    print(pos_cursor_1.query)
    start_data = _cursor_one_to_dict(pos_cursor_1)
    pos_cursor_1.close()

    # get the one most recent one containing elevation (take other fields as well)
    pos_cursor_2 = ps_connection.cursor()
    pos_cursor_2.execute(
        "select latitude, longitude, speed, power, odometer, elevation from positions WHERE car_id = %s::integer AND elevation IS NOT NULL AND date < %s::timestamptz order by date desc limit 1",
        (CAR_ID, date))
    print(pos_cursor_2.query)
    out_data_2 = _cursor_one_to_dict(pos_cursor_2)
    start_data.update(out_data_2)  # just add the extra fields
    pos_cursor_2.close()

    print(f"Result data: {start_data}")

    counter = 0
    while True:
        cursor = ps_connection.cursor()

        if counter % 30 == 0:
            print(f"full data {counter}")
            cursor.execute(f"""
            INSERT INTO positions (
                date,
                latitude,
                longitude,
                speed,
                power,
                odometer,
                ideal_battery_range_km,
                battery_level,
                outside_temp,
                fan_status,
                driver_temp_setting,
                passenger_temp_setting,
                is_climate_on,
                is_rear_defroster_on,
                is_front_defroster_on,
                car_id,
                drive_id,
                inside_temp,
                battery_heater,
                battery_heater_on,
                battery_heater_no_power,
                est_battery_range_km,
                rated_battery_range_km,
                usable_battery_level
                )
                values
                (
                %s::timestamptz,
                %s::decimal,
                %s::decimal,
                %s::integer,
                %s::integer,
                %s::decimal,
                %s::decimal,
                %s::integer,
                %s::decimal,
                %s::integer,
                %s::decimal,
                %s::decimal,
                %s::bool,
                %s::bool,
                %s::bool,
                %s::integer,
                %s::integer,
                %s::decimal,
                %s::bool,
                %s::bool,
                %s::bool,
                %s::decimal,
                %s::decimal,
                %s::integer
                )
            """,(
               datetime.now(timezone.utc),
               start_data["latitude"],
               start_data["longitude"],
               start_data["speed"],
               start_data["power"],
               start_data["odometer"],
               start_data["ideal_battery_range_km"],
               start_data["battery_level"],
               start_data["outside_temp"],
               start_data["fan_status"],
               start_data["driver_temp_setting"],
               start_data["passenger_temp_setting"],
               start_data["is_climate_on"],
               start_data["is_rear_defroster_on"],
               start_data["is_front_defroster_on"],
               start_data["car_id"],
               start_data["drive_id"],
               start_data["inside_temp"],
               start_data["battery_heater"],
               start_data["battery_heater_on"],
               start_data["battery_heater_no_power"],
               start_data["est_battery_range_km"],
               start_data["rated_battery_range_km"],
               start_data["usable_battery_level"]
               ))
        else:
            print(f"short data {counter}")
            cursor.execute("""  
                INSERT INTO positions (
                    date,
                    latitude,
                    longitude,
                    speed,
                    power,
                    odometer,
                    battery_level,
                    elevation,
                    car_id,
                    drive_id
                    )
                    values
                    (
                    %s::timestamptz,
                    %s::decimal,
                    %s::decimal,
                    %s::integer,
                    %s::integer,
                    %s::decimal,
                    %s::integer,
                    %s::integer,
                    %s::integer,
                    %s::integer
                    )""", (
                    datetime.now(timezone.utc),
                    start_data["latitude"],
                    start_data["longitude"],
                    start_data["speed"],
                    start_data["power"],
                    start_data["odometer"],
                    start_data["battery_level"],
                    start_data["elevation"],
                    start_data["car_id"],
                    start_data["drive_id"]
                    ))

        # print(cursor.query)
        ps_connection.commit()
        cursor.close()

        # update data
        start_data["latitude"] += POSITION_STEP
        start_data["longitude"] += POSITION_STEP
        counter += 1
        sleep(1)

except (Exception, Error) as error:
    print("Error while connecting to PostgreSQL", error)
finally:
    if (ps_connection):
        ps_connection.close()
        print("PostgreSQL connection is closed")





