from ds_types import Configuration, LapStatus, ForecastResult, CarStatus
from typing import List, Optional
import logging
import pendulum

logger = logging.getLogger('app.lap_forecast')


def _get_forecast_laps(configuration: Configuration, car_laps_list: List[LapStatus]) -> List[LapStatus]:
    use_laps = configuration.forecastUseLaps
    exclude_laps = configuration.forecastExcludeLaps

    car_laps = [lap for lap in car_laps_list if lap.finished]  # care only about finished lap
    logger.debug(f"{len(car_laps)} finished laps to analyze")

    if not car_laps_list or len(car_laps) < (use_laps + exclude_laps):
        logger.info(f"not enough laps ({len(car_laps)}/{len(car_laps_list)}) from {use_laps} + {exclude_laps} needed)")
        return []

    return car_laps[-use_laps:]


def do_forecast(configuration: Configuration, car_laps_list: List[LapStatus], car_status: CarStatus, now_time: pendulum.DateTime) -> Optional[ForecastResult]:

    if not car_laps_list:
        return None

    unfinished_lap = car_laps_list[-1] if car_laps_list and not car_laps_list[-1].finished else None
    logger.debug(f"unfinished lap: {unfinished_lap is not None}")

    car_laps = _get_forecast_laps(configuration, car_laps_list)
    if not car_laps:
        return None
    logger.info(f"{len(car_laps)} laps to analyze")

    start_time = pendulum.from_timestamp(car_status.start_time.timestamp(), tz='utc')
    end_time = pendulum.from_timestamp(car_status.end_time.timestamp(), tz='utc')
    time_since_start = now_time - start_time if now_time > start_time else pendulum.period(now_time, now_time)
    time_to_end = end_time - now_time if now_time < end_time else pendulum.period(now_time, now_time)
    distance_since_start = car_status.distance

    # print(f"from start: {time_since_start.in_hours()}, to end: {time_to_end.in_hours()}, dist: {distance_since_start}")

    now = pendulum.now('utc')
    avgLapTime = pendulum.Period(now, now)
    avgPitTime = pendulum.Period(now, now)
    avgLapDistance = 0
    for lap in car_laps:
        avgLapTime += lap.duration
        avgPitTime += lap.pitDuration
        avgLapDistance += lap.distance
    logger.info(f"sum lap time {avgLapTime}, sum lap distance {avgLapDistance}")
    avgLapTime /= len(car_laps)
    avgPitTime /= len(car_laps)
    avgLapDistance /= len(car_laps)
    # print(f"avg lap time {avgLapTime}, avg pit time: {avgPitTime}, avg lap distance {avgLapDistance}")
    # print(f"avg lap time {avgLapTime}, avg lap distance {avgLapDistance}")

    unfinished_lap_remaining_time = pendulum.Period(now_time, now_time)
    unfinished_lap_remaining_distance = 0
    # calculate time and dist for the unfinished lap
    # print(f"unfinished lap duration {unfinished_lap.duration} vs avg {avgLapTime}")
    if unfinished_lap and unfinished_lap.duration < avgLapTime:
        unfinished_lap_remaining_time = avgLapTime - unfinished_lap.duration
    # print(f"unfinished lap time remaining time: {unfinished_lap_remaining_time}")
    if unfinished_lap and unfinished_lap.distance < avgLapDistance:
        unfinished_lap_remaining_distance = avgLapDistance - unfinished_lap.distance
    # print(f"unfinished lap time remaining distance: {unfinished_lap_remaining_time}")

    timeToForecast = time_to_end
    if unfinished_lap_remaining_time:
        timeToForecast -= unfinished_lap_remaining_time
    # print(f"time to forecast: {timeToForecast.in_hours()}")
    fullLapsRemaining = int(timeToForecast / (avgLapTime + avgPitTime))
    # print(f"laps to go: {fullLapsRemaining}")
    remaining_last_lap_time = timeToForecast - fullLapsRemaining * (avgLapTime + avgPitTime)  # time left after max possible full laps
    # print(f"last lap time: {remaining_last_lap_time}")
    coef = remaining_last_lap_time / (avgLapTime + avgPitTime)
    # print(f"coef: {coef}")
    last_lap_duration = avgLapTime * coef
    # print(f"last lap duration: {last_lap_duration}")
    last_pit_duration = avgPitTime * coef
    # print(f"last pit duration : {last_pit_duration}")
    last_lap_distance = avgLapDistance * coef
    # print(f"last lap distance: {last_lap_distance}")

    total_estimated_distance = distance_since_start + unfinished_lap_remaining_distance + fullLapsRemaining * avgLapDistance + last_lap_distance
    # print(f"total estimated distance: {total_estimated_distance}")

    return ForecastResult(
        avgLapDuration=avgLapTime,
        avgPitDuration=avgPitTime,
        avgLapFullDuration=avgLapTime + avgPitTime,
        avgLapDistance=avgLapDistance,
        recentLapRemainingDuration=unfinished_lap_remaining_time,
        recentLapRemainingDistance=unfinished_lap_remaining_distance,
        fullLapsRemaining=fullLapsRemaining,
        lastLapDuration=last_lap_duration,
        lastPitDuration=last_pit_duration,
        lastLapFullDuration=last_lap_duration + last_pit_duration,
        lastLapDistance=last_lap_distance,
        estimatedTotalDistance=total_estimated_distance
    )
