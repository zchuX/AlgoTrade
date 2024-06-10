import dataclasses
import glob
import json

from time import sleep

from trading.base_strategy import Action, ActionMetadata
from trading.stock_historical_collector import StockHistoricalCollector
from trading.strategies.alpha_strategy import AlphaStrategy
from trading.trading_agent import TradingAgent, TradeSnapshot, OrderMetadata
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


def persist_order_details(order: OrderMetadata):
	order_json = json.dumps(dataclasses.asdict(order), default=json_serial, indent=4)
	output_file = f"{PACKAGE_ROOT}/Data/Orders/{order.stock}.{get_yyyymmdd_date()}.json"
	log_info(f"Writing order to: {output_file}...")
	with open(output_file, 'a') as outfile:
		outfile.write(order_json)


def intraday_collecting():
	with open(f"{PACKAGE_ROOT}/Config/stock_list.txt") as f:
		stocks = f.read().split(",")
	yyyymmdd_date = get_yyyymmdd_date()
	mkdir(f"{PACKAGE_ROOT}/Data/{yyyymmdd_date}")
	login()
	trading_agent = prepare_trading_agent(stocks)

	while is_pre_hour():
		if TEST_MODE:
			log_info("TEST MODE, skip loop...")
			break
		sleep(5)

	log_info("Start Running....")
	stock_info_worker = StockHistoricalCollector(stocks)
	stock_info_worker.start()

	# stock_real_time_price_worker = StockInfoCollector(stocks)
	# stock_real_time_price_worker.start()
	alpha_strategy = AlphaStrategy(stock_info_worker, trading_agent)
	sleep(5)

	try:
		while is_trading_hour() or TEST_MODE:
			for stock in stocks:
				try:
					action: ActionMetadata = alpha_strategy.action(stock)
					if action.action == Action.BUY:
						persist_order_details(trading_agent.buy(symbol=stock, uuid=action.uuid))
					elif action.action == Action.SELL:
						persist_order_details(trading_agent.clean_all_position(symbol=stock, uuid=action.uuid))
				except Exception as e:
					log_error(f"Exception when getting stock price for {stock}.", e)
			sleep(30)
		log_info(f"Current time is not trading hour: {get_current_hhmmss_time()}.")
	finally:
		persist_trading_snapshot(trading_agent=trading_agent)
		stock_info_worker.stop()
		stock_info_worker.join()
		# stock_real_time_price_worker.stop()
		# stock_real_time_price_worker.join()


def main():
	set_log_level()
	while True:
		log_info("Loop Start...")
		while is_early_morning() or is_late_night():
			if TEST_MODE:
				log_info("TEST MODE, skip loop...")
				break
			log_info("Not trading hour, sleep 30 minutes....")
			sleep(1800)
		intraday_collecting()


if __name__ == "__main__":
	main()
