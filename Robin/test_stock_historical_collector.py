from time import sleep

from trading.stock_historical_collector import StockHistoricalCollector, HjkMetadata, BollingerMetadata, RSIMetadata
from util.util import *

from matplotlib import pyplot as plt
import numpy as np
import pandas as pd

TEST_MODE = True
TEST_STOCKS = []


def intraday_collecting():
	with open(f"{PACKAGE_ROOT}/Config/stock_list.txt") as f:
		stocks = f.read().replace('\n', '').split(",")
	if TEST_MODE and len(TEST_STOCKS) > 0:
		stocks = TEST_STOCKS
	login()
	while not TEST_MODE and is_pre_hour():
		sleep(5)
	log_info("Start collecting....")
	worker = StockHistoricalCollector(stocks)
	worker.start()
	sleep(5)
	try:
		while TEST_MODE or is_trading_hour():
			for stock in stocks:
				try:
					df = worker.get_historical_info_by_symbol(
						stock,
						metadata_list=[
							HjkMetadata(interval=8, smooth_parameters=[3, 3], std_interval=21, std_multiplier=3),
							HjkMetadata(interval=21, smooth_parameters=[5], std_interval=37, std_multiplier=2),
							HjkMetadata(interval=55, smooth_parameters=[5], std_interval=0, std_multiplier=0)
						],
						bollinger=BollingerMetadata(window=20, no_of_std=2),
						rsi_metadata=RSIMetadata(window_size=14)
					)
					# Plotting the lines
					plt.figure(figsize=(12, 6))
					plt.plot(range(len(df)), df['close_price'], label='Close Price')

					start_idx = 0
					end_idx = 0
					for i in range(len(df['begins_at'])):
						if df['begins_at'][i] \
							>= datetime(2024, 6, 10, 6, 30, 0, tzinfo=pytz.timezone('US/Eastern')) and start_idx == 0:
							start_idx = i
						elif df['begins_at'][i] \
							>= datetime(2024, 6, 10, 16, 00, 0, tzinfo=pytz.timezone('US/Eastern')) and end_idx == 0:
							end_idx = i
					plt.axvspan(start_idx, start_idx + 1, color='black', alpha=0.3)
					plt.axvspan(end_idx, end_idx + 1, color='black', alpha=0.3)

					# Golden Pit indicator
					golden_pit = list((df['term_line_8'] < 15) & (df['term_line_21'] < 15) & (df['term_line_55'] < 15))
					for i in range(len(golden_pit)):
						if golden_pit[i]:
							plt.axvspan(i, i + 1, color='yellow', alpha=0.3)

					resistance_signals = []
					for i in range(len(df)):
						if df['close_price'][i] >= df['upper_band'][i]:
							resistance_signals.append((range(len(df))[i], df['close_price'][i]))
					plt.plot(range(len(df)), df['upper_band'], label='Upper Band', linestyle='--', color='red')
					plt.plot(range(len(df)), df['SMA'], label='Middle Band (SMA)', linestyle='--', color='blue')
					plt.plot(range(len(df)), df['lower_band'], label='Lower Band', linestyle='--', color='green')
					plt.scatter(
						[signal[0] for signal in resistance_signals],
						[signal[1] for signal in resistance_signals],
						color='red',
						label='Resistance Signal',
						marker='o')

					# Define overbought and oversold levels
					over_bought = list(df['rsi'] > 70)
					over_sold = list(df['rsi'] < 30)

					# plt.axvspan(0, 0, color='red', alpha=0.3, label='over_bought')
					plt.axvspan(0, 0, color='green', alpha=0.3, label='over_sold')
					for i in range(len(df)):
					# 	if over_bought[i]:
					# 		plt.axvspan(i, i + 1, color='red', alpha=0.3)
						if over_sold[i]:
							plt.axvspan(i, i + 1, color='green', alpha=0.3)

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

					plt.axvspan(0, 0, color='grey', alpha=0.3, label='main_force_entry')
					plt.axvspan(0, 0, color='pink', alpha=0.3, label='main_force_pulling_up')

					# main_force_entry = list(var5 > ref(var5, 1))
					# for i in range(len(main_force_entry)):
					# 	if main_force_entry[i]:
					# 		plt.axvspan(i, i + 1, color='grey', alpha=0.3)

					main_force_pulling_up = list(var51 < ref(var51, 1))
					for i in range(len(main_force_pulling_up)):
						if main_force_pulling_up[i]:
							plt.axvspan(i, i + 1, color='pink', alpha=0.3)

					plt.legend()
					plt.title(f'Trading Indicators {stock}')
					plt.xlabel('Date')
					plt.ylabel('Value')
					plt.show()
				except Exception as e:
					log_error(f"Exception when getting stock price for {stock}.", e)
			sleep(3600)
		log_info(f"Current time is not trading hour: {get_current_hhmmss_time()}.")
	finally:
		worker.stop()
		worker.join()


def main():
	set_log_level()
	while True:
		log_info("Loop Start...")
		while not TEST_MODE and (is_early_morning() or is_late_night()):
			log_info("Not trading hour, sleep 30 minutes....")
			sleep(1800)
		intraday_collecting()


if __name__ == "__main__":
	main()
