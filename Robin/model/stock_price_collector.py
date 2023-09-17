import yfinance as yf
from enum import Enum
from sklearn.preprocessing import MinMaxScaler
from matplotlib import pyplot
import numpy as np

from keras.models import Sequential
from keras.layers import Dense
from keras.layers import LSTM

class Period(Enum):
	LONG_TERM = 1
	MID_TERM = 2
	SHORT_TERM = 3


def get_stock_prices(symbol: str, period: Period):
	stock_prices = None
	if period == Period.LONG_TERM:
		stock_prices = yf.download(tickers=symbol, period="1500d", interval="1d")
	elif period == Period.MID_TERM:
		stock_prices = yf.download(tickers=symbol, period="60d", interval="5m")
	elif period == Period.SHORT_TERM:
		stock_prices = yf.download(tickers=symbol, period="5d", interval="1m")

	print(stock_prices.columns)
	return stock_prices[["High", "Low", "Volume"]]


def get_test_data(symbol: str, period: Period):
	pass


def split_data_by_daybeginning(data, num_days, min_dict, max_dict):
	length = len(data) // num_days
	l = []
	for i in range(num_days):
		l.append(data.iloc[length * i + 1: length * (i + 1)].copy())

	for day_data in l:
		day_data.loc[len(day_data)] = min_dict
		day_data.loc[len(day_data)] = max_dict
	return l

def create_traiing_data(data, Y_min, Y_max, training_data_points=10, min_max_period=5):
	for row in range(len(data) - training_data_points - min_max_period):
		y = min([data_point[1] for data_point in data[row + training_data_points: row + training_data_points + min_max_period, :]])
		Y_min.append(y)
		y = max([data_point[0] for data_point in data[row + training_data_points: row + training_data_points + min_max_period, :]])
		Y_max.append(y)
		


# buffer is used to account for stock price grow/drop beyond the existing min/max range.
def normalize_data(data, num_days=5, buffer=0.1):
	min_dict = {column: min(data[column]) * (1 - buffer) for column in data.columns}
	max_dict = {column: max(data[column]) * (1 + buffer) for column in data.columns}
	scaler = MinMaxScaler(feature_range=(0,1))
	data_by_day = split_data_by_daybeginning(data, num_days, min_dict, max_dict)
	data_by_day = [scaler.fit_transform(df.values)[0:-2, :] for df in data_by_day]

	training_data_points = 10
	min_max_period = 5
	X = np.concatenate([data[0:-min_max_period, :] for data in data_by_day], axis=0)
	X = X.reshape((X.shape[0], 1, X.shape[1]))
	Y_min = []
	Y_max = []
	for data in data_by_day:
		create_traiing_data(data, Y_min, Y_max, training_data_points, min_max_period)
	Y_min, = np.array(Y_min), np.array(Y_max)
	return X, Y_min, Y_max


data = get_stock_prices("TSLA", Period.SHORT_TERM)
X, Y_min, Y_max = normalize_data(data)

print(X.shape)
print(Y_min.shape, Y_max.shape)


# def LSTM_network():
# 	model = Sequential()
# 	model.add(LSTM(50, input_shape=(train_X.shape[1], train_X.shape[2])))
# 	model.add(Dense(1))
# 	model.compile(loss='mae', optimizer='adam')
# 	# fit network
# 	history = model.fit(train_X, train_y, epochs=50, batch_size=72, validation_data=(test_X, test_y), verbose=2, shuffle=False)
# 	# plot history
# 	pyplot.plot(history.history['loss'], label='train')
# 	pyplot.plot(history.history['val_loss'], label='test')
# 	pyplot.legend()
# 	pyplot.show()


