from time import sleep

from lib.stock_historical_collector import StockHistoricalCollector, HjkMetadata
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
						[
							HjkMetadata(interval=8, smooth_parameters=[3, 3], std_interval=21, std_multiplier=3),
							HjkMetadata(interval=21, smooth_parameters=[5], std_interval=37, std_multiplier=2),
							HjkMetadata(interval=55, smooth_parameters=[5], std_interval=0, std_multiplier=0)
						])
					# Plotting the lines
					plt.figure(figsize=(12, 6))
					df['index'] = list(range(len(df)))
					plt.plot(df['index'], df['term_line_8'], label='short_term', color='blue')
					plt.plot(df['index'], df['term_line_21'], label='mid_term', color='grey')
					plt.plot(df['index'], df['term_line_55'], label='long_term', color='purple')


					# Golden Pit indicator
					golden_pit = (df['term_line_8'] < 15) & (df['term_line_21'] < 15) & (df['term_line_55'] < 15)

					for i in range(len(golden_pit) - 1):
						if golden_pit[i]:
							plt.axvspan(df['index'][i], df['index'][i + 1], color='yellow', alpha=0.3)

					# Adding labels for bottom and Top
					for i in range(len(df)):
						if df['term_line_21'][i] < 20:
							plt.annotate('X', (df['index'][i], df['term_line_21'][i]),
										 textcoords="offset points", xytext=(0, -10), ha='center', color='green',
										 fontsize=8)
						if df['term_line_21'][i] > 80:
							plt.annotate('X', (df['index'][i], df['term_line_21'][i]),
										 textcoords="offset points", xytext=(0, 10), ha='center', color='red',
										 fontsize=8)

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
