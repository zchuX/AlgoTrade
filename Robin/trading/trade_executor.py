import typing

from dataclasses import dataclass
from time import sleep

import robin_stocks.robinhood as robin

from trading.stock_info_collector import StockInfoCollector
from util.util import log_info

MIN_CASH_VALUE: float = 0

TIME_OUT = 30


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

    def limit_buy_stock(self, amount: float) -> OrderDetails:
        market_price = StockInfoCollector.get_current_price_by_symbol(self.symbol)
        price = market_price + min(0.05, market_price * 0.001)
        quantity = max(1, int(amount / price))
        log_info(f"limit buy stock: {self.symbol} with market price: {market_price} "
                 f"with limit price: {price}, quantity: {quantity}")
        buy_result: dict = robin.orders.order(
            symbol=self.symbol,
            quantity=quantity,
            side="buy",
            limitPrice=price,
            extendedHours=True,
            market_hours="extended_hours"
        )
        order_id = "unknown_id"
        if "id" in buy_result:
            order_id = buy_result["id"]

        instrument_id = "unknown_id"
        if "instrument_id" in buy_result:
            instrument_id = buy_result["instrument_id"]

        order_detail = OrderDetails(order_id=order_id,
                                    symbol=self.symbol,
                                    instrument_id=instrument_id,
                                    price=price,
                                    share=quantity)
        log_info(f"limit_buy_stock: {order_detail}")
        return order_detail

    def limit_sell_stock(self, quantity: float) -> OrderDetails:
        pre_positions = self.get_stock_positions()
        market_price = StockInfoCollector.get_current_price_by_symbol(self.symbol)
        price = market_price - min(0.05, market_price * 0.001)
        quantity = int(quantity)
        current_cash = TradeExecutor.get_total_cash_position()
        log_info(f"limit sell stock: {self.symbol} with market price: {market_price} "
                 f"with limit price: {price}, quantity: {quantity}")
        sell_result: dict = robin.orders.order(
            symbol=self.symbol,
            quantity=quantity,
            side="sell",
            limitPrice=price,
            extendedHours=True,
            market_hours="extended_hours")

        time_out = 0
        while TradeExecutor.get_total_cash_position() - current_cash <= price * quantity * 0.95 and time_out < TIME_OUT:
            time_out += 1
            sleep(1)
        share = pre_positions - self.get_stock_positions()
        if share < quantity:
            log_info(f"Out of {quantity} shares of stocks to be sold, only {share} shares were sold. Cancel the order.")
            robin.orders.cancel_stock_order(sell_result["id"])

        order_id = "unknown_id"
        instrument_id = "unknown_instrument_id"
        if "id" in sell_result:
            order_id = sell_result["id"]

        if "instrument_id" in sell_result:
            instrument_id = sell_result["instrument_id"]
        order_detail = OrderDetails(order_id=order_id,
                                    symbol=self.symbol,
                                    instrument_id=instrument_id,
                                    price=price,
                                    share=share)
        log_info(f"limit_sell_stock: {order_detail}")
        return order_detail

    def sell_stock(self, shares: float) -> OrderDetails:
        shares = round(shares, 2)
        if shares == 0:
            raise Exception("Attempting to sell 0 share of stocks...")
        current_cash = TradeExecutor.get_total_cash_position()
        price = StockInfoCollector.get_current_price_by_symbol(self.symbol)
        sell_result: dict = robin.orders.order_sell_fractional_by_quantity(self.symbol, shares)
        log_info(f"sell_result: {sell_result}")
        time_out = 0
        while TradeExecutor.get_total_cash_position() - current_cash <= price * shares * 0.8 and time_out < TIME_OUT:
            time_out += 1
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

    def get_avg_buy_price(self) -> float:
        positions: typing.List[dict] = robin.account.get_open_stock_positions()
        for position in positions:
            instrument_id = position["instrument_id"]
            if self.instrument_id is None:
                cur_symbol = robin.stocks.get_symbol_by_url(position["instrument"])
                if cur_symbol == self.symbol:
                    self.instrument_id = instrument_id
            if instrument_id == self.instrument_id:
                return float(position["average_buy_price"])
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