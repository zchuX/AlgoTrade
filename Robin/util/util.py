import logging
import os
from datetime import date, datetime

import robin_stocks.robinhood.authentication as auth

PACKAGE_ROOT = "/Users/meow/Desktop/Robin"


def log_info(msg):
    logging.info(f"[{get_yyyymmdd_date()} {get_current_hhmmss_time()}] {msg}.")


def set_log_level(level="INFO"):
    logging.basicConfig(level=level)


def login():
    auth.login(username=os.getenv("robin_user_name"), password=os.getenv("robin_password"), expiresIn=720000,
               by_sms=True)
    log_info("logged in robin account.")


def logout():
    auth.logout()
    log_info("logged out robin_account")


def mkdir(path):
    if not os.path.exists(path):
        os.makedirs(path)


def get_yyyymmdd_date():
    return date.today().strftime("%Y%m%d")


def get_current_hhmmss_time():
    return datetime.now().strftime("%H%M%S")


def is_pre_hour():
    hhmmss_time = get_current_hhmmss_time()
    return "093000" > hhmmss_time >= "090000"


def is_early_morning():
    return get_current_hhmmss_time() < "090000"


def is_late_night():
    return get_current_hhmmss_time() >= "160000"


def is_trading_hour():
    hhmmss = get_current_hhmmss_time()
    return "093000" <= hhmmss < "160000"


def log_error(msg):
    logging.error(f"[{get_yyyymmdd_date()} {get_current_hhmmss_time()}] {msg}.")
