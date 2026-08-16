import yfinance as yf
import talib
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import classification_report, accuracy_score
from DB import *

mysql_engine = DB.open_sql_connection('localhost', 'root', 'petla123', db='US_Stocks')

# Step 1: Download historical price data
sym = "NVDA"
query = 'select Date, Open, High, Low, Volume, Close, `Adj Close` from {}'.format(get_symbol_table_name(sym))
#data = yf.download(symbol, start="2021-01-01", end="2024-03-22")
data = read_from_sql(query, mysql_engine)
data = normalize_cols_with_adj_close(data)
#data = data.tail(500)

# Technical indicators
data["rsi_current"] = talib.RSI(data["Adj Close"], timeperiod=14)
data["rsi_60_low"] = data["rsi_current"].rolling(window=60).min()
data["rsi_60_high"] = data["rsi_current"].rolling(window=60).max()
data["rsi_ratio"] = (data["rsi_current"] - data["rsi_60_low"]) / (data["rsi_60_high"] - data["rsi_60_low"] + 1e-9)

data["psar"] = talib.SAR(data["High"], data["Low"], acceleration=0.02, maximum=0.2)
data["psar_trend"] = np.where(data["psar"] > data["Adj Close"], 1, 0)

data["price_change"] = data["Adj Close"].pct_change() * 100
data["cci"] = talib.CCI(data["High"], data["Low"], data["Adj Close"], timeperiod=14)
macd, macd_signal, macd_hist = talib.MACD(data["Adj Close"])
data["macd"] = macd
data["macd_hist"] = macd_hist

# Additional Features
data["atr"] = talib.ATR(data["High"], data["Low"], data["Adj Close"], timeperiod=14)
data["close_to_high10"] = data["Adj Close"] / data["High"].rolling(window=10).max()
data["close_to_low10"] = data["Adj Close"] / data["Low"].rolling(window=10).min()
data["rsi_slope"] = data["rsi_current"].diff(periods=5)

# Future target
future_return = data["Adj Close"].pct_change(periods=5).shift(-5) * 100

# Classification target
def classify(future_ret):
    if future_ret > 5:
        #return 1  # Buy
        return 2  # Buy
    elif future_ret < -5:
        #return -1  # Sell
        return 0  # Sell
    else:
        #return 0  # Hold
        return 1  # Hold

data["signal_class"] = future_return.apply(classify)

data.dropna(inplace=True)

# Features and Target
features = [
    "psar_trend", "rsi_ratio", "price_change", "cci", "macd", "macd_hist",
    "atr", "close_to_high10", "close_to_low10", "rsi_slope"
]
target = "signal_class"

# Prepare datasets
future_data = data[-20:]
train_test_data = data[:-20]

X = train_test_data[features]
y = train_test_data[target]

# Scale
scaler = MinMaxScaler()
X_scaled = scaler.fit_transform(X)

# Train/test split
X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

# Train XGBoost
model = xgb.XGBClassifier(n_estimators=100, learning_rate=0.1, max_depth=5, random_state=42, use_label_encoder=False, eval_metric='mlogloss')
model.fit(X_train, y_train)

# Test evaluation
y_pred = model.predict(X_test)
print("Test Accuracy:", accuracy_score(y_test, y_pred))
print(classification_report(y_test, y_pred, target_names=["Sell", "Hold", "Buy"]))

# Predict on future data
X_future_scaled = scaler.transform(future_data[features])
future_probs = model.predict_proba(X_future_scaled)  # Gives probability for each class

# Attach predictions
future_data = future_data.copy()
future_data["Sell_Prob(%)"] = future_probs[:,0] * 100
future_data["Hold_Prob(%)"] = future_probs[:,1] * 100
future_data["Buy_Prob(%)"] = future_probs[:,2] * 100

print(future_data[["Adj Close", "Sell_Prob(%)", "Hold_Prob(%)", "Buy_Prob(%)"]])

