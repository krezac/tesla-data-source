from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import pendulum


class Configuration(BaseModel):
    enabled: bool
    carId: int
    startLatitude: float
    startLongitude: float
    startRadius: float
    startTime: Optional[pendulum.DateTime]
    hours: Optional[int]
    mergeFromLap: int
    lapsMerged: int
    consumptionRated: float
    statusRefreshSeconds: int
    lapsRefreshSeconds: int
    fioRefreshSeconds: int
    defaultMapZoom: int


class CarStatus(BaseModel):
    # id: int
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
    name: str


class Balance(BaseModel):
    amount: float
    currency: str
