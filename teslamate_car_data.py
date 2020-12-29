from typing import Callable, List

from teslamate_data_source import TeslamateDataSource
from ds_types import Configuration, LapsResponse, LapStatus, CarStatus
import lap_analyzer

_get_configuration_func = None
_data_source = TeslamateDataSource()
_car_status = None
_car_laps_structured: LapsResponse = None
_car_laps_list: List[LapStatus] = None

def _update_car_status():
    global _car_status
    global _data_source
    global _get_configuration_func

    print("updating car status")
    _car_status = _data_source.get_car_status(_get_configuration_func())
    print("updating car status done")


def _update_car_laps():
    global _car_laps_list
    global _car_laps_structured
    global _get_configuration_func

    print("updating car laps")
    configuration = _get_configuration_func()
    positions = _data_source.get_car_positions(configuration)
    _car_laps_list = lap_analyzer.find_laps(configuration, positions, configuration.startRadius, 0, -1)
    prev_list = _car_laps_list[-configuration.previousLaps - 1:-1] if len(_car_laps_list) > 0 else []
    prev_list.reverse()  # to have newest on top
    _car_laps_structured = LapsResponse(
        total=_calculate_lap_total(_car_laps_list) if _car_laps_list else None,
        previous=prev_list,
        recent=_car_laps_list[-1] if len(_car_laps_list) > 0 else None
    )
    print("updating car laps done")


def _calculate_lap_total(laps: List[LapStatus]) -> LapStatus:
    start_lap = laps[0]
    end_lap = laps[-1]

    total_status = LapStatus(
        id=f"{start_lap.id} - {end_lap.id}",
        startTime=start_lap.startTime,
        endTime=end_lap.endTime,
        startOdo=start_lap.startOdo,
        endOdo=end_lap.endOdo,
        insideTemp=end_lap.insideTemp,
        outsideTemp=end_lap.outsideTemp,
        startSOC=start_lap.startSOC,
        endSOC=end_lap.endSOC,
        startRangeIdeal=start_lap.startRangeIdeal,
        endRangeIdeal=end_lap.endRangeIdeal,
        startRangeEst=start_lap.startRangeEst,
        endRangeEst=end_lap.endRangeEst,
        startRangeRated=start_lap.startRangeRated,
        endRangeRated=end_lap.endRangeRated,
        consumptionRated=start_lap.consumptionRated,
        finished=False
    )

    # TODO calculate energy as sum
    energy = 0
    for lap in laps:
        energy += lap.energy
    total_status.energy = energy

    return total_status

def get_car_status() -> CarStatus:
    global _car_status
    return _car_status


def get_car_laps() -> LapsResponse:
    global _car_laps_structured
    return _car_laps_structured


def get_car_positions(configuration: Configuration):
    # TODO this should go thru cache
    return _data_source.get_car_positions(configuration)


def register_jobs(scheduler, get_configuration_func: Callable[[], Configuration]):
    global _get_configuration_func
    _get_configuration_func = get_configuration_func
    scheduler.add_job(_update_car_status, 'interval', seconds=get_configuration_func().statusRefreshSeconds)
    scheduler.add_job(_update_car_laps, 'interval', seconds=get_configuration_func().lapsRefreshSeconds)
