from flask import Flask, request, render_template, Response, abort

import os
import sys
import logging

import fio_api
import teslamate_car_data
import lap_analyzer
from ds_types import Configuration, DriverChange, JsonStatusResponse, LapsList
from labels import generate_labels

from apscheduler.schedulers.background import BackgroundScheduler

NOT_ENABLED_JSON = str({"enabled": "false"})
app = Flask("app")

handler = logging.StreamHandler(sys.stdout)
app.logger.addHandler(handler)
app.logger.setLevel(logging.DEBUG)


def _read_config_file() -> Configuration:
    config_file_locations = [
        "/etc/tesla-data-source/config.json",
        "/etc/config.json",
        "config.json"
    ]
    for config_file_location in config_file_locations:
        app.logger.info(f"Trying to read config from {config_file_location}")
        try:
            c = Configuration.parse_file(config_file_location)
            if c:
                app.logger.info(f"Config found and parsed: {config_file_location}")
                return c
        except FileNotFoundError:
            pass
    raise FileNotFoundError(f" no config file in any of {config_file_locations}")


def _verify_post_token():
    expected_token = os.environ.get("POST_CONFIG_TOKEN", "secret_value")
    actual_token = request.args.get('_token', default="", type=str)
    if expected_token != actual_token:
        app.logger.error(f"token mismatch, got: {actual_token}")
        abort(403)


def get_configuration():
    """
    this is for background jobs to get the fresh configuration
    """
    global _configuration
    return _configuration


###################### main
@app.route('/')
def index_page():
    return 'Nothing here. You need to know the magic word.'


@app.route('/custom')
def custom_page():
    template = request.args.get('_template', default=None, type=str)
    if not template:
        abort(404)
    return render_template(template)


# ########### JSON endpoints (AJAX) ############
@app.route('/car_status_json_full')
def get_car_status_json_full():
    """
    This is for debugging purposes - shows all available data
    """
    if not _configuration.enabled:
        return NOT_ENABLED_JSON

    status = teslamate_car_data.get_car_status()
    return Response(status.json() if status else {}, mimetype='application.json')


@app.route('/car_status_json')
def get_car_status_json():
    """
    This is to be used from web pages
    :return:
    """
    if not _configuration.enabled:
        return NOT_ENABLED_JSON

    out = teslamate_car_data.get_car_status_formatted()
    return Response(out.json(), mimetype='application.json')


@app.route('/car_laps_json_full')
def get_car_laps_json_full():
    if not _configuration.enabled:
        return NOT_ENABLED_JSON

    out = LapsList(
        __root__=teslamate_car_data.get_car_laps_list()
    )
    return Response(out.json(), mimetype='application.json')


@app.route('/car_laps_json')
def get_car_laps_json():
    if not _configuration.enabled:
        return NOT_ENABLED_JSON

    laps = teslamate_car_data.get_car_laps_formatted()
    return Response(laps.json() if laps else {}, mimetype='application.json')


@app.route('/car_charging_json_full')
def get_car_charging_json_full():
    if not _configuration.enabled:
        return NOT_ENABLED_JSON

    laps = teslamate_car_data.get_car_laps_formatted()
    return Response(laps.json() if laps else {}, mimetype='application.json')


@app.route('/car_charging_json')
def get_car_charging_json():
    if not _configuration.enabled:
        return NOT_ENABLED_JSON

    laps = teslamate_car_data.get_car_laps_formatted()
    return Response(laps.json() if laps else {}, mimetype='application.json')


@app.route('/fio_balance_json')
def get_fio_balance_json():
    if not _configuration.enabled:
        return NOT_ENABLED_JSON

    balance = fio_api.get_balance_info()
    return Response(balance.json(), mimetype='application.json')


@app.route('/configuration', methods=['GET', 'POST', 'DELETE'])
def configuration():
    global _configuration
    if request.method == 'DELETE':
        app.logger.warning("trying to reset config")
        _verify_post_token()  # abort inside
        _configuration = _read_config_file()
    elif request.method == 'POST':
        app.logger.warning("trying to post config")
        _verify_post_token()  # abort inside
        try:
            j = request.get_json()
            orig = _configuration.dict()
            orig.update(j)
            _configuration = Configuration(**orig)
        except Exception as ex:
            app.logger.error(f"Unable to parse configuration", ex)
            abort(400, ex)

    return Response(_configuration.json(), mimetype='application.json')


@app.route('/driver_change', methods=['GET', 'POST'])
def driver_change():
    global _configuration
    if request.method == 'POST':
        _verify_post_token()  # abort inside
        try:
            j = request.get_json()
            driver_change = DriverChange(**j)
            teslamate_car_data.apply_driver_change(driver_change)

        except Exception as ex:
            app.logger.error(f"Unable to parse driver change", ex)
            abort(400, ex)

    return Response({}, mimetype='application.json')


# ########### web endpoints ############
@app.route('/car_map')
def car_map():
    if not _configuration.enabled:
        return render_template('not_enabled.html')

    return render_template('map.html', zoom=_configuration.defaultMapZoom)


@app.route('/dashboard')
def dashboard():
    if not _configuration.enabled:
        return render_template('not_enabled.html')

    return render_template('dashboard.html', zoom=_configuration.defaultMapZoom, title="Tesla Racing Dashboard",
                           config=_configuration)


@app.route('/fio_balance')
def get_fio_balance():
    if not _configuration.enabled:
        return render_template('not_enabled.html')

    balance = fio_api.get_balance_info()
    return render_template('fio_balance.html', balance=balance, title="Balance")


@app.route('/laps_table')
def get_tm_car_data():
    if not _configuration.enabled:
        return render_template('not_enabled.html')

    items = teslamate_car_data.get_car_laps()
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
app.logger.info("starting background jobs")
scheduler = BackgroundScheduler()
teslamate_car_data.register_jobs(scheduler, get_configuration)
fio_api.register_jobs(scheduler, get_configuration)
scheduler.start()


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')
