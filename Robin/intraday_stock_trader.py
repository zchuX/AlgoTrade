import dataclasses
import glob
import json

from time import sleep
from datetime import timedelta

import dateutil

from trading.base_strategy import Action, ActionMetadata, BaseStrategy
from trading.stock_historical_collector import StockHistoricalCollector
from trading.strategies.alpha_strategy import AlphaStrategy
from trading.trading_agent import TradingAgent, TradeSnapshot, OrderMetadata
from util.util import *

TEST_MODE = False

TEST_DATE_TIME = datetime(2024, 6, 10, 9, 30, 0, tzinfo=pytz.timezone('US/Eastern'))


def prepare_trading_agent(stocks: list[str]):
	snapshot_files = glob.glob(f"{PACKAGE_ROOT}/Data/TradingSnapshot/*.json")
	trade_snapshot = None
	if snapshot_files:
		latest_snapshot = max(snapshot_files, key=os.path.getctime)
		log_info(f"Loading trading snapshot from: {latest_snapshot}...")
		with open(latest_snapshot, 'r') as openfile:
			json_object = json.load(openfile)
			trade_snapshot = TradeSnapshot(**json_object)
			trade_snapshot.time = dateutil.parser.parse(trade_snapshot.time)
			for symbol in trade_snapshot.active_orders:
				trade_snapshot.active_orders[symbol] = [
					OrderMetadata(**order) for order in trade_snapshot.active_orders[symbol]
				]
	else:
		log_info(f"No active trading snapshot, create an empty one..")
	trading_agent = TradingAgent(
		symbols=stocks,
		trade_snapshot=trade_snapshot,
		test_mode=TEST_MODE
	)
	return trading_agent


def persist_trading_snapshot(
	trading_agent: TradingAgent,
	prices: Optional[dict[str, float]] = None,
	time: Optional[datetime] = None):
	snapshot: TradeSnapshot = trading_agent.test_snapshot(prices, time) if TEST_MODE else trading_agent.snapshot()
	snapshot_json = json.dumps(dataclasses.asdict(snapshot), default=json_serial, indent=4)
	output_file = f"{PACKAGE_ROOT}/Data/TradingSnapshot/snapshot.{get_yyyymmdd_hhmmss_time(time)}.json"
	log_info(f"Writing trading snapshot to: {output_file}...")
	with open(output_file, 'w') as outfile:
		outfile.write(snapshot_json)


def persist_order_details(order: OrderMetadata):
	if order is None:
		return
	output_file = f"{PACKAGE_ROOT}/Data/Orders/{order.stock}.{get_yyyymmdd_date()}.json"
	orders = []
	if os.path.exists(output_file):
		with open(output_file, 'r') as f:
			json_data = f.read()
		orders = json.loads(json_data)
	orders.append(dataclasses.asdict(order))
	orders_json = json.dumps(orders, default=json_serial, indent=4)
	log_info(f"Writing order to: {output_file}...")
	with open(output_file, 'w') as outfile:
		outfile.write(orders_json)


def run_test_cycles(
	stocks: list[str],
	trading_agent: TradingAgent,
	stock_info_worker: StockHistoricalCollector,
	strategy: BaseStrategy
):
	log_info("Running test cycles...")
	time = TEST_DATE_TIME
	last_snapshot_time = time
	prices = dict()
	while is_trading_hour(time):
		log_info(f"CurrentTime: {time}")
		for stock in stocks:
			df = stock_info_worker.get_historical_info_by_symbol(stock)
			action: ActionMetadata = strategy.action(stock, time)
			price = list(df.loc[df["begins_at"] < time - timedelta(minutes=5)]["close_price"])[-1]
			prices[stock] = price
			if action.action == Action.BUY:
				persist_order_details(trading_agent.test_buy(
					symbol=stock, uuid=action.uuid, price=price, time=time))
			elif action.action == Action.SELL:
				persist_order_details(
					trading_agent.test_clean_all_position(symbol=stock, uuid=action.uuid, price=price, time=time))
		time += timedelta(minutes=5)
		sleep(1)
		if last_snapshot_time + timedelta(hours=1) < time:
			persist_trading_snapshot(trading_agent=trading_agent, prices=prices, time=time)
			last_snapshot_time = time
	log_info(f"Current time is not trading hour: {get_current_hhmmss_time()}.")
	persist_trading_snapshot(trading_agent=trading_agent, prices=prices, time=time)


def intraday_collecting():
	with open(f"{PACKAGE_ROOT}/Config/stock_list.txt") as f:
		stocks = f.read().split(",")
	login()
	trading_agent = prepare_trading_agent(stocks)

	while preparing_trade():
		if TEST_MODE:
			log_info("TEST MODE, skip loop...")
			break
		sleep(5)

	log_info("Start Running....")
	stock_info_worker = StockHistoricalCollector(stocks)
	stock_info_worker.start()
	alpha_strategy = AlphaStrategy(stock_info_worker, trading_agent)
	sleep(5)

	try:
		if TEST_MODE:
			run_test_cycles(stocks, trading_agent, stock_info_worker, alpha_strategy)
			return

		last_snapshot_time = datetime.now()
		persist_trading_snapshot(trading_agent=trading_agent)
		while is_pre_hour() or is_trading_hour() or is_after_hour():
			is_extended_hour = is_after_hour() or is_pre_hour()
			log_info("Running loop....")
			for stock in stocks:
				try:
					action: ActionMetadata = alpha_strategy.action(stock)
					if action.action == Action.BUY:
						persist_order_details(
							trading_agent.buy(
								symbol=stock,
								uuid=action.uuid,
								extended_hour=is_extended_hour
							)
						)
					elif action.action == Action.SELL:
						persist_order_details(
							trading_agent.clean_all_position(
								symbol=stock,
								uuid=action.uuid,
								extended_hour=is_extended_hour
							)
						)
				except Exception as e:
					log_error(f"Exception when getting stock price for {stock}.", e)
			if last_snapshot_time + timedelta(hours=1) < datetime.now():
				persist_trading_snapshot(trading_agent=trading_agent)
				last_snapshot_time = datetime.now()
			log_info("Completing loop...")
			sleep(60)
		log_info(f"Current time is not trading hour: {get_current_hhmmss_time()}.")
	except Exception as e:
		log_error(f"Exception running the main cycle...", e)
	finally:
		if not TEST_MODE:
			persist_trading_snapshot(trading_agent=trading_agent)
		stock_info_worker.stop()
		stock_info_worker.join()


def main():
	set_log_level()
	while True:
		log_info("Loop start")
		while is_early_morning() or is_late_night() or not is_trading_day():
			if TEST_MODE:
				log_info("TEST MODE, skip loop...")
				break
			log_info(f"Not trading hour: is_early_morning: {is_early_morning()}, is_late_night: {is_late_night()}, "
					 f"is_trading_day: {is_trading_day()}, sleep 30 minutes....")
			sleep(1800)
		intraday_collecting()
		if TEST_MODE:
			break


if __name__ == "__main__":
	main()
