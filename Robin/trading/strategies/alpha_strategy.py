import pandas as pd

from trading.base_strategy import BaseStrategy, ActionMetadata, Action
from trading.stock_historical_collector import StockHistoricalCollector, HjkMetadata, BollingerMetadata, RSIMetadata
from trading.trading_agent import OrderMetadata, TradingAgent


MIN_PURCHASE_GAP = 3


class AlphaStrategy(BaseStrategy):
	def __init__(self, stock_info_collector: StockHistoricalCollector, trading_agent: TradingAgent):
		super().__init__(stock_info_collector, trading_agent)

	def action(self, symbol: str) -> ActionMetadata:
		should_buy = super().should_buy(symbol)
		should_sell = super().should_sell(symbol)
		action: Action = Action.HOLD
		if not should_buy and not should_sell:
			return ActionMetadata(action=action, amount=0)

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

		active_orders: list[OrderMetadata] = self._trade_agent.get_active_orders(symbol)

		if should_buy:
			uuids = list(df['uuid'])
			for active_order in active_orders:
				if active_order.uuid in uuids[-3:]:
					should_buy = False
					break
			golden_pit = list((df['term_line_8'] < 15) & (df['term_line_21'] < 15) & (df['term_line_55'] < 15))
			over_sold = list(df['rsi'] < 30)
			should_buy = should_buy and golden_pit[-1] and over_sold[-1]
			if should_buy:
				action = Action.BUY
				return ActionMetadata(action=action, amount=1)
		if should_sell:
			over_buy = list(df['rsi'] > 70)[-1]
			resistance_signals = list(df['close_price'])[-1] >= list(df['upper_band'])[-1]
			if resistance_signals or over_buy:
				action = Action.SELL
				return ActionMetadata(action=action, amount=0)

		return ActionMetadata(action=action, amount=0)
