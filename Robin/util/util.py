import logging
import os
from datetime import date, datetime
from typing import Optional

import pytz
import pandas_market_calendars as m_cal
import robin_stocks.robinhood.authentication as auth

PACKAGE_ROOT = "/Users/meow/Desktop/AlgoTrade/Robin"


def log_info(msg):
	logging.info(f"[{get_yyyymmdd_date()} {get_current_hhmmss_time()}] {msg}.")


def set_log_level(level="INFO"):
	logging.basicConfig(level=level)


def login():
	auth.login(
		username=os.getenv("robin_user_name"),
		password=os.getenv("robin_password"),
		expiresIn=720000,
		by_sms=True
	)
	log_info("logged in robin account.")


def logout():
	auth.logout()
	log_info("logged out robin_account")


def mkdir(path):
	if not os.path.exists(path):
		os.makedirs(path)


def get_yyyymmdd_date():
	return get_datetime().strftime("%Y%m%d")


def get_yyyymmdd_hhmmss_time(time: Optional[datetime]):
	if time is None:
		return get_datetime().strftime("%Y%m%d-%H%M%S")
	else:
		return time.strftime("%Y%m%d-%H%M%S")


def get_datetime() -> datetime:
	return datetime.now(pytz.timezone('US/Eastern'))


def get_current_hhmmss_time(time: Optional[datetime] = None):
	if time is None:
		return get_datetime().strftime("%H%M%S")
	else:
		return time.strftime("%H%M%S")


def is_pre_hour():
	hhmmss_time = get_current_hhmmss_time()
	return "093000" > hhmmss_time >= "073000"


def preparing_trade():
	hhmmss_time = get_current_hhmmss_time()
	return "073000" > hhmmss_time >= "070000"


def is_after_hour():
	hhmmss_time = get_current_hhmmss_time()
	return "200000" > hhmmss_time >= "160000"


def is_early_morning():
	return get_current_hhmmss_time() < "070000"


def is_late_night():
	return get_current_hhmmss_time() >= "200000"


def is_trading_hour(time: Optional[datetime] = None):
	hhmmss = get_current_hhmmss_time(time)
	return "093000" <= hhmmss < "160000"


def log_error(msg, e):
	logging.error(f"[{get_yyyymmdd_date()} {get_current_hhmmss_time()}] {msg}.", e)


def json_serial(obj):
	if isinstance(obj, (datetime, date)):
		return obj.isoformat()
	raise TypeError("Type %s not serializable" % type(obj))


def is_trading_day():
	yyyymmdd_date = get_yyyymmdd_date()
	result = m_cal.get_calendar("NYSE").schedule(start_date=yyyymmdd_date, end_date=yyyymmdd_date)
	return not result.empty

