from typing import Callable, List, Dict, Optional
import pendulum
import logging

from teslamate_data_source import TeslamateDataSource
from ds_types import Configuration, LapStatus, CarStatus, DriverChange, LapsList, JsonLapsResponse, JsonStatusResponse, ForecastResult
from labels import generate_labels
import lap_analyzer
from lap_forecast import do_forecast
from datetime import datetime, timezone
from gpxplotter.gpxread import vincenty


logger = logging.getLogger('app.car_data')

_get_configuration_func: Callable[[], Configuration] = None
_data_source = TeslamateDataSource()

_car_status: CarStatus = None
_car_status_formatted: JsonStatusResponse = None
_initial_status: CarStatus = None
_car_laps_list: List[LapStatus] = None
_car_laps_formatted: JsonLapsResponse = None
_car_charging_processes = None
_forecast_result: ForecastResult = None


def _add_calculated_fields(status: CarStatus, initial_status: CarStatus, configuration: Configuration):
    start_time = pendulum.from_timestamp(configuration.startTime.timestamp(), tz='utc')
    now = pendulum.now(tz='utc')
    end_time = start_time.add(hours=configuration.hours)

    status.start_time = start_time
    status.end_time = end_time
    status.start_odometer = initial_status.odometer
    status.distance = status.odometer - initial_status.odometer if status.odometer and initial_status.odometer else 0
    status.time_since_start = pendulum.period(start_time, now, True) if now >= start_time else pendulum.period(now, now, True)
    status.time_to_end = pendulum.period(now, end_time, True) if now <= end_time else pendulum.period(now, now, True)

    start = (configuration.startLatitude, configuration.startLongitude)
    loc = (status.latitude, status.longitude)
    status.direct_start_distance = vincenty(loc, start) / 1000.0  # from m to km


    if _car_laps_list:
        current_lap = _car_laps_list[-1]
        status.lap = current_lap.id
        status.lap_distance = current_lap.distance
        status.lap_time = current_lap.duration


def _update_car_status():
    global _initial_status
    global _car_status
    global _car_status_formatted
    global _data_source
    global _get_configuration_func
    global _forecast_result

    if not _initial_status:
        logger.debug("updating initial car status")
        _initial_status = _data_source.get_car_status(_get_configuration_func(), _get_configuration_func().startTime)
        logger.debug("updating initial car status done")

    logger.debug("updating car status")
    _car_status = _data_source.get_car_status(_get_configuration_func(), pendulum.parse('2021-01-03 02:26:39', tz='utc'))
    if _car_status and _initial_status:
        logger.debug("updating calculated fields")
        _add_calculated_fields(_car_status, _initial_status, _get_configuration_func())

    _update_forecast_result()

    # build the formatted form
    _car_status_formatted = JsonStatusResponse(
        lat=_car_status.latitude,
        lon=_car_status.longitude,
        mapLabels=generate_labels(_get_configuration_func().mapLabels, _car_status.dict()),
        textLabels=generate_labels(_get_configuration_func().textLabels, _car_status.dict()),
        forecastLabels=generate_labels(_get_configuration_func().forecastLabels, _forecast_result.dict() if _forecast_result else {})
    )
    logger.debug("updating car status done")


def _update_car_laps():
    global _car_laps_list
    global _car_laps_formatted
    global _get_configuration_func
    global _car_charging_processes

    logger.debug("updating car laps")
    configuration = _get_configuration_func()
    positions = _data_source.get_car_positions(configuration)
    _car_laps_list = lap_analyzer.find_laps(configuration, positions, configuration.startRadius, 0, 0)
    _car_charging_processes = _data_source.get_charging_processes(configuration)

    # load driver names
    dates = [l.startTime for l in _car_laps_list]
    if dates:
        driver_map = _data_source.get_driver_changes(configuration, dates)
        for l in _car_laps_list:
            if l.startTime in driver_map:
                l.driver_name = driver_map[l.startTime].name

    # fill charging data
    first = True
    for l in _car_laps_list:
        if first:  # ignore any charging for first lap
            first = False
            continue
        for charging in _car_charging_processes:
            if not charging.end_date:
                continue  # incomplete records - they are visible in the db from time to time
            charging.start_date = charging.start_date.replace(tzinfo=timezone.utc)
            charging.end_date = charging.end_date.replace(tzinfo=timezone.utc)
            if l.startTimePit <= charging.start_date and (not l.endTimePit or l.endTimePit > charging.start_date ):
                # set the value
                l.chargeStartTime = pendulum.from_timestamp(charging.start_date.timestamp())
                l.chargeEndTime = pendulum.from_timestamp(charging.end_date.timestamp())
                l.chargeEnergyAdded = charging.charge_energy_added
                l.chargeStartSoc = charging.start_battery_level
                l.chargeEndSoc = charging.end_battery_level
                l.chargeStartRangeRated = charging.start_rated_range_km
                l.chargeEndRangeRated = charging.end_rated_range_km
                l.chargeRangeRatedAdded = charging.end_rated_range_km - charging.start_rated_range_km  # the validator doesn't fill it for some reason
                l.chargeSocAdded = charging.end_battery_level - charging.start_battery_level  # the validator doesn't fill it for some reason
                l.chargeDuration = pendulum.Period(charging.start_date, charging.end_date) if charging.start_date and charging.end_date else None
                l.chargeMaxPower = charging.max_power
                l.chargeEnergyPerHour = charging.charge_energy_added * 3600.0 / l.chargeDuration.in_seconds()
                break  # load only one charging

    total_lap = _calculate_lap_total(_car_laps_list) if _car_laps_list else None
    recent_lap = _car_laps_list[-1] if _car_laps_list else None
    prev_lap_list = _car_laps_list[-configuration.previousLaps - 1:-1] if len(_car_laps_list) > 0 else []
    prev_lap_list.reverse()  # to have newest on top

    total_formatted = generate_labels(_get_configuration_func().lapLabelsTotal, total_lap.dict() if total_lap else {})
    previous_formatted = [generate_labels(_get_configuration_func().lapLabelsPrevious, lap.dict()) for lap in prev_lap_list]
    recent_formatted = generate_labels(_get_configuration_func().lapLabelsRecent, recent_lap.dict() if recent_lap else {})

    _car_laps_formatted = JsonLapsResponse(
        total=total_formatted,
        previous=previous_formatted,
        recent=recent_formatted
    )

    logger.debug("updating car laps done")


