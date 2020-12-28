from flask import Flask, request, render_template

import pendulum

import fio_api
# import tesla_logger_car_data
import teslamate_car_data
import lap_analyzer

from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

#################### scheduler stuff #########################
scheduler = BackgroundScheduler()
teslamate_car_data.register_jobs(scheduler)
fio_api.register_job(scheduler)
scheduler.start()


def _read_config():
    config = {
        "lat": request.args.get('lat', default=None, type=float),
        "lon": request.args.get('lon', default=None, type=float),
        "radius": request.args.get('radius', default=100.0, type=float),
        "consumption_rated": request.args.get('consumption_rated', default=14.7, type=float),
        "hours": request.args.get('hours', default=24, type=int),
        "format": request.args.get('format', default=None, type=str),
        "from_time": request.args.get('from_time', default=None, type=str),
        "merge_from_lap": request.args.get('merge_from_lap', default=1, type=int),
        "lap_merge": request.args.get('lap_merge', default=1, type=int),
    }
    if config["from_time"]:
        config["from_time"] = pendulum.parse(config["from_time"])
    return config


###################### main
@app.route('/')
def hello_world():
    return 'Nothing here. You need to know the magic word.'


@app.route('/car_status')
def car_status():
    status = teslamate_car_data.get_car_status()
    return status.json() if status else {}


@app.route('/car_map')
def car_map():
    car_status = teslamate_car_data.get_car_status()
    return render_template('map.html', car_status=car_status, title="Car status and position")


@app.route('/laps_table')
def get_tm_car_data():
    config = _read_config()
    positions = teslamate_car_data.get_car_positions(config)
    items = lap_analyzer.find_laps(config, positions, config['radius'], 0, -1)
    return render_template('laps_table.html', items=items, title="Laps")


#@app.route('/tesla_logger_car_data')
#def get_tl_car_data():
#    return tesla_logger_car_data.get_car_data()

#@app.route('/teslamate_car_data')
#def get_tm_car_data():
#    config = _read_config()
#    positions = teslamate_car_data.get_car_positions(config)
#    laps = lap_analyzer.find_laps(config, positions, config['radius'], 0, -1)
#    return str(laps)


@app.route('/fio_balance')
def get_fio_balance():
    return fio_api.get_balance_info()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
