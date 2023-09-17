import typing
import time
from threading import Thread

from trade_executor import TradeExecutor
from stock_info_collector import StockInfoCollector
from util import *


class TradingAgent(Thread):
    def __init__(self, symbol: str, cash: float, stock_info_collector: StockInfoCollector):
        self.symbol: str = symbol
        self.cash: float = cash
        self.stock_info_collector = stock_info_collector
        self.executor = TradeExecutor(symbol)
        self.cur_position: float = self.executor.get_stock_positions([symbol]).position

        while not self.get_latest_prices():
            time.sleep(1)

        self.prices = self.get_latest_prices()
        self.initial_val = self.prices[0] * self.cur_position + self.cash
        self.halting = False
        self.running = True

    def get_latest_prices(self) -> typing.List[float]:
        return self.stock_info_collector.get_price_by_symbol(self.symbol)

    def clear_all_positions(self):
        self.executor.sell_stock(self.symbol, self.cur_position)

    def stop(self):
        self.running = False

    def set_halting_state(self, halting):
        self.halting = halting

    def run(self):
        log_info(f"Starting TradingAgent for {self.symbol}...")
        while self.running:
            while self.halting:
                time.sleep(1)
            try:
                pass
            except Exception as e:
                log_error(f"Error when running TradingAgent: {e}")
            time.sleep(10)
