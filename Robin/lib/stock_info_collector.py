import time

from threading import Thread
from typing import Optional

import robin_stocks.robinhood.stocks as robin_stocks
from util.util import log_info, log_error, login

"""
StockInfoCollector
@params:
symbols: Stock symbols
interval: price collection time interval
"""


class StockInfoCollector(Thread):
	def __init__(self, symbols, interval=5):
		super().__init__()
		log_info(f"Collecting stock prices for: {', '.join(symbols)}.")
		self._price_store = [[] for _ in symbols]
		self._symbols = symbols
		self._interval = interval
		self._running = True

	def _get_prices(self):
		prices = robin_stocks.get_latest_price(self._symbols, includeExtendedHours=True)
		for i in range(len(prices)):
			self._price_store[i].append(float(prices[i]))

	def run(self):
		while self._running:
			start_time = time.time()
			try:
				self._get_prices()
			except Exception as e:
				log_error(f"Error when updating stock prices: {e}.")
				try:
					login()
					log_info(f"Re-login to the account.")
				except Exception as login_error:
					log_error(f"Error when logging in: {login_error}.")
			time.sleep(max(0, int(self._interval - (time.time() - start_time))))

	def stop(self):
		self._running = False
		log_info(f"Stop collecting prices for {', '.join(self._symbols)}.")

	# Get the latest prices for a stock
	def get_price_by_symbol(self, symbol):
		if symbol not in self._symbols:
			return None
		idx = self._symbols.index(symbol)
		result, self._price_store[idx] = self._price_store[idx], []
		return result

	@staticmethod
	def get_current_price_by_symbol(symbol) -> Optional[float]:
		prices = robin_stocks.get_latest_price(symbol, includeExtendedHours=True)
		if prices:
			return float(robin_stocks.get_latest_price(symbol, includeExtendedHours=True)[0])
		return None
