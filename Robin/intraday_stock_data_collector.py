from time import sleep

from lib.stock_info_collector import StockInfoCollector
from util.util import *


def intraday_collecting():
	with open(f"{PACKAGE_ROOT}/Config/stock_list.txt") as f:
		stocks = f.read().split(",")
	yyyymmdd_date = get_yyyymmdd_date()
	mkdir(f"{PACKAGE_ROOT}/Data/{yyyymmdd_date}")
	login()
	worker = StockInfoCollector(stocks)
	while is_pre_hour():
		sleep(5)
	log_info("Start collecting....")
	worker.start()
	try:
		while is_trading_hour():
			for stock in stocks:
				try:
					prices = worker.get_price_by_symbol(stock)
					with open(f"{PACKAGE_ROOT}/Data/{yyyymmdd_date}/{stock}.{yyyymmdd_date}", 'a') as f:
						f.write(','.join([str(price) for price in prices]))
						f.write(',')
				except Exception as e:
					log_error(f"Exception when getting stock price for {stock}: {e}.")
			sleep(30)
		log_info(f"Current time is not trading hour: {get_current_hhmmss_time()}.")
	finally:
		worker.stop()
		worker.join()


def main():
	set_log_level()
	while True:
		log_info("Loop Start...")
		while is_early_morning() or is_late_night():
			log_info("Not trading hour, sleep 30 minutes....")
			sleep(1800)
		intraday_collecting()


if __name__ == "__main__":
	main()
