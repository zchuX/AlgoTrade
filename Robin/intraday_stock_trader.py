import dataclasses
import glob
import json

from time import sleep
from trading.stock_historical_collector import StockHistoricalCollector, HjkMetadata, BollingerMetadata
from trading.stock_info_collector import StockInfoCollector
from trading.trading_agent import TradingAgent, TradeSnapshot
from util.util import *

TEST_MODE = True


def prepare_trading_agent(stocks: list[str]):
	snapshot_files = glob.glob(f"{PACKAGE_ROOT}/Data/TradingSnapshot/*.json")
	trade_snapshot = None
	if snapshot_files:
		latest_snapshot = max(snapshot_files, key=os.path.getctime)
		log_info(f"Loading trading snapshot from: {latest_snapshot}...")
		with open(latest_snapshot, 'r') as openfile:
			json_object = json.load(openfile)
			trade_snapshot = TradeSnapshot(**json_object)
	else:
		log_info(f"No active trading snapshot, create an empty one..")
	trading_agent = TradingAgent(
		symbols=stocks,
		trade_snapshot=trade_snapshot
	)
	return trading_agent


def persist_trading_snapshot(trading_agent: TradingAgent):
	snapshot: TradeSnapshot = trading_agent.snapshot()
	snapshot_json = json.dumps(dataclasses.asdict(snapshot), default=json_serial, indent=4)
	output_file = f"{PACKAGE_ROOT}/Data/TradingSnapshot/snapshot.{get_yyyymmdd_hhmmss_time()}.json"
	log_info(f"Writing trading snapshot to: {output_file}...")
	with open(output_file, 'w') as outfile:
		outfile.write(snapshot_json)


def intraday_collecting():
	with open(f"{PACKAGE_ROOT}/Config/stock_list.txt") as f:
		stocks = f.read().split(",")
	yyyymmdd_date = get_yyyymmdd_date()
	mkdir(f"{PACKAGE_ROOT}/Data/{yyyymmdd_date}")
	login()
	trading_agent = prepare_trading_agent(stocks)

	while is_pre_hour():
		sleep(5)
	log_info("Start collecting....")
	real_time_price_worker = StockInfoCollector(stocks)
	stock_info_worker = StockHistoricalCollector(stocks)
	real_time_price_worker.start()
	stock_info_worker.start()
	sleep(5)

	try:
		if TEST_MODE:
			return
		while is_trading_hour():
			for stock in stocks:
				try:
					prices = real_time_price_worker.get_price_by_symbol(stock)
					stock_info_df = stock_info_worker.get_historical_info_by_symbol(
						stock,
						[
							HjkMetadata(interval=8, smooth_parameters=[3, 3], std_interval=21, std_multiplier=3),
							HjkMetadata(interval=21, smooth_parameters=[5], std_interval=37, std_multiplier=2),
							HjkMetadata(interval=55, smooth_parameters=[5], std_interval=0, std_multiplier=0)
						],
						BollingerMetadata(window=20, no_of_std=2)
					)

					with open(f"{PACKAGE_ROOT}/Data/{yyyymmdd_date}/{stock}.{yyyymmdd_date}", 'a') as f:
						f.write(','.join([str(price) for price in prices]))
						f.write(',')

				except Exception as e:
					log_error(f"Exception when getting stock price for {stock}.", e)
			sleep(30)
		log_info(f"Current time is not trading hour: {get_current_hhmmss_time()}.")
	finally:
		persist_trading_snapshot(trading_agent=trading_agent)
		real_time_price_worker.stop()
		stock_info_worker.stop()
		real_time_price_worker.join()
		stock_info_worker.join()


def main():
	set_log_level()
	while True:
		log_info("Loop Start...")
		# while is_early_morning() or is_late_night():
		# 	log_info("Not trading hour, sleep 30 minutes....")
		# 	sleep(1800)
		intraday_collecting()


if __name__ == "__main__":
	main()
