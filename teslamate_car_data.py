
from teslamate_data_source import TeslamateDataSource

_data_source = TeslamateDataSource()
_car_status = None


def _update_car_status():
    global _car_status
    global _data_source

    print("updating car status")
    _car_status = _data_source.get_car_status()
    print("updating car status done")


def _update_car_laps():
    # TODO cache these as well. We need to handle config
    pass

def get_car_status():
    global _car_status
    return _car_status

def get_car_positions(config):
    # TODO this should go thru cache
    return _data_source.get_car_positions(config)


def register_jobs(scheduler):
    scheduler.add_job(_update_car_status, 'interval', seconds=2)
    scheduler.add_job(_update_car_laps, 'interval', seconds=10)
