# Import necessary libraries
import robin_stocks.robinhood as rh
import numpy as np
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
from keras.models import Sequential
from keras.layers import LSTM, Dense, Dropout
from keras.callbacks import History

from util.util import login

login()


# Step 1: Fetch data using robin_stocks
def fetch_stock_data():
	# Assuming you have authenticated and set up robin_stocks already
	historical_data = rh.stocks.get_stock_historicals("TSLA", interval="5minute", span="week")

	# Extract high, low, close prices and volumes
	highs = np.array([float(item['high_price']) for item in historical_data])
	lows = np.array([float(item['low_price']) for item in historical_data])
	closes = np.array([float(item['close_price']) for item in historical_data])
	volumes = np.array([float(item['volume']) for item in historical_data])

	return highs, lows, closes, volumes


# Step 2: Data preprocessing function
def preprocess_data(highs, lows, closes, volumes):
	# MinMax scaling for high, low, close prices
	price_scaler = MinMaxScaler()
	highs_scaled = price_scaler.fit_transform(highs.reshape(-1, 1))
	lows_scaled = price_scaler.transform(lows.reshape(-1, 1))
	closes_scaled = price_scaler.transform(closes.reshape(-1, 1))

	# MinMax scaling for volume
	volume_scaler = MinMaxScaler()
	volumes_scaled = volume_scaler.fit_transform(volumes.reshape(-1, 1))

	# MinMax scaling for output close prices
	close_scaler = MinMaxScaler()
	closes_output_scaled = close_scaler.fit_transform(closes.reshape(-1, 1))

	return highs_scaled, lows_scaled, closes_scaled, volumes_scaled, closes_output_scaled, price_scaler, volume_scaler, close_scaler


# Step 3: Prepare data for LSTM
def create_sequences(highs, lows, closes, volumes, sequence_length):
	X, Y = [], []
	for i in range(len(closes) - sequence_length):
		X.append(np.column_stack((highs[i:i + sequence_length],
								  lows[i:i + sequence_length],
								  closes[i:i + sequence_length],
								  volumes[i:i + sequence_length])))
		Y.append(closes[i + sequence_length])  # Use the next close price as Y

	X = np.array(X)
	Y = np.array(Y)

	return X, Y


# Step 4: Define LSTM model
def create_lstm_model(input_shape):
	model = Sequential()
	model.add(LSTM(units=50, return_sequences=True, input_shape=input_shape))
	model.add(Dropout(0.2))
	model.add(LSTM(units=50, return_sequences=False))
	model.add(Dropout(0.2))
	model.add(Dense(units=50, activation='relu'))
	model.add(Dense(units=1))  # Output layer for close price prediction

	model.compile(optimizer='adam', loss='mse')  # Use MSE as loss function for regression

	return model


# Step 5: Plot loss function
def plot_loss(history):
	plt.plot(history.history['loss'], label='Training Loss')
	plt.plot(history.history['val_loss'], label='Validation Loss')
	plt.title('Model Loss')
	plt.xlabel('Epochs')
	plt.ylabel('Loss')
	plt.legend()
	plt.show()


def predict_and_plot(model, X, Y, close_scaler):
	predictions_scaled = model.predict(X)
	predictions = close_scaler.inverse_transform(predictions_scaled)
	actual_prices = close_scaler.inverse_transform(Y.reshape(-1, 1))

	plt.figure(figsize=(14, 7))
	plt.plot(actual_prices, label='Actual Prices')
	plt.plot(predictions, label='Predicted Prices')
	plt.title('Actual vs Predicted Prices')
	plt.xlabel('Time')
	plt.ylabel('Price')
	plt.legend()
	plt.show()


# Main function to train and predict
def main():
	# Step 1: Fetch data
	highs, lows, closes, volumes = fetch_stock_data()

	# Step 2: Preprocess data
	highs_scaled, lows_scaled, closes_scaled, volumes_scaled, closes_output_scaled, price_scaler, volume_scaler, close_scaler = preprocess_data(
		highs, lows, closes, volumes)

	# Step 3: Create sequences for LSTM
	sequence_length = 50  # Example sequence length
	X, Y = create_sequences(highs_scaled, lows_scaled, closes_scaled, volumes_scaled, sequence_length)

	# Step 4: Split data into training and testing sets
	X_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size=0.2, shuffle=True)

	# Step 5: Create and train LSTM model
	model = create_lstm_model(input_shape=(X_train.shape[1], X_train.shape[2]))

	history = History()
	model.fit(X_train, Y_train, epochs=300, batch_size=32, validation_data=(X_test, Y_test), callbacks=[history])

	# Step 6: Plot loss function
	plot_loss(history)

	# Step 7: Predict next data point (5 minutes ahead)
	# Example: Assume X_test has the latest available sequence
	latest_sequence = X_test[-1].reshape(1, X_test.shape[1], X_test.shape[2])
	prediction_scaled = model.predict(latest_sequence)[0, 0]
	prediction = close_scaler.inverse_transform([[prediction_scaled]])[0, 0]
	actual_price = close_scaler.inverse_transform(Y_test[-1].reshape(-1, 1))[0, 0]

	print(f"Prediction for the next 5 minutes: {prediction:.2f}")
	print(f"Actual price: {actual_price:.2f}")

	# Step 8: Print 20 samples from the test set with actual vs predicted close prices
	print("\nActual vs Predicted Close Prices for 20 Samples:")
	for i in range(20):
		sample_sequence = X_test[i].reshape(1, X_test.shape[1], X_test.shape[2])
		sample_prediction_scaled = model.predict(sample_sequence)[0, 0]
		sample_prediction = close_scaler.inverse_transform([[sample_prediction_scaled]])[0, 0]
		sample_actual_price = close_scaler.inverse_transform(Y_test[i].reshape(-1, 1))[0, 0]
		print(f"Sample {i + 1}: Actual = {sample_actual_price:.2f}, Predicted = {sample_prediction:.2f}")

	predict_and_plot(model, X, Y, close_scaler)

# Execute main function
if __name__ == "__main__":
	main()
