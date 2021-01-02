from pydantic import BaseModel, validator
from typing import Optional, List, Dict
from datetime import datetime
import pendulum


class LabelConfigItem(BaseModel):
    field: str
    label: str
    format: Optional[str]
    format_function: Optional[str]
    unit: Optional[str]
    default: Optional[str]


class Configuration(BaseModel):
    enabled: bool
    defaultPageTitle: str
    defaultPageTemplate: str
    debugSql: bool
    carId: int
    startLatitude: float
    startLongitude: float
    startRadius: float
    startTime: Optional[datetime]
    hours: Optional[int]
    mergeFromLap: int
    lapsMerged: int
    consumptionRated: float
    statusRefreshSeconds: int
    lapsRefreshSeconds: int
    fioRefreshSeconds: int
    defaultMapZoom: int
    previousLaps: int
    minTimeLap: int
    forecastUseLaps: int
    forecastExcludeLaps: int
    mapLabels: List[LabelConfigItem]
    textLabels: List[LabelConfigItem]
    lapLabelsTotal: List[LabelConfigItem]
    lapLabelsRecent: List[LabelConfigItem]
    lapLabelsPrevious: List[LabelConfigItem]
    chargingLabels: List[LabelConfigItem]
    forecastLabels: List[LabelConfigItem]


class CarStatus(BaseModel):
    id: int
    date: datetime
    latitude: Optional[float]
    longitude: Optional[float]
    speed: Optional[float]
    power: Optional[float]
    odometer: Optional[float]
    ideal_battery_range_km: Optional[float]
    battery_level: Optional[int]
    outside_temp: Optional[float]
    elevation: Optional[float]
    # fan_status: Optional[int]
    # driver_temp_setting: Optional[float]
    # passenger_temp_setting: Optional[float]
    # is_climate_on: Optional[str]
    # is_rear_defroster_on: Optional[str]
    # is_front_defroster_on: Optional[str]
    # car_id: Optional[int]
    # drive_id: Optional[int]
    inside_temp: Optional[float]
    # battery_heater: Optional[str]
    # battery_heater_on: Optional[str]
    # battery_heater_no_power: Optional[str]
    est_battery_range_km: Optional[float]
    rated_battery_range_km: Optional[float]
    usable_battery_level: Optional[int]
    car_name: str
    driver_name: Optional[str]

    # calculated fields (diff from initial status). The ALL NEED to be optional (as they are filled later).
    start_odometer: Optional[float]
    distance: Optional[float]
    lap: Optional[str]
    lap_distance: Optional[float]
    lap_time: Optional[pendulum.Duration]
    start_time: Optional[pendulum.DateTime]
    end_time: Optional[pendulum.DateTime]
    time_since_start: Optional[pendulum.Duration]
    time_to_end: Optional[pendulum.Duration]


class Balance(BaseModel):
    amount: float
    currency: str


