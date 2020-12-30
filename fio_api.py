from typing import Callable
import requests
import pendulum
import os
import logging

from ds_types import Configuration, Balance

_balance_info: Balance = None
_get_configuration_func = None

logger = logging.getLogger('app.fio_api')


def update_balance():
    logger.debug("updating balance")
    global _balance_info
    global _get_configuration_func

    today = pendulum.today(tz="utc").format("YYYY-MM-DD")
    token = os.environ.get("FIO_API_TOKEN", None)
    if token:
        data = requests.get(f"https://www.fio.cz/ib_api/rest/periods/{token}/{today}/{today}/transactions.json")
        if data and data.status_code == 200:
            json_data = data.json()

            _balance_info = Balance(amount=json_data["accountStatement"]["info"]["closingBalance"],
                                    currency=json_data["accountStatement"]["info"]["currency"])
        else:
            logger.error(f"Weird FIO response data: {data}")
            _balance_info = Balance(amount=0.0, currency='???')
    else:
        logger.debug("No token")
        _balance_info = Balance(amount=0.0, currency='???')
    logger.debug("updating balance done")


def get_balance_info() -> Balance:
    global _balance_info

    if not _balance_info:
        update_balance()

    return _balance_info


def register_jobs(scheduler, get_configuration_func: Callable[[], Configuration]):
    global _get_configuration_func
    _get_configuration_func = get_configuration_func
    scheduler.add_job(update_balance, 'interval', seconds=get_configuration_func().fioRefreshSeconds)
