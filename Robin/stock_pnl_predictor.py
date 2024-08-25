import robin_stocks.robinhood as rh
import pandas as pd
import numpy as np
from keras.src.layers import Conv1D, MaxPooling1D
from keras.src.regularizers import l2
from sklearn.preprocessing import MinMaxScaler
from keras.models import Sequential
from keras.layers import LSTM, Dense, Dropout
from util.util import login

# Login to Robinhood (replace 'your_username' and 'your_password' with actual credentials)
login()

# Fetch historical data for TSLA (adjust dates as needed)
historical_data = rh.stocks.get_stock_historicals('TSLA', interval='5minute', span='week')
df = pd.DataFrame(historical_data)
print(df.head(10))

df['open_price'] = df['open_price'].astype(float)
df['high_price'] = df['high_price'].astype(float)
df['low_price'] = df['low_price'].astype(float)
df['close_price'] = df['close_price'].astype(float)
df['volume'] = df['volume'].astype(float)

# Convert timestamp to datetime and set as index
df['begins_at'] = pd.to_datetime(df['begins_at'])
df.set_index('begins_at', inplace=True)

# Select relevant columns (open, high, low, close, volume)
df = df[['open_price', 'high_price', 'low_price', 'close_price', 'volume']]

# Feature selection (you may adjust this based on your data)
features_price = ['open_price', 'high_price', 'low_price', 'close_price']
features_volume = ['volume']

# Split into X and y
X = df[features_price + features_volume].values
y = df['close_price'].values

# Normalize X (features)
scaler_X = MinMaxScaler(feature_range=(0, 1))
X = scaler_X.fit_transform(X)

# Normalize y (target)
scaler_y = MinMaxScaler(feature_range=(0, 1))
y = scaler_y.fit_transform(y.reshape(-1, 1))


# Function to create sequences for LSTM
def create_sequences(data, target, seq_length):
    X, y = [], []
    for i in range(len(data)-seq_length-1):
        X.append(data[i:(i+seq_length)])
        y.append(target[i+seq_length])  # predicting 'close_price' for the next day
    return np.array(X), np.array(y), np.array(data[-seq_length:])


# Create sequences of length 50 (adjust as needed)
sequence_length = 30
X, y, last_sequence = create_sequences(X, y, sequence_length)

# Randomly shuffle indices
indices = np.arange(len(X))
np.random.shuffle(indices)

X = X[indices]
y = y[indices]

# Train-test split (80% train, 20% test)
split_ratio = 0.8
split = int(split_ratio * len(X))

X_train, X_test = X[:split], X[split:]
y_train, y_test = y[:split], y[split:]

# Build LSTM model
model = Sequential([
    LSTM(units=60, return_sequences=False, input_shape=(X_train.shape[1], X_train.shape[2])),
    Dropout(0.2),
    Dense(units=25),
    Dense(units=1)
])

model.compile(optimizer='adam', loss='mean_squared_error')

# Print summary of the model
model.summary()

# Train the model
history = model.fit(X_train, y_train, epochs=200, batch_size=32, validation_data=(X_test, y_test), shuffle=True)

# Evaluate the model
loss = model.evaluate(X_test, y_test)
print(f"Test Loss: {loss}")

# Predictions for the next trading day
# last_sequence = X_test[-1].reshape(1, sequence_length, X_test.shape[2])  # take the last sequence from the test data
last_sequence = last_sequence.reshape(1, sequence_length, X_test.shape[2])
next_day_prediction = model.predict(last_sequence)

# Inverse transform the prediction to get the actual price
next_day_prediction_actual = scaler_y.inverse_transform(next_day_prediction)[0][0]

print(f"\nPredicted Next Day's Closing Price: {next_day_prediction_actual}")

# Print random data points from the testing set with date, actual price, and estimated price
print("\nRandom Data Points from Testing Set:")
print("Date | Actual Price | Estimated Price")
random_indices = np.random.choice(len(X_test), size=10, replace=False)
for idx in random_indices:
    date = df.index[indices[split+idx] + sequence_length]
    actual_price1 = df.iloc[indices[split+idx] + sequence_length]['close_price']
    actual_price2 = scaler_y.inverse_transform([y_test[idx]])[0][0]
    # Prepare the input sequence for prediction
    input_sequence = X_test[idx].reshape(1, sequence_length, X_test.shape[2])
    # Predict the next day's closing price
    estimated_price = model.predict(input_sequence)
    # Inverse transform the predicted price
    estimated_price_actual = scaler_y.inverse_transform(estimated_price)[0][0]
    print(f"{date} | {actual_price1:.2f} | {actual_price2:.2f} |{estimated_price_actual:.2f}")