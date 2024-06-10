import pandas as pd
from dataclasses import dataclass
from enum import Enum

from trading.stock_historical_collector import StockHistoricalCollector
from trading.trading_agent import OrderMetadata, TradingAgent


class Action(Enum):
	HOLD = 0
	BUY = 1
	SELL = 2


@dataclass
class ActionMetadata:
	action: Action
	amount: int
	uuid: str


class BaseStrategy(object):
	def __init__(self, stock_info_collector: StockHistoricalCollector, trading_agent: TradingAgent):
		self._stock_info_collector: StockHistoricalCollector = stock_info_collector
		self._trade_agent: TradingAgent = trading_agent

	"""
	Avoid duplicate purchase here
	"""
	def should_buy(self, symbol: str) -> bool:
		stock_historical_data: pd.DataFrame = self._stock_info_collector.get_historical_info_by_symbol(symbol=symbol)
		active_orders: list[OrderMetadata] = self._trade_agent.get_active_orders(symbol)
		if len(stock_historical_data) == 0:
			return False

		for active_order in active_orders:
			if active_order.uuid == stock_historical_data['uuid'][-1]:
				return False

		return True

	"""
	Avoid selling without active order
	"""
	def should_sell(self, symbol: str) -> bool:
		stock_historical_data: pd.DataFrame = self._stock_info_collector.get_historical_info_by_symbol(symbol=symbol)
		active_orders: list[OrderMetadata] = self._trade_agent.get_active_orders(symbol)
		return len(stock_historical_data) > 0 or len(active_orders) > 0
