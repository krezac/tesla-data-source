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
    mapLabels: List[LabelConfigItem]
    textLabels: List[LabelConfigItem]
    lapLabels: List[LabelConfigItem]
    chargingLabels: List[LabelConfigItem]


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
    startTime: pendulum.DateTime
    endTime: Optional[pendulum.DateTime]
    startTimePit: Optional[pendulum.DateTime]
    endTimePit: Optional[pendulum.DateTime]
    startOdo: float
    endOdo: Optional[float]
    insideTemp: Optional[float]
    outsideTemp: Optional[float]


    startSOC: float
    endSOC: float
    #usedSoc: float

    startRangeIdeal: float
    endRangeIdeal: float
    #usedRangeIdeal: float

    startRangeEst: float
    endRangeEst: float
    #usedRangeEst: float

    startRangeRated: float
    endRangeRated: float
    #usedRangeRated: float

    consumptionRated: float
    finished: bool
    driver_name: Optional[str]

    # calculated fields
    duration: Optional[pendulum.Duration]

    @validator('duration', always=True)
    def set_duration(cls, v, values) -> pendulum.Duration:
        return values['endTime'] - values['startTime']

    # calculated fields
    pitDuration: Optional[pendulum.Duration]

    @validator('pitDuration', always=True)
    def set_pit_uration(cls, v, values) -> pendulum.Duration:
        return values['endTimePit'] - values['startTimePit'] if values['endTimePit'] and values['startTimePit'] else 0

    distance: Optional[float]

    @validator('distance', always=True)
    def set_distance(cls, v, values) -> float:
        return values['endOdo'] - values['startOdo']

    avgSpeed: Optional[float]

    @validator('avgSpeed', always=True)
    def set_avg_speed(cls, v, values) -> float:
        return values['distance'] / values['duration'].seconds * 3600

    startEnergy: Optional[float]

    @validator('startEnergy', always=True)
    def set_start_energy(cls, v, values) -> float:
        return values['consumptionRated'] / 100 * float(values['startRangeRated'])

    endEnergy: Optional[float]

    @validator('endEnergy', always=True)
    def set_end_energy(cls, v, values) -> float:
        return values['consumptionRated'] / 100 * float(values['endRangeRated'])

    energy: Optional[float]

    @validator('energy', always=True)
    def set_energy(cls, v, values) -> float:
        return values['startEnergy'] - values['endEnergy']

    chargeEnergyAdded: Optional[float]
    chargeStartSoc: Optional[float]
    chargeEndSoc: Optional[float]
    chargeStartRangeRated: Optional[float]
    chargeEndRangeRated: Optional[float]
    chargeDurationMin: Optional[float]

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


class ChargingProcess(BaseModel):
    start_date: datetime
    end_date: Optional[datetime]
    charge_energy_added: float
    start_battery_level: int
    end_battery_level: int
    duration_min: int
    outside_temp_avg: float
    start_ideal_range_km: float
    end_ideal_range_km: float
    start_rated_range_km: float
    end_rated_range_km: float
    charge_energy_used: float
