import typing

from dataclasses import dataclass

import robin_stocks.robinhood as robin
from util.util import log_info

MIN_CASH_VALUE: float = 25000


@dataclass
class OrderDetails:
    order_id: str
    symbol: str
    instrument_id: str
    price: float
    position: float


@dataclass
class StkPosition:
    symbol: str
    position: float


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
                                    position=float(buy_result["quantity"]))
        log_info(f"buy_stock: {order_detail}")
        return order_detail

    def sell_stock(self, shares: float) -> OrderDetails:
        sell_result: dict = robin.orders.order_sell_fractional_by_quantity(self.symbol, shares)
        order_detail = OrderDetails(order_id=sell_result["id"],
                                    symbol=self.symbol,
                                    instrument_id=sell_result["instrument_id"],
                                    price=float(sell_result["price"]),
                                    position=-float(sell_result["quantity"]))
        log_info(f"sell_stock: {order_detail}")
        return order_detail

    def get_stock_positions(self) -> typing.Optional[StkPosition]:
        positions: typing.List[dict] = robin.account.get_open_stock_positions()
        for position in positions:
            instrument_id = position["instrument_id"]
            if self.instrument_id is None:
                cur_symbol = robin.stocks.get_symbol_by_url(position["instrument"])
                if cur_symbol == self.symbol:
                    self.instrument_id = instrument_id
            if instrument_id == self.instrument_id:
                return StkPosition(symbol=self.symbol, position=float(position["quantity"]))
        return None

    @staticmethod
    def get_cash_position():
        cash_val = float(robin.profiles.load_account_profile()["cash"])
        if cash_val > MIN_CASH_VALUE:
            return cash_val - MIN_CASH_VALUE
        raise Exception("Insufficient fund.")
