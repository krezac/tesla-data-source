#!/usr/bin/env python

import numpy as np
from gpxplotter.gpxread import vincenty
import pendulum
from ds_types import Configuration, LapStatus, LapSplit
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

csv_template = """id,start,end,odo,time,dist,speed,soc,d_soc,rng_ideal,d_rng_ideal,rng_est,d_rng_est,rng_rated,d_rng_rated,energy_lap,energy_hour,energy_left,t_in,t_out
{% for item in items -%}
{{item.id}},{{item.start_time}},{{item.end_time}},{{item.odo}},{{item.lap_time}},{{'%.2f' % item.lap_dist}},{{'%.2f' % item.lap_speed}},{{'%.2f' % item.soc}},{{'%.2f' % item.d_soc}},{{'%.2f' % item.rng_ideal}},{{'%.2f' % item.d_rng_ideal}},{{'%.2f' % item.rng_est}},{{'%.2f' % item.d_rng_est}},{{'%.2f' % item.rng_rated}}},{{'%.2f' % item.d_rng_rated}},{{'%.2f' % item.d_energy}},{{'%.2f' % item.energy_hour}},{{'%.2f' % item.energy_left}},{{'%.2f' % item.t_in}},{{'%.2f' % item.t_out}}
{% endfor %}
"""


def find_laps(configuration: Configuration, segment, region=10, min_time=5, start_idx=0) -> List[LapSplit]:
    """Return laps given latitude & longitude data.

    We assume that the first point defines the start and
    that the last point defines the end and that these are
    approximately at the same place.

    Parameters
    ----------
    segment : dict
        The data for the full track.
    region : float
        The region around the starting point which is used to
        define if we are passing through the starting point and
        begin a new lap.
    min_time : float
        This is the minimum time (in seconds) we should spend in the
        region before exiting. This will depend on the setting for region
        and the velocity for the activity.
    start_idx : integer
        The starting point for the first lap.

    """
    points = [(pt.latitude, pt.longitude) for pt in segment]
    start = (configuration.startLatitude, configuration.startLongitude) \
        if configuration.startLatitude is not None and configuration.startLongitude \
        else points[start_idx]
    time = [pt.date for pt in segment]
    # For locating the tracks, we look for point which are such that
    # we enter the starting region and pass through it.
    # For each point, find the distance to the starting region:
    distance = np.array([vincenty(point, start) for point in points])
    #np.set_printoptions(suppress=True)
    # print(distance)

    # Now look for points where we enter the region:
    # We want to avoid cases where we jump back and forth across the
    # boundary, so we set a minimum time we should spend inside the
    # region.

    # let's assume we are in pit or at the lap already at start time

    lapId = 1
    splits = []
    pit_entry_idx = None
    lap_entry_idx = None
    current_split = None

    for i, dist in enumerate(distance):
        if i == start_idx:  # in fact that just skips the first one
            if distance[0] > region:  # already at lap, so create new one
                current_split = LapSplit(
                    lapId=lapId,
                    pitEntryIdx=start_idx,
                    pitLeaveIdx=start_idx,
                    lapEntryIdx=start_idx
                )
            else:  # in pit
                current_split = LapSplit(
                    lapId=lapId,
                    pitEntryIdx=start_idx,
                )
            continue
        if dist <= region:  # we are inside the pit
            if distance[i - 1] <= region:  # was in pit before
                if pit_entry_idx:  # not recorded yet
                    delta_t = time[i] - time[pit_entry_idx]
                    if min_time < delta_t.total_seconds():  # check time in pit
                        if current_split:  # long enough, dump the previous one to output list
                            current_split.lapLeaveIdx = pit_entry_idx
                            splits.append(current_split)
                        current_split = LapSplit(lapId=str(lapId), pitEntryIdx=pit_entry_idx)  # and create new one
                        lapId += 1
                        pit_entry_idx = None
            else:  # entered the pit (left lap)
                pit_entry_idx = i  # remember entry, start measuring time
        else:  # outside of pit (on lap)
            if distance[i - 1] > region:  # was on lap before
                if lap_entry_idx:  # not recorded yet
                    delta_t = time[i] - time[lap_entry_idx]
                    if min_time < delta_t.total_seconds():  # check time in pit
                        if current_split:  # long enough, record switch to lap
                            current_split.pitLeaveIdx = lap_entry_idx
                            current_split.lapEntryIdx = lap_entry_idx
                        pit_entry_idx = None
            else:  # entered the lap (left pit)
                lap_entry_idx = i  # remember exit, start measuring time

    if current_split and current_split.lapEntryIdx:  # do not include the one having just pit time
        splits.append(current_split)

    agg_splits = aggregate_splits(configuration, splits)

    # new
    statuses = extract_lap_statuses(configuration, agg_splits, segment)
    if not agg_splits[-1].lapLeaveIdx or distance[agg_splits[-1].lapLeaveIdx] > region:
        statuses[-1].finished = False  # outside of region
    return statuses