def _calculate_lap_total(laps: List[LapStatus]) -> LapStatus:
    start_lap = laps[0]
    end_lap = laps[-1]

    total_status = LapStatus(
        id=f"{start_lap.id} - {end_lap.id}",
        startTimePit=start_lap.startTimePit,
        endTimePit=start_lap.endTimePit,
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
    chargeSocAdded = 0
    chargeEnergyAdded = 0
    chargeRangeAdded = 0
    now = pendulum.now(tz='utc')
    duration = pendulum.Period(now, now)
    pit_duration = pendulum.Period(now, now)
    chargeDuration = pendulum.Period(now, now)
    for lap in laps:
        energy += lap.energy if lap.energy else 0
        duration += lap.duration if lap.duration else pendulum.Period(now, now)
        pit_duration += lap.pitDuration if pit_duration else pendulum.Period(now, now)
        chargeSocAdded += lap.chargeSocAdded if lap.chargeSocAdded else 0
        chargeEnergyAdded += lap.chargeEnergyAdded if lap.chargeEnergyAdded else 0
        chargeRangeAdded += lap.chargeRangeRatedAdded if lap.chargeRangeRatedAdded else 0
        chargeDuration += lap.chargeDuration if lap.chargeDuration else pendulum.Period(now, now)
    total_status.energy = energy
    total_status.duration = duration
    total_status.pitDuration = pit_duration
    total_status.chargeSocAdded = chargeSocAdded
    total_status.chargeEnergyAdded = chargeEnergyAdded
    total_status.chargeRangeRatedAdded = chargeEnergyAdded
    total_status.chargeDuration = chargeDuration

    return total_status


def _update_forecast_result():
    global _car_laps_list
    global _car_status
    global _get_configuration_func
    global _forecast_result

    logger.info("updating forecast")

    if not _car_status and _car_laps_list:
        logger.info("no data, no forecast")
        return

    print(_get_configuration_func())
    print(_car_laps_list)
    print(_car_status)
    _forecast_result = do_forecast(_get_configuration_func(), _car_laps_list, _car_status, pendulum.now(tz='utc'))
    logger.info("updating done")


def get_car_status() -> CarStatus:
    global _car_status
    if not _car_status:
        _update_car_status()
    return _car_status


def get_car_status_formatted() -> CarStatus:
    global _car_status_formatted
    if not _car_status_formatted:
        _update_car_status()
    return _car_status_formatted


def get_car_laps_list() -> LapsList:
    global _car_laps_list
    if not _car_laps_list:
        _update_car_laps()
    return _car_laps_list


def get_car_laps_formatted() -> JsonLapsResponse:
    global _car_laps_formatted
    if not _car_laps_formatted:
        _update_car_laps()
    return _car_laps_formatted


def get_forecast_result() -> Optional[ForecastResult]:
    global _forecast_result
    if not _forecast_result:
        _update_forecast_result()
    return _forecast_result


def apply_driver_change(driver_change: DriverChange):
    global _get_configuration_func
    return _data_source.apply_driver_change(_get_configuration_func(), driver_change)


def get_driver_changes(self, dates: List[datetime]) -> Dict[datetime, DriverChange]:
    global _get_configuration_func
    return _data_source.get_driver_changes(_get_configuration_func(), dates)


def register_jobs(scheduler, get_configuration_func: Callable[[], Configuration]):
    global _get_configuration_func
    _get_configuration_func = get_configuration_func
    scheduler.add_job(_update_car_status, 'interval', seconds=get_configuration_func().statusRefreshSeconds)
    scheduler.add_job(_update_car_laps, 'interval', seconds=get_configuration_func().lapsRefreshSeconds)
