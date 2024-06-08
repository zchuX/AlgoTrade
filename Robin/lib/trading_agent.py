import typing
from dataclasses import dataclass
from datetime import datetime

from lib.trade_executor import TradeExecutor, OrderDetails
from lib.stock_info_collector import StockInfoCollector
from util.util import get_datetime

DEFAULT_PORTIONS = 20


@dataclass
class OrderMetadata:
	stock: str
	time: datetime
	price: float
	share: float
	remain_portion: int


@dataclass
class TradeSnapshot:
	time: datetime
	daily_start_net_value: float
	current_net_value: float
	daily_pnl: float
	daily_pnl_percentage: float
	remain_portion: int
	positions: dict[str, float]
	cash_position: float
	active_orders: dict[str, list[OrderMetadata]]
	active_pnl: dict[str, float]
	active_pnl_percentage: dict[str, float]


class TradingAgent(object):
	def __init__(
		self,
		symbols: list[str],
		trade_snapshot: typing.Optional[TradeSnapshot],
	):
		self._symbols: list[str] = symbols
		self._executor: dict[str, TradeExecutor] = {symbol: TradeExecutor(symbol) for symbol in symbols}
		self._cur_position: dict[str, float] = {
			symbol: self._executor[symbol].get_stock_positions() for symbol in symbols
		}
		self._cash_position = TradeExecutor.get_cash_position()

		if trade_snapshot is None:
			net_value = TradeExecutor.get_net_worth()
			trade_snapshot = TradeSnapshot(
				time=get_datetime(),
				daily_start_net_value=net_value,
				current_net_value=net_value,
				daily_pnl=0,
				daily_pnl_percentage=0,
				remain_portion=DEFAULT_PORTIONS,
				positions=self._cur_position,
				cash_position=self._cash_position,
				active_orders={symbol: [] for symbol in symbols},
				active_pnl={symbol: 0 for symbol in symbols},
				active_pnl_percentage={symbol: 0 for symbol in symbols}
			)

		self._remain_portion = trade_snapshot.remain_portion
		self._portion_size: float = self._cash_position / trade_snapshot.remain_portion
		self._active_orders: dict[str, list[OrderMetadata]] = trade_snapshot.active_orders
		for symbol in symbols:
			if symbol not in self._active_orders:
				self._active_orders[symbol] = []

		self._start_trade_snapshot = trade_snapshot

	def clean_all_position(self, symbol):
		self._executor[symbol].sell_stock(self._executor[symbol].get_stock_positions())

	def clean_all_positions(self):
		for symbol in self._symbols:
			self.clean_all_position(symbol=symbol)

	def buy(self, symbol) -> OrderMetadata:
		order: OrderDetails = self._executor[symbol].buy_stock(self._portion_size)
		self._remain_portion -= 1
		self._cur_position[symbol] = self._executor[symbol].get_stock_positions()
		self._cash_position = TradeExecutor.get_cash_position()
		return OrderMetadata(
			stock=symbol,
			time=get_datetime(),
			price=order.price,
			share=order.share,
			remain_portion=self._remain_portion
		)

	def _get_pnl(self, symbol):
		cur_price = StockInfoCollector.get_current_price_by_symbol(symbol=symbol)
		if cur_price is None:
			raise Exception(f"Current price for {symbol} not available.")
		pnl = 0
		for order in self._active_orders[symbol]:
			pnl += order.share * (cur_price - order.price)
		return pnl

	def _get_pnl_percentage(self, symbol):
		cur_price = StockInfoCollector.get_current_price_by_symbol(symbol=symbol)
		if cur_price is None:
			raise Exception(f"Current price for {symbol} not available.")
		pnl = 0
		starting_price = 0
		for order in self._active_orders[symbol]:
			pnl += order.share * (cur_price - order.price)
			starting_price += order.share * order.price
		if starting_price > 0:
			return pnl / starting_price - 1
		else:
			return 0

	def snapshot(self) -> TradeSnapshot:
		start_net_value = self._start_trade_snapshot.daily_start_net_value
		net_value = TradeExecutor.get_net_worth()
		return TradeSnapshot(
			time=get_datetime(),
			daily_start_net_value=start_net_value,
			current_net_value=net_value,
			daily_pnl=net_value - start_net_value,
			daily_pnl_percentage=(net_value - start_net_value) / start_net_value,
			remain_portion=self._remain_portion,
			positions=self._cur_position,
			cash_position=self._cash_position,
			active_orders=self._active_orders,
			active_pnl={symbol: self._get_pnl(symbol) for symbol in self._symbols},
			active_pnl_percentage={symbol: self._get_pnl_percentage(symbol) for symbol in self._symbols}
		)