def aggregate_splits(configuration: Configuration, splits: List[LapSplit]) -> List[LapSplit]:
    agg_start = configuration.mergeFromLap
    agg_count = configuration.lapsMerged

    if agg_count <= 1 or len(splits) <= agg_start:
        return splits

    agg_splits = []

    # copy the ones before start (1, 2, 3, ... agg_start - 1)
    for i in range(agg_start - 1):
        agg_splits.append(splits[i])

    group_count = (len(splits) - agg_start + 1) // agg_count
    for i in range(group_count):
        first = splits[agg_start - 1 + i * agg_count]
        last = splits[agg_start - 1 + (i + 1) * agg_count - 1]
        split = LapSplit(
            lapId=first.lapId + "-" + last.lapId,
            pitEntryIdx=first.pitEntryIdx,
            pitLeaveIdx=first.pitLeaveIdx,
            lapEntryIdx=first.lapEntryIdx,
            lapLeaveIdx=last.lapLeaveIdx
        )
        agg_splits.append(split)

    for i in range(agg_start + agg_count * group_count - 1, len(splits)):
        agg_splits.append(splits[i])
    return agg_splits


def extract_lap_statuses(configuration: Configuration, splits: List[LapSplit], segment: List) -> List[LapStatus]:
    out = []
    for split in splits:
        out.append(extract_lap_status(configuration, split, segment))
    return out


def extract_lap_status(configuration: Configuration, split: LapSplit, segment) -> LapStatus:
    """ Lap data from database:
    xx id |
    xx date           |
    xx latitude  |
    xx longitude |
    -- speed |
    -- power |
    xx odometer   |
    xx ideal_battery_range_km |
    xx battery_level |
    xx outside_temp |
    -- elevation |
    -- fan_status |
    -- driver_temp_setting |
    -- passenger_temp_set ting |
    -- is_climate_on |
    -- is_rear_defroster_on |
    -- is_front_defroster_on |
    -- car_id |
    -- drive_id |
    xx inside_temp |
    -- battery_heater |
    -- battery_heater_on |
    -- battery_heater_no_power |
    xx est_battery_range_km |
    xx rated_battery_range_km
    """

    lap_start = split.lapEntryIdx
    lap_stop = split.lapLeaveIdx + 1 if split.lapLeaveIdx else len(segment) - 1
    lap_data = segment[lap_start:lap_stop]

    pit_start = split.pitEntryIdx
    pit_stop = split.pitLeaveIdx + 1 if split.pitLeaveIdx else len(segment) - 1
    pit_data = segment[pit_start:pit_stop]


    return LapStatus(
        id=split.lapId,
        startTime=pendulum.instance(lap_data[0].date, 'utc'),
        endTime=pendulum.instance(lap_data[-1].date, 'utc'),

        startTimePit=pendulum.instance(pit_data[0].date, 'utc'),
        endTimePit=pendulum.instance(pit_data[-1].date, 'utc'),

        startOdo=lap_data[0].odometer,
        endOdo=lap_data[-1].odometer,

        insideTemp=lap_data[-1].inside_temp,
        outsideTemp=lap_data[-1].outside_temp,

        startSOC=lap_data[0].usable_battery_level,
        endSOC=lap_data[-1].usable_battery_level,

        startRangeIdeal=lap_data[0].ideal_battery_range_km,
        endRangeIdeal=lap_data[-1].ideal_battery_range_km,

        startRangeEst=lap_data[0].est_battery_range_km,
        endRangeEst=lap_data[-1].est_battery_range_km,

        startRangeRated=lap_data[0].rated_battery_range_km,
        endRangeRated=lap_data[-1].rated_battery_range_km,

        consumptionRated=configuration.consumptionRated,
        finished=True  # will be set later
    )
