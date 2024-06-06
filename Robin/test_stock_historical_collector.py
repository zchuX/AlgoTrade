from time import sleep

from lib.stock_historical_collector import StockHistoricalCollector, HjkMetadata
from util.util import *


def intraday_collecting():
	with open(f"{PACKAGE_ROOT}/Config/stock_list.txt") as f:
		stocks = f.read().split(",")
	login()
	worker = StockHistoricalCollector(stocks)
	while is_pre_hour():
		sleep(5)
	log_info("Start collecting....")
	worker.start()
	try:
		while is_trading_hour():
			for stock in stocks:
				try:
					prices = worker.get_historical_info_by_symbol(
						stock,
						[
							HjkMetadata(interval=8, smooth_parameters=[3, 3], std_interval=21, std_multiplier=3),
							HjkMetadata(interval=21, smooth_parameters=[5], std_interval=37, std_multiplier=2),
							HjkMetadata(interval=55, smooth_parameters=[5], std_interval=0, std_multiplier=0)
						])
					print(stock, prices)
				except Exception as e:
					log_error(f"Exception when getting stock price for {stock}: {e}.")
			sleep(3600)
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
