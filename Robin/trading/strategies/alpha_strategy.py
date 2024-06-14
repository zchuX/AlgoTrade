from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, List

import pandas as pd
import numpy as np

from trading.base_strategy import BaseStrategy, ActionMetadata, Action
from trading.stock_historical_collector import StockHistoricalCollector, HjkMetadata, BollingerMetadata, RSIMetadata
from trading.trading_agent import OrderMetadata, TradingAgent
from util.util import log_info

MIN_PURCHASE_GAP = 3


@dataclass
class MainForceResult:
	main_force_entry: List[bool]
	main_force_pulling_up: List[bool]


class AlphaStrategy(BaseStrategy):
	def __init__(self, stock_info_collector: StockHistoricalCollector, trading_agent: TradingAgent):
		super().__init__(stock_info_collector, trading_agent)

	@staticmethod
	def main_force_data(df: pd.DataFrame) -> MainForceResult:
		close_prices = df['close_price'].values
		open_prices = df['open_price'].values
		low_prices = df['low_price'].values
		high_prices = df['high_price'].values

		# Define calculation functions
		def sma(values: np.array, window):
			return np.array(pd.Series(values).rolling(window).mean())

		def ema(values, window):
			return np.array(pd.Series(values).ewm(span=window, adjust=False).mean())

		def llv(values, window):
			return np.array(pd.Series(values).rolling(window).min())

		def hhv(values, window):
			return np.array(pd.Series(values).rolling(window).max())

		def ref(values, period):
			return np.roll(values, period)

		# Perform calculations
		var1 = ref((low_prices + open_prices + close_prices + high_prices) / 4, 1)
		with np.errstate(divide='ignore'):
			var2 = sma(np.abs(low_prices - var1), 13) / sma(np.maximum(low_prices - var1, 0), 10)
		var3 = ema(var2, 10)
		var4 = llv(low_prices, 33)
		var5 = ema(np.where(low_prices <= var4, var3, 0), 3)
		with np.errstate(divide='ignore'):
			var21 = sma(np.abs(high_prices - var1), 13) / sma(np.minimum(high_prices - var1, 0), 10)
		var31 = ema(var21, 10)
		var41 = hhv(high_prices, 33)
		var51 = ema(np.where(high_prices >= var41, var31, 0), 3)

		main_force_entry = list(var5 > ref(var5, 1))

		main_force_pulling_up = list(var51 < ref(var51, 1))
		return MainForceResult(main_force_entry=main_force_entry, main_force_pulling_up=main_force_pulling_up)

	def action(self, symbol: str, test_datetime: Optional[datetime] = None) -> ActionMetadata:
		should_buy = super().should_buy(symbol)
		should_sell = super().should_sell(symbol)
		action: Action = Action.HOLD
		if not should_buy and not should_sell:
			return ActionMetadata(action=action, amount=0, uuid="")

		df: pd.DataFrame = self._stock_info_collector.get_historical_info_by_symbol(
			symbol=symbol,
			metadata_list=[
				HjkMetadata(interval=8, smooth_parameters=[3, 3], std_interval=21, std_multiplier=3),
				HjkMetadata(interval=21, smooth_parameters=[5], std_interval=37, std_multiplier=2),
				HjkMetadata(interval=55, smooth_parameters=[5], std_interval=0, std_multiplier=0)
			],
			bollinger=BollingerMetadata(window=20, no_of_std=2),
			rsi_metadata=RSIMetadata(window_size=14)
		)

		if test_datetime:
			df = df.loc[df["begins_at"] < test_datetime - timedelta(minutes=5)]

		active_orders: list[OrderMetadata] = self._trade_agent.get_active_orders(symbol)
		main_force_data: MainForceResult = AlphaStrategy.main_force_data(df)
		uuids = list(df['uuid'])
		uuid = uuids[-1]

		if should_buy:
			"""
			Buy stock only when all of the following conditions are met
			1. We did not buy any stock in the last 3 periods
			2. golden_pit is meet
			3. RSI < 30
			"""
			for active_order in active_orders:
				if active_order.uuid in uuids[-3:]:
					should_buy = False
					break
			golden_pit = list((df['term_line_8'] < 15) & (df['term_line_21'] < 15) & (df['term_line_55'] < 15))[-1]
			over_sold = list(df['rsi'] < 30)[-1]
			if should_buy and golden_pit and over_sold:
				log_info(
					f"Buying stock {symbol} with --- "
					f"term_line_8: {list(df['term_line_8'])[-1]}, "
					f"term_line_21: {list(df['term_line_21'])[-1]}, "
					f"term_line_55: {list(df['term_line_55'])[-1]}, "
					f"rsi: {list(df['rsi'])[-1]}, "
					f"main_force_entry: {main_force_data.main_force_entry[-1]}"
				)
				action = Action.BUY
				return ActionMetadata(action=action, amount=1, uuid=uuid)

		if should_sell:
			"""
			Sell stock only when any of the following condition is met
			1. RSI > 70
			2. resistance_signal is observed (bollinger)
			3. Earn 25% original price
			4. Loss from the high_price exceeds 5%
			"""
			over_buy = list(df['rsi'] > 70)[-1]
			max_buy_price = max([active_order.price for active_order in active_orders])
			resistance_signals = [df['close_price'][i] >= df['upper_band'][i] for i in range(len(df))]
			main_force_pulling_up = main_force_data.main_force_pulling_up
			has_resistance_signal = False
			if not main_force_pulling_up[-1]:
				i = 2
				while main_force_pulling_up[-i] and i <= len(main_force_pulling_up):
					if resistance_signals[-i]:
						has_resistance_signal = True
					i += 1
			sell_price_valid = list(df['upper_band'])[-1] >= max_buy_price
			take_benefit = list(df['close_price'])[-1] >= max_buy_price * 1.25
			take_loss = list(df['close_price'])[-1] <= 0.95 * max(list(df['high_price'])[list(df['uuid']).index(uuid):])
			if (has_resistance_signal and sell_price_valid) or over_buy or take_benefit or take_loss:
				log_info(
					f"Selling stock {symbol} with --- "
					f"over_buy: {over_buy}, "
					f"resistance_signals: {has_resistance_signal}, "
					f"sell_price_valid: {sell_price_valid}, "
					f"take_benefit: {take_benefit}, "
					f"take_loss: {take_loss}"
				)
				action = Action.SELL
				return ActionMetadata(action=action, amount=0, uuid=uuid)

		return ActionMetadata(action=action, amount=0, uuid="")
