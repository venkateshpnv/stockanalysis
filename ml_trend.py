import yfinance as yf
import talib
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_absolute_error, r2_score
from DB import *

#c = DB.open_db_client()
#db = c['Stocks']
#collection = DB.get_collection('US', db)
mysql_engine = DB.open_sql_connection('localhost', 'root', 'petla123', db='US_Stocks')

# Step 1: Download historical price data
sym = "NVDA"
query = 'select Date, Open, High, Low, Volume, Close, `Adj Close` from {}'.format(get_symbol_table_name(sym))
#data = yf.download(sym, start="2023-01-01", end="2024-03-22")

data = read_from_sql(query, mysql_engine)
data = normalize_cols_with_adj_close(data)
data = data.tail(500)

# Step 2: Calculate technical indicators
data["psar_trend"] = np.where(talib.SAR(data['High'], data['Low']) > data["Adj Close"], 1, 0)
data["rsi_current"] = talib.RSI(data["Adj Close"], timeperiod=14)
data["rsi_60_day_low"] = data["rsi_current"].rolling(window=60).min()
data["rsi_60_day_high"] = data["rsi_current"].rolling(window=60).max()
data["rsi_ratio"] = (data["rsi_current"] - data["rsi_60_day_low"]) / (data["rsi_60_day_high"] - data["rsi_60_day_low"])

# Find all points where rsi_ratio == 0
rsi_zero_indices = data.index[data["rsi_ratio"] == 0].tolist()
zero_and_rebound_entries = []

# For each zero, find the first RSI rebound (rsi_ratio >= 0.5) in next 14 days
for idx in rsi_zero_indices:
    current_loc = data.index.get_loc(idx)
    zero_entry = data.loc[[idx], ['Adj Close', 'rsi_ratio', 'rsi_current', 'rsi_60_day_low', 'rsi_60_day_high']]
    zero_entry["label"] = "rsi_zero"

    # Future 14-day window
    future_window = data.iloc[current_loc+1: current_loc+15]
    rebound_idx = future_window[future_window["rsi_ratio"] >= 0.5].first_valid_index()

    if rebound_idx:
        rebound_entry = data.loc[[rebound_idx], ['Adj Close', 'rsi_ratio', 'rsi_current', 'rsi_60_day_low', 'rsi_60_day_high']]
        rebound_entry["label"] = "rsi_rebound"
        zero_and_rebound_entries.append(zero_entry)
        zero_and_rebound_entries.append(rebound_entry)

# Combine all entries and sort by date
final_df = pd.concat(zero_and_rebound_entries).sort_index()
final_df.insert(0, "day", final_df.index.day_name())
final_df = final_df[~final_df.index.duplicated(keep='first')]
print(final_df)

data["price_change"] = data["Adj Close"].pct_change() * 100
data["cci"] = talib.CCI(data["High"], data["Low"], data["Adj Close"], timeperiod=14)
macd, _, _ = talib.MACD(data["Adj Close"])
data["macd"] = macd

# Step 3: Create target output (future price % change)
data["signal"] = data["Adj Close"].pct_change(periods=5).shift(-5) * 100
data["signal"] = np.clip(data["signal"], -100, 100)

# Drop NaNs
data.dropna(inplace=True)

# Features and target
features = ["psar_trend", "rsi_ratio", "price_change", "cci", "macd"]
target = "signal"

# Split into train, test, and future
future_data = data[-20:]
train_test_data = data[:-20]

X = train_test_data[features]
y = train_test_data[target]

scaler = MinMaxScaler()
X_scaled = scaler.fit_transform(X)

X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

# Step 5: Train the model
model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Evaluate model
y_pred = model.predict(X_test)
print("Test MAE:", mean_absolute_error(y_test, y_pred))
print("Test R²:", r2_score(y_test, y_pred))

# Predict for future
X_future_scaled = scaler.transform(future_data[features])
future_data["predicted_signal"] = model.predict(X_future_scaled)

# Show final predictions
print(future_data[["Adj Close", "rsi_ratio", "predicted_signal"]])

# Step 6: Predict signal for new input
def predict_trade_signal(high, low, close, rsi_series):
    psar_val = talib.SAR(np.array([high]), np.array([low]))[-1]
    psar_trend = 1 if psar_val > close else 0

    rsi_val = talib.RSI(np.array([close]), timeperiod=14)[-1]
    rsi_60_low = rsi_series[-60:].min()
    rsi_60_high = rsi_series[-60:].max()
    rsi_ratio = (rsi_val - rsi_60_low) / (rsi_60_high - rsi_60_low + 1e-9)  # avoid div by zero

    price_change = ((close - data["Adj Close"].iloc[-1]) / data["Close"].iloc[-1]) * 100
    cci_val = talib.CCI(np.array([high]), np.array([low]), np.array([close]), timeperiod=14)[-1]
    macd_val = talib.MACD(np.array([close]), fastperiod=12, slowperiod=26, signalperiod=9)[0][-1]

    features = np.array([[psar_trend, rsi_ratio, price_change, cci_val, macd_val]])
    scaled_input = scaler.transform(features)
    signal_pct = model.predict(scaled_input)[0]

    return f"Predicted Signal: {signal_pct:.2f}%"

# Example usage
rsi_series_full = data["rsi_current"]
new_signal = predict_trade_signal(high=175, low=170, close=172, rsi_series=rsi_series_full)
print(new_signal)

