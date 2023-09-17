from stock_info_collector import StockInfoCollector
from trade_executor import TradeExecutor


class TradeRealtimeManager(object):
	def __init__(self):
		self.monitored_stocks = self._get_monitored_stocks()
		self.stock_price_collector = StockInfoCollector(self.monitored_stocks)
		self.trade_executor = TradeExecutor()
		self.current_positions = self.trade_executor.get_stock_positions()
		self.current_cash = self.trade_executor.get_cash_position()
		self._start_children_threads()

	def __del__(self):
		self._end_children_threads()

	def _get_monitored_stocks(self):
		return ["TSLA", "C", "AAPL", "MSFT", "NVDA"]

	def _start_children_threads(self):
		self.stock_price_collector.start()

	def _end_children_threads(self):
		self.stock_price_collector.stop()

		self.stock_price_collector.join()

	