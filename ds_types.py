from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CarStatus(BaseModel):
    id: int
    date: datetime
    latitude: float
    longitude: float
    speed: Optional[float]
    power: float
    odometer: float
    ideal_battery_range_km: Optional[float]
    battery_level: int
    outside_temp: Optional[float]
    elevation: Optional[float]
    fan_status: int
    driver_temp_setting: float
    passenger_temp_setting: float
    is_climate_on: str
    is_rear_defroster_on: str
    is_front_defroster_on: str
    car_id: int
    drive_id: Optional[int]
    inside_temp: Optional[float]
    battery_heater: str
    battery_heater_on: str
    battery_heater_no_power: str
    est_battery_range_km: Optional[float]
    rated_battery_range_km: Optional[float]
    usable_battery_level: int
