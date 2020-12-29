from typing import Callable

from teslamate_data_source import TeslamateDataSource
from ds_types import Configuration

_get_configuration_func = None
_data_source = TeslamateDataSource()
_car_status = None


def _update_car_status():
    global _car_status
    global _data_source
    global _get_configuration_func

    print("updating car status")
    _car_status = _data_source.get_car_status(_get_configuration_func())
    print("updating car status done")


def _update_car_laps():
    # TODO cache these as well. We need to handle config
    pass


def get_car_status():
    global _car_status
    return _car_status


def get_car_positions(configuration: Configuration):
    # TODO this should go thru cache
    return _data_source.get_car_positions(configuration)


def register_jobs(scheduler, get_configuration_func: Callable[[], Configuration]):
    global _get_configuration_func
    _get_configuration_func = get_configuration_func
    scheduler.add_job(_update_car_status, 'interval', seconds=get_configuration_func().statusRefreshSeconds)
    scheduler.add_job(_update_car_laps, 'interval', seconds=get_configuration_func().lapsRefreshSeconds)
