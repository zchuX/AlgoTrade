import typing

from dataclasses import dataclass
from time import sleep

import robin_stocks.robinhood as robin

from trading.stock_info_collector import StockInfoCollector
from util.util import log_info

MIN_CASH_VALUE: float = 0


@dataclass
class OrderDetails:
    order_id: str
    symbol: str
    instrument_id: str
    price: float
    share: float


class TradeExecutor(object):
    def __init__(self, symbol: str):
        self.instrument_id = None
        self.symbol = symbol

    def buy_stock(self, amount: float) -> OrderDetails:
        buy_result: dict = robin.orders.order_buy_fractional_by_price(self.symbol, amount)
        order_detail = OrderDetails(order_id=buy_result["id"],
                                    symbol=self.symbol,
                                    instrument_id=buy_result["instrument_id"],
                                    price=float(buy_result["price"]),
                                    share=float(buy_result["quantity"]))
        log_info(f"buy_stock: {order_detail}")
        return order_detail

    def sell_stock(self, shares: float) -> OrderDetails:
        current_cash = TradeExecutor.get_total_cash_position()
        price = StockInfoCollector.get_current_price_by_symbol(self.symbol)
        sell_result: dict = robin.orders.order_sell_fractional_by_quantity(self.symbol, shares)
        while TradeExecutor.get_total_cash_position() - current_cash <= price * shares * 0.8:
            sleep(0.2)
        price = (TradeExecutor.get_total_cash_position() - current_cash) / shares
        order_detail = OrderDetails(order_id=sell_result["id"],
                                    symbol=self.symbol,
                                    instrument_id=sell_result["instrument_id"],
                                    price=price,
                                    share=-shares)
        log_info(f"sell_stock: {order_detail}")
        return order_detail

    def get_stock_positions(self) -> float:
        positions: typing.List[dict] = robin.account.get_open_stock_positions()
        for position in positions:
            instrument_id = position["instrument_id"]
            if self.instrument_id is None:
                cur_symbol = robin.stocks.get_symbol_by_url(position["instrument"])
                if cur_symbol == self.symbol:
                    self.instrument_id = instrument_id
            if instrument_id == self.instrument_id:
                return float(position["quantity"])
        return 0

    @staticmethod
    def get_cash_position() -> float:
        account_profile = robin.profiles.load_account_profile()
        # cash_val = float(account_profile["portfolio_cash"])
        cash_val = float(account_profile['buying_power'])
        return max(cash_val - MIN_CASH_VALUE, 0)

    @staticmethod
    def get_total_cash_position() -> float:
        account_profile = robin.profiles.load_account_profile()
        cash_val = float(account_profile["portfolio_cash"])
        return max(cash_val - MIN_CASH_VALUE, 0)

    @staticmethod
    def get_net_worth() -> float:
        net_worth = float(robin.profiles.load_portfolio_profile()["equity"])
        return net_worth

    @staticmethod
    def get_all_stock_positions() -> typing.List[dict]:
        return robin.account.get_open_stock_positions()

    @staticmethod
    def get_symbol(instrument_id: str) -> str:
        return robin.stocks.get_symbol_by_url(instrument_id)