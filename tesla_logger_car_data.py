import mariadb

_car_data = {}

def update_car_data():
    return
    global _car_data
    config = {
        'host': '127.0.0.1',
        'port': 3306,
        'user': 'root',
        'password': 'teslalogger',
        'database': 'teslalogger'
    }
    # connection for MariaDB
    conn = mariadb.connect(**config)
    # create a connection cursor
    cur = conn.cursor()
    # execute a SQL statement
    cur.execute("select odometer from pos")

    # serialize results into JSON
    row_headers = [x[0] for x in cur.description]
    rv = cur.fetchall()
    json_data = []
    for result in rv:
        json_data.append(dict(zip(row_headers, result)))

    # return the results!
    _car_data = {
        'data': json_data
    }


def get_car_data():
    global _car_data
    return _car_data


def register_job(scheduler):
    scheduler.add_job(update_car_data, 'interval', seconds=10)
