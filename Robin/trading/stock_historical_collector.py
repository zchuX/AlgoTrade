import datetime
import time
import uuid
import pandas as pd
import ta

from typing import Optional, List, Dict
from dataclasses import dataclass
from collections import defaultdict
from threading import Thread
from robin_stocks.robinhood import stocks as robin_stocks

from util.util import log_info, log_error, login


@dataclass
class HjkMetadata:
	interval: int
	smooth_parameters: List[int]
	std_interval: int
	std_multiplier: int


@dataclass
class BollingerMetadata:
	window: int
	no_of_std: float


@dataclass
class RSIMetadata:
	window_size: int


class StockHistoricalCollector(Thread):
	def __init__(self, symbols):
		super().__init__()
		log_info(f"[StockHistoricalCollector] Collecting stock historical information for: {', '.join(symbols)}.")
		self._symbols = symbols
		self._interval = '5minute'
		self._period = 'day'
		self._sleep_interval = 60
		self._stock_info: Dict[str, pd.DataFrame] = dict()
		self._collect_stock_info(self._period)
		self._running = True

	"""
	Interval: Interval to retrieve data for. Values are '5minute', '10minute', 'hour', 'day', 'week'.
	Span: 'day', 'week', 'month', '3month', 'year', or '5year'. 
	"""

	def _collect_stock_info(self, span: str) -> Dict[str, pd.DataFrame]:
		additional_historical_info = robin_stocks.get_stock_historicals(
			self._symbols,
			interval=self._interval,
			span="week",
			bounds="regular"
		)

		historical_info = robin_stocks.get_stock_historicals(
			self._symbols,
			interval=self._interval,
			span=span,
			bounds="extended"
		)

		stock_info_dict = defaultdict(list)
		for info in historical_info:
			stock_info_dict[info['symbol']].append(info)

		stock_info_dataframes = {symbol: pd.DataFrame(stock_info_dict[symbol]) for symbol in stock_info_dict}

		stock_info_dict = defaultdict(list)
		for info in additional_historical_info:
			stock_info_dict[info['symbol']].append(info)

		additional_historical_info_df = {symbol: pd.DataFrame(stock_info_dict[symbol]) for symbol in stock_info_dict}

		for symbol in stock_info_dataframes:
			latest_df = stock_info_dataframes[symbol]
			latest_df['begins_at'] = pd.to_datetime(latest_df['begins_at'])
			df = additional_historical_info_df[symbol]
			df['begins_at'] = pd.to_datetime(df['begins_at'])
			df_2 = df.loc[df.begins_at < latest_df.begins_at[0]]
			df_3 = df_2.loc[df_2.begins_at > (latest_df.begins_at[0] - datetime.timedelta(days=3))]
			stock_info_dataframes[symbol] = pd.concat([df_3, latest_df], ignore_index=True)

		for symbol in stock_info_dataframes:
			updated_df = stock_info_dataframes[symbol]
			updated_df['begins_at'] = pd.to_datetime(updated_df['begins_at'])
			updated_df['open_price'] = updated_df['open_price'].astype(float)
			updated_df['close_price'] = updated_df['close_price'].astype(float)
			updated_df['low_price'] = updated_df['low_price'].astype(float)
			updated_df['high_price'] = updated_df['high_price'].astype(float)
			updated_df['uuid'] = [str(uuid.uuid4()) for _ in range(len(updated_df))]
			if symbol not in self._stock_info:
				self._stock_info[symbol] = updated_df
			else:
				updated_df = updated_df[updated_df['begins_at'] > list(self._stock_info[symbol]['begins_at'])[-1]]
				if len(updated_df) > 0:
					log_info(
						f"[StockHistoricalCollector] "
						f"Appending updated historical info for stock {symbol}: {updated_df}..."
					)
					self._stock_info[symbol] = pd.concat([self._stock_info[symbol], updated_df], ignore_index=True)

		return stock_info_dataframes

	def stop(self):
		self._running = False
		log_info(f"[StockHistoricalCollector] Stop collecting historical info for {', '.join(self._symbols)}.")

	def run(self):
		while self._running:
			try:
				self._collect_stock_info(self._period)
			except Exception as e:
				log_error(f"[StockHistoricalCollector] Error when updating historical info.", e)
				try:
					login()
					log_info(f"[StockHistoricalCollector] Re-login to the account.")
				except Exception as login_error:
					log_error(f"[StockHistoricalCollector] Error when logging in.", login_error)
			time.sleep(self._sleep_interval)

	def get_historical_info_by_symbol(
		self,
		symbol: str,
		metadata_list: Optional[List[HjkMetadata]] = None,
		bollinger: Optional[BollingerMetadata] = None,
		rsi_metadata: Optional[RSIMetadata] = None
	) -> Optional[pd.DataFrame]:
		if symbol in self._stock_info:
			df = self._stock_info[symbol]

			if metadata_list is None:
				metadata_list = []

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
			if bollinger is not None:
				df['SMA'] = df['close_price'].rolling(bollinger.window).mean()
				df['STD'] = df['close_price'].rolling(bollinger.window).std()
				df['upper_band'] = df['SMA'] + bollinger.no_of_std * df['STD']
				df['lower_band'] = df['SMA'] - bollinger.no_of_std * df['STD']

			if rsi_metadata is not None:
				# Calculate RSI
				df['rsi'] = ta.momentum.RSIIndicator(df['close_price'], window=rsi_metadata.window_size).rsi()
			return df
		return None
