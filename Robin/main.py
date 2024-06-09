import os
import logging
import time

from trading.stock_info_collector import StockInfoCollector
from trading.trade_executor import TradeExecutor
from util.util import login, logout, set_log_level


def main():
	set_log_level()
	try:
		login()
		stock_collectors = [StockInfoCollector(["TSLA","C"], 2), StockInfoCollector(["AAPL"], 2)]
		for coll in stock_collectors:
			coll.start()
		for i in range(4):
			time.sleep(2)
			print(stock_collectors[0].get_price_by_symbol("TSLA"))
			print(stock_collectors[1].get_price_by_symbol("AAPL"))

		# trade_executor = TradeExecutor("TSLA")
	finally:
		for coll in stock_collectors:
			coll.stop()
		for coll in stock_collectors:
			coll.join()
		logout()


if __name__ == "__main__":
	main()