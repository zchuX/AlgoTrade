import typing
from dataclasses import dataclass
from datetime import datetime, timedelta
from time import sleep

from trading.trade_executor import TradeExecutor, OrderDetails, MIN_CASH_VALUE
from trading.stock_info_collector import StockInfoCollector
from util.util import get_datetime, log_info

TIMEOUT = 25

DEFAULT_PORTION_SIZE = 300


@dataclass
class OrderMetadata:
	uuid: str
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
		test_mode: bool = False
	):
		self._symbols: list[str] = symbols
		self._executor: dict[str, TradeExecutor] = {symbol: TradeExecutor(symbol) for symbol in symbols}
		self._cur_position: dict[str, float] = {
			symbol: self._executor[symbol].get_stock_positions() for symbol in symbols
		}
		self._cash_position: float = TradeExecutor.get_cash_position()
		self._remain_portion: int = int(self._cash_position) // DEFAULT_PORTION_SIZE

		if trade_snapshot is None or get_datetime() - timedelta(hours=6, minutes=30) > trade_snapshot.time:
			net_value = TradeExecutor.get_net_worth()
			positions: typing.List[dict] = TradeExecutor.get_all_stock_positions()
			active_orders = {symbol: [] for symbol in symbols}
			for position in positions:
				symbol = TradeExecutor.get_symbol(position["instrument"])
				active_orders[symbol].append(
					OrderMetadata(
						uuid="00000000-0000-0000-0000-0000000000",
						stock=symbol,
						time=get_datetime(),
						price=float(position["average_buy_price"]),
						share=float(position["quantity"]),
						remain_portion=-1,
				))
			trade_snapshot = TradeSnapshot(
				time=get_datetime(),
				daily_start_net_value=net_value,
				current_net_value=net_value,
				daily_pnl=0,
				daily_pnl_percentage=0,
				remain_portion=self._remain_portion,
				positions=self._cur_position,
				cash_position=self._cash_position,
				active_orders=active_orders,
				active_pnl={symbol: 0 for symbol in symbols},
				active_pnl_percentage={symbol: 0 for symbol in symbols}
			)

		if test_mode:
			self._cur_position = {symbol: 0 for symbol in symbols}
			self._cash_position = trade_snapshot.cash_position
			for symbol in symbols:
				for active_order in trade_snapshot.active_orders[symbol]:
					self._cur_position[symbol] += active_order.share

		self._portion_size: float = DEFAULT_PORTION_SIZE
		self._active_orders: dict[str, list[OrderMetadata]] = trade_snapshot.active_orders
		for symbol in symbols:
			if symbol not in self._active_orders:
				self._active_orders[symbol] = []

		self._start_trade_snapshot = trade_snapshot

	def clean_all_position(self, symbol, uuid: str):
		order: OrderDetails = self._executor[symbol].sell_stock(self._executor[symbol].get_stock_positions())
		self._remain_portion += len(self._active_orders[symbol])
		self._cur_position[symbol] = 0
		self._cash_position = TradeExecutor.get_cash_position()
		self._active_orders[symbol] = []
		sell_order = OrderMetadata(
			uuid=uuid,
			stock=symbol,
			time=get_datetime(),
			price=order.price,
			share=order.share,
			remain_portion=self._remain_portion
		)
		log_info(f"Completed order: {sell_order}")
		return sell_order

	def test_clean_all_position(self, symbol: str, uuid: str, price: float, time: datetime) -> OrderMetadata:
		self._remain_portion += len(self._active_orders[symbol])
		shares = self._cur_position[symbol]
		self._cur_position[symbol] = 0
		self._cash_position += price * shares
		self._active_orders[symbol] = []
		sell_order = OrderMetadata(
			uuid=uuid,
			stock=symbol,
			time=time,
			price=price,
			share=-shares,
			remain_portion=self._remain_portion
		)
		log_info(f"Completed order: {sell_order}")
		return sell_order

	def buy(self, symbol: str, uuid: str) -> OrderMetadata:
		self._cash_position: float = TradeExecutor.get_cash_position()
		self._remain_portion: int = int(self._cash_position) // DEFAULT_PORTION_SIZE
		if self._remain_portion <= 0:
			raise Exception(f"Insufficient fund buying: {symbol}")
		order: OrderDetails = self._executor[symbol].buy_stock(self._portion_size)
		self._remain_portion -= 1
		cur_position = self._cur_position[symbol]
		time_out = 0
		while self._executor[symbol].get_stock_positions() <= cur_position and time_out < TIMEOUT:
			sleep(0.2)
			time_out += 1
		self._cur_position[symbol] = self._executor[symbol].get_stock_positions()
		self._cash_position = TradeExecutor.get_cash_position()
		if self._cur_position[symbol] <= cur_position:
			self._remain_portion += 1
			log_info(f"Order with {symbol} did not go through: {order}!!")
		order_metadata = OrderMetadata(
			uuid=uuid,
			stock=symbol,
			time=get_datetime(),
			price=order.price,
			share=self._executor[symbol].get_stock_positions() - cur_position,
			remain_portion=self._remain_portion
		)
		self._active_orders[symbol].append(order_metadata)
		log_info(f"Completed order: {order_metadata}")
		return order_metadata

	def test_buy(self, symbol: str, uuid: str, price: float, time: datetime) -> OrderMetadata:
		self._remain_portion -= 1
		share = self._portion_size / price
		self._cur_position[symbol] += share
		self._cash_position -= self._portion_size
		order_metadata = OrderMetadata(
			uuid=uuid,
			stock=symbol,
			time=time,
			price=price,
			share=self._portion_size / price,
			remain_portion=self._remain_portion
		)
		self._active_orders[symbol].append(order_metadata)
		log_info(f"Completed order: {order_metadata}")
		return order_metadata

	def _get_pnl(self, symbol, cur_price: typing.Optional[float] = None):
		if cur_price is None:
			cur_price = StockInfoCollector.get_current_price_by_symbol(symbol=symbol)
		if cur_price is None:
			raise Exception(f"Current price for {symbol} not available.")
		pnl = 0
		for order in self._active_orders[symbol]:
			pnl += order.share * (cur_price - order.price)
		return pnl

	def _get_pnl_percentage(self, symbol, cur_price: typing.Optional[float] = None):
		if cur_price is None:
			cur_price = StockInfoCollector.get_current_price_by_symbol(symbol=symbol)
		if cur_price is None:
			raise Exception(f"Current price for {symbol} not available.")
		pnl = 0
		starting_price = 0
		for order in self._active_orders[symbol]:
			pnl += order.share * (cur_price - order.price)
			starting_price += order.share * order.price
		if starting_price > 0:
			return pnl / starting_price * 100
		else:
			return 0

	def get_active_orders(self, symbol):
		return self._active_orders[symbol]

	def get_position(self, symbol):
		return self._cur_position[symbol]

	def snapshot(self) -> TradeSnapshot:
		start_net_value = self._start_trade_snapshot.current_net_value
		if get_datetime() - timedelta(hours=6, minutes=30) < self._start_trade_snapshot.time:
			start_net_value = self._start_trade_snapshot.daily_start_net_value
		net_value = TradeExecutor.get_net_worth()
		return TradeSnapshot(
			time=get_datetime(),
			daily_start_net_value=start_net_value,
			current_net_value=net_value,
			daily_pnl=net_value - start_net_value,
			daily_pnl_percentage=round((net_value - start_net_value) / (start_net_value - MIN_CASH_VALUE) * 100, 2),
			remain_portion=self._remain_portion,
			positions=self._cur_position,
			cash_position=self._cash_position,
			active_orders=self._active_orders,
			active_pnl={symbol: round(self._get_pnl(symbol), 2) for symbol in self._symbols},
			active_pnl_percentage={symbol: round(self._get_pnl_percentage(symbol), 2) for symbol in self._symbols}
		)

	def test_snapshot(self, prices: dict[str, float], time: datetime) -> TradeSnapshot:
		start_net_value = self._start_trade_snapshot.current_net_value
		if time - timedelta(hours=6, minutes=30) < self._start_trade_snapshot.time:
			start_net_value = self._start_trade_snapshot.daily_start_net_value
		net_value = MIN_CASH_VALUE + self._cash_position + sum([
			self._cur_position[symbol] * prices[symbol] for symbol in self._cur_position])
		return TradeSnapshot(
			time=time,
			daily_start_net_value=start_net_value,
			current_net_value=net_value,
			daily_pnl=net_value - start_net_value,
			daily_pnl_percentage=round((net_value - start_net_value) / (start_net_value - MIN_CASH_VALUE) * 100, 2),
			remain_portion=self._remain_portion,
			positions=self._cur_position,
			cash_position=self._cash_position,
			active_orders=self._active_orders,
			active_pnl={symbol: round(self._get_pnl(symbol, prices[symbol]), 2) for symbol in self._symbols},
			active_pnl_percentage={
				symbol: round(self._get_pnl_percentage(symbol, prices[symbol]), 2) for symbol in self._symbols
			}
		)
