from time import sleep

from lib.stock_historical_collector import StockHistoricalCollector, HjkMetadata, BollingerMetadata, RSIMetadata
from util.util import *

from matplotlib import pyplot as plt

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

					# Golden Pit indicator
					golden_pit = list((df['term_line_8'] < 15) & (df['term_line_21'] < 15) & (df['term_line_55'] < 15))
					for i in range(len(golden_pit)):
						if golden_pit[i]:
							plt.axvspan(i, i + 1, color='yellow', alpha=0.3)

					resistance_signals = []
					for i in range(len(df)):
						if df['close_price'][i] >= df['upper_band'][i]:
							resistance_signals.append((range(len(df))[i], df['close_price'][i]))

					plt.plot(range(len(df)), df['close_price'], label='Close Price')
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

					for i in range(len(df)):
						if over_bought[i]:
							plt.axvspan(i, i + 1, color='red', alpha=0.3)
						if over_sold[i]:
							plt.axvspan(i, i + 1, color='green', alpha=0.3)

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
