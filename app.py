from flask import Flask, request, render_template, Response, abort

import os
import pendulum

import fio_api
# import tesla_logger_car_data
import teslamate_car_data
import lap_analyzer
from ds_types import Configuration

from apscheduler.schedulers.background import BackgroundScheduler

NOT_ENABLED_JSON = str({"enabled": "false"})
app = Flask(__name__)


def _read_config_file() -> Configuration:
    config_file_locations = [
        "/etc/tesla-data-source/config.json",
        "/etc/config.json",
        "config.json"
    ]
    for config_file_location in config_file_locations:
        print(f"Trying to read config from {config_file_location}")
        try:
            c = Configuration.parse_file(config_file_location)
            if c:
                print(f"Config found and parsed: {config_file_location}")
                return c
        except FileNotFoundError:
            pass
    raise FileNotFoundError(f" no config file in any of {config_file_locations}")


def get_configuration():
    """
    this is for background jobs to get the fresh configuration
    """
    global _configuration
    return _configuration


def _read_config_from_request():
    config = {
        #"lat": request.args.get('lat', default=None, type=float),
        #"lon": request.args.get('lon', default=None, type=float),
        #"radius": request.args.get('radius', default=100.0, type=float),
        "consumption_rated": request.args.get('consumption_rated', default=14.7, type=float),
        #"hours": request.args.get('hours', default=24, type=int),
        "format": request.args.get('format', default=None, type=str),
        #"from_time": request.args.get('from_time', default=None, type=str),
        #"merge_from_lap": request.args.get('merge_from_lap', default=1, type=int),
        #"lap_merge": request.args.get('lap_merge', default=1, type=int),
    }
    if config["from_time"]:
        config["from_time"] = pendulum.parse(config["from_time"])
    return config


###################### main
@app.route('/')
def index_page():
    return 'Nothing here. You need to know the magic word.'


# ########### JSON endpoints (AJAX) ############
@app.route('/car_status_json')
def car_status():
    if not _configuration.enabled:
        return NOT_ENABLED_JSON

    status = teslamate_car_data.get_car_status()
    return Response(status.json() if status else {}, mimetype='application.json')


@app.route('/fio_balance_json')
def get_fio_balance():
    if not _configuration.enabled:
        return NOT_ENABLED_JSON

    balance = fio_api.get_balance_info()
    return Response(balance.json(), mimetype='application.json')


# TODO this should be protected somehow
@app.route('/configuration', methods=['GET', 'POST'])
def configuration():
    global _configuration
    if request.method == 'POST':
        expected_token = os.environ.get("POST_CONFIG_TOKEN", "secret_value")
        actual_token = request.args.get('_token', default="", type=str)
        if expected_token != actual_token:
            abort(403)
        try:
            j = request.get_json()
            _configuration = Configuration(**j)
        except Exception as ex:
            print(f"Unable to parse configuration", ex)
            abort(400, ex)

    return Response(_configuration.json(), mimetype='application.json')


# ########### web endpoints ############
@app.route('/car_map')
def car_map():
    if not _configuration.enabled:
        return render_template('not_enabled.html')

    car_status = teslamate_car_data.get_car_status()
    return render_template('map.html',
                           car_status=car_status, title="Car status and position", zoom=_configuration.defaultMapZoom)


@app.route('/laps_table')
def get_tm_car_data():
    if not _configuration.enabled:
        return render_template('not_enabled.html')

    # config = _read_config_from_request()
    positions = teslamate_car_data.get_car_positions(_configuration)
    items = lap_analyzer.find_laps(_configuration, positions, _configuration.startRadius, 0, -1)
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


_configuration = _read_config_file()

# ################### scheduler stuff #########################
print("starting background jobs")
scheduler = BackgroundScheduler()
teslamate_car_data.register_jobs(scheduler, get_configuration)
fio_api.register_jobs(scheduler, get_configuration)
scheduler.start()


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')