class LapStatus(BaseModel):
    """
    raw fields only
    """
    id: str  # string because of aggregating
    startTime: Optional[pendulum.DateTime]
    endTime: Optional[pendulum.DateTime]
    startTimePit: Optional[pendulum.DateTime]
    endTimePit: Optional[pendulum.DateTime]
    startOdo: Optional[float]
    endOdo: Optional[float]
    insideTemp: Optional[float]
    outsideTemp: Optional[float]


    startSOC: Optional[float]
    endSOC: Optional[float]
    #usedSoc: float

    startRangeIdeal: Optional[float]
    endRangeIdeal: Optional[float]
    #usedRangeIdeal: float

    startRangeEst: Optional[float]
    endRangeEst: Optional[float]
    #usedRangeEst: float

    startRangeRated: Optional[float]
    endRangeRated: Optional[float]
    #usedRangeRated: float

    consumptionRated: float
    finished: bool
    driver_name: Optional[str]

    # calculated fields
    duration: Optional[pendulum.Duration]

    @validator('duration', always=True)
    def set_duration(cls, v, values) -> pendulum.Duration:
        now = pendulum.now(tz='utc')
        return (values['endTime'] if 'endTime' in values and values['endTime'] else now) - \
               (values['startTime'] if 'startTime' in values and values['startTime'] else now)

    # calculated fields
    pitDuration: Optional[pendulum.Duration]

    @validator('pitDuration', always=True)
    def set_pit_uration(cls, v, values) -> pendulum.Duration:
        now = pendulum.now(tz='utc')
        return (values['endTimePit'] if 'endTimePit' in values and values['endTimePit'] else now) - \
               (values['startTimePit'] if 'startTimePit' in values and values['startTimePit'] else now)

    distance: Optional[float]

    @validator('distance', always=True)
    def set_distance(cls, v, values) -> float:
        return values['endOdo'] - values['startOdo'] if values['endOdo'] and values['startOdo'] else 0

    avgSpeed: Optional[float]

    @validator('avgSpeed', always=True)
    def set_avg_speed(cls, v, values) -> float:
        return values['distance'] / values['duration'].seconds * 3600 if 'duration' in values and values['duration'] else 0

    startEnergy: Optional[float]

    @validator('startEnergy', always=True)
    def set_start_energy(cls, v, values) -> float:
        return values['consumptionRated'] / 100 * float(values['startRangeRated']) if 'startRangeRated' in values and values['startRangeRated'] else None

    endEnergy: Optional[float]

    @validator('endEnergy', always=True)
    def set_end_energy(cls, v, values) -> float:
        return values['consumptionRated'] / 100 * float(values['endRangeRated']) if 'endRangeRated' in values and values['endRangeRated'] else None

    energy: Optional[float]

    @validator('energy', always=True)
    def set_energy(cls, v, values) -> float:
        return values['startEnergy'] - values['endEnergy'] if values['startEnergy'] and values['endEnergy'] else None

    chargeStartTime: Optional[pendulum.DateTime]
    chargeEndTime: Optional[pendulum.DateTime]
    chargeEnergyAdded: Optional[float]
    chargeStartSoc: Optional[float]
    chargeEndSoc: Optional[float]
    chargeStartRangeRated: Optional[float]
    chargeEndRangeRated: Optional[float]
    chargeSocAdded: Optional[float]

    # TODO this doesn't work for some reason (the one above does). explicit assignement in car_data
    # @validator('chargeSocAdded', always=True)
    # def set_soc_added(cls, v, values) -> float:
    #     return values['chargeEndSoc'] - values['chargeStartSoc'] if values['chargeEndSoc'] and values['chargeStartSoc'] else 0

    chargeRangeRatedAdded: Optional[float]

    # TODO this doesn't work for some reason (the one above does). explicit assignement in car_data
    #@validator('chargeRangeRatedAdded', always=True)
    #def set_charge_energy_added(cls, v, values) -> float:
    #    return values['chargeEndRangeRated'] - values['chargeStartRangeRated'] if values['chargeEndRangeRated'] and values['chargeStartRangeRated'] else 0

    chargeDuration: Optional[pendulum.Duration]

    @validator('chargeDuration', always=True)
    def set_charge_energy_added(cls, v, values) -> pendulum.Duration:
        return values['chargeEndTime'] - values['chargeStartTime'] if values['chargeEndTime'] and values['chargeStartTime'] else pendulum.Period(pendulum.now(), pendulum.now())

    chargeMaxPower: Optional[float]
    chargeEnergyPerHour: Optional[float]


class LapsList(BaseModel):
    __root__: List[LapStatus]


class LapSplit(BaseModel):
    lapId: str
    pitEntryIdx: Optional[int]
    pitLeaveIdx: Optional[int]
    lapEntryIdx: Optional[int]
    lapLeaveIdx: Optional[int]


class DriverChange(BaseModel):
    name: str
    dateFrom: Optional[datetime]


class LabelItem(BaseModel):
    label: str
    value: Optional[str]


class JsonLapsResponse(BaseModel):
    total: List[LabelItem]
    previous: List[List[LabelItem]]
    recent: List[LabelItem]


class JsonStatusResponse(BaseModel):
    lat: float
    lon: float
    mapLabels: List[LabelItem]
    textLabels: List[LabelItem]
    forecastLabels: List[LabelItem]


class ChargingProcess(BaseModel):
    start_date: datetime
    end_date: Optional[datetime]
    charge_energy_added: Optional[float]
    start_battery_level: Optional[int]
    end_battery_level: Optional[int]
    duration_min: Optional[int]
    outside_temp_avg: Optional[float]
    start_ideal_range_km: Optional[float]
    end_ideal_range_km: Optional[float]
    start_rated_range_km: Optional[float]
    end_rated_range_km: Optional[float]
    charge_energy_used: Optional[float]
    max_power: Optional[float]


class ForecastResult(BaseModel):
    avgLapDuration: pendulum.Duration
    avgPitDuration: pendulum.Duration
    avgLapFullDuration: pendulum.Duration
    avgLapDistance: float
    recentLapRemainingDuration: pendulum.Duration
    recentLapRemainingDistance: float
    fullLapsRemaining: int
    lastLapDuration: pendulum.Duration
    lastPitDuration: pendulum.Duration
    lastLapFullDuration: pendulum.Duration
    lastLapDistance: float
    estimatedTotalDistance: float
