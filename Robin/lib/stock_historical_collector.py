from dataclasses import dataclass
from collections import defaultdict
from threading import Thread

import time
from typing import Optional

import pandas as pd
import robin_stocks.robinhood.stocks as robin_stocks

from util.util import log_info, log_error, login


@dataclass
class HjkMetadata:
	interval: int
	smooth_parameters: list[int]
	std_interval: int
	std_multiplier: int


class StockHistoricalCollector(Thread):
	def __init__(self, symbols):
		super().__init__()
		log_info(f"Collecting stock historical information for: {', '.join(symbols)}.")
		self._symbols = symbols
		self._interval = 'hour'
		self._sleep_interval = 3600
		self._stock_info: dict[str, pd.DataFrame] = self._collect_stock_info('month')
		self._running = True

	"""
	Interval: Interval to retrieve data for. Values are '5minute', '10minute', 'hour', 'day', 'week'.
	Span: 'day', 'week', 'month', '3month', 'year', or '5year'. 
	"""

	def _collect_stock_info(self, span: str) -> dict[str, pd.DataFrame]:
		historical_info = robin_stocks.get_stock_historicals(
			self._symbols,
			interval=self._interval,
			span=span
		)

		stock_info_dict = defaultdict(list)

		for info in historical_info:
			stock_info_dict[info['symbol']].append(info)

		stock_info_dataframes = {symbol: pd.DataFrame(stock_info_dict[symbol]) for symbol in stock_info_dict}

		for symbol in stock_info_dataframes:
			stock_info_dataframes[symbol]['begins_at'] = pd.to_datetime(stock_info_dataframes[symbol]['begins_at'])
			stock_info_dataframes[symbol].set_index('begins_at', inplace=True)
			stock_info_dataframes[symbol]['close_price'] = stock_info_dataframes[symbol]['close_price'].astype(float)
			stock_info_dataframes[symbol]['low_price'] = stock_info_dataframes[symbol]['low_price'].astype(float)
			stock_info_dataframes[symbol]['high_price'] = stock_info_dataframes[symbol]['high_price'].astype(float)
		return stock_info_dataframes

	def stop(self):
		self._running = False
		log_info(f"Stop collecting historical info for {', '.join(self._symbols)}.")

	def run(self):
		while self._running:
			try:
				self._stock_info = self._collect_stock_info('month')
			except Exception as e:
				log_error(f"Error when updating historical info: {e}.")
				try:
					login()
					log_info(f"Re-login to the account.")
				except Exception as login_error:
					log_error(f"Error when logging in: {login_error}.")
			time.sleep(self._sleep_interval)

	def get_historical_info_by_symbol(self, symbol: str, metadata_list: list[HjkMetadata]) -> Optional[pd.DataFrame]:
		if symbol in self._stock_info:
			df = self._stock_info[symbol]
			for metadata in metadata_list:
				interval = metadata.interval
				rsv_key = f'rsv_{interval}'
				term_key = f'term_line_{interval}'
				df[rsv_key] = (df['close_price'] - df['low_price'].rolling(window=interval).min()) / (
					df['high_price'].rolling(window=interval).max() - df['low_price'].rolling(window=interval).min()
				) * 100
				df[term_key] = df[rsv_key]
				for smooth_parameters in metadata.smooth_parameters:
					df[term_key] = df[term_key].rolling(window=smooth_parameters).mean()
				if metadata.std_multiplier > 0:
					df[term_key] = df[term_key] + df['close_price'].rolling(
						window=metadata.std_interval).std() * metadata.std_multiplier
			return df
		return None