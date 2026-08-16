import talib
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler

import DB

# Function to try the model and return the buy date
def try_model(df):
    """Tries to find a buy date based on the model predictions."""
    # Extract features and target variable
    X = df[["psar_trend", "rsi_diff", "price_change", "cci", "macd"]]
    y = df["signal"]

    # Normalize input features
    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(X)

    # Split data into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

    # Train the model
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    # Predict on the test set
    predictions = model.predict(X_test)

    # Find the buy date based on predictions
    buy_date_index = np.argmax(predictions > 0)  # Find the first index where prediction is positive
    if buy_date_index >= len(df):
        return None

    return df.iloc[buy_date_index]["Date"]

# Function to fetch historical stock price data
def get_stock_price_data(sym):
    """
    Fetches historical stock price data from the database.
    """
    # Connect to the MySQL database
    # Assuming DB.open_sql_connection and DB.read_from_sql are defined in the DB module
    # Replace with your actual database connection details

    mysql_engine = DB.open_sql_connection('localhost', 'root', 'petla123', db='US_Stocks')

    try:
        query = 'select Date, Open, High, Low, Volume, Close, `Adj Close` from {}'.format(DB.get_symbol_table_name(sym))
        df = DB.read_from_sql(query, mysql_engine)
        df = DB.normalize_cols_with_adj_close(df)
        ## Take only last one year data
        #df = df.tail(250)

        return df
    finally:
        DB.close_sql_connection(mysql_engine)

def process_model(sym):

    # Step 1: Fetch Historical Price Data
    data = get_stock_price_data(sym)
    end = 60
    while end < len(df):
        buy_date = try_model(df.iloc[0:end])
        if not buy_date:
            print("Got a date when to buy/sell stock/option")
            # Calculate the put option profit here
        end = end + 1



# Step 2: Calculate Technical Indicators

# 1. Compute PSAR Trend
psar = talib.SAR(data['High'], data['Low'], acceleration=0.02, maximum=0.2)
data["psar_trend"] = np.where(psar > data["Adj Close"], 1, 0)  # 1 = Down, 0 = Up

# 2. RSI and 60-day RSI low difference
rsi = talib.RSI(data['Adj Close'], timeperiod=14)
rsi_60_day_low = rsi.rolling(window=60).min()
data["rsi_diff"] = rsi_60_day_low - rsi

# 3. Price Change %
data["price_change"] = data["Adj Close"].pct_change() * 100

# 4. CCI Indicator
data["cci"] = talib.CCI(data['High'], data['Low'], data['Adj Close'], timeperiod=14)

# 5. MACD Indicator
macd, macdsignal, macdhist = talib.MACD(data['Adj Close'], fastperiod=12, slowperiod=26, signalperiod=9)
data["macd"] = macd

# Drop NaN values from indicator calculations
data.dropna(inplace=True)

# Step 3: Prepare Data for Machine Learning

# Features (X)
X = data[["psar_trend", "rsi_diff", "price_change", "cci", "macd"]]

# Generate synthetic trading signal (-100% to 100%) based on price movement
data["signal"] = (data["Adj Close"].pct_change(5) * 100).shift(-5)  # Future return over 5 days
data["signal"] = np.clip(data["signal"], -100, 100)  # Limit between -100% and 100%

# Drop NaN rows
data.dropna(inplace=True)

# Target Variable (Y)
y = data["signal"]

# Normalize Input Features
scaler = MinMaxScaler()
X_scaled = scaler.fit_transform(X)

# Split Data for Training
X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

# Step 4: Train Machine Learning Model
model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Step 5: Function to Predict Signal for New Data
def predict_trade_signal(high, low, close):
    """
    Predicts a trading signal based on new stock price data.
    """
    psar_val = talib.SAR(np.array([high]), np.array([low]), acceleration=0.02, maximum=0.2)[-1]
    psar_trend = 1 if psar_val > close else 0
    
    rsi_val = talib.RSI(np.array([close]), timeperiod=14)[-1]
    rsi_60_day_low = min(rsi[-60:])  # Approximate 60-day RSI low
    rsi_diff = rsi_60_day_low - rsi_val
    
    price_change = ((close - data["Adj Close"].iloc[-1]) / data["Adj Close"].iloc[-1]) * 100
    cci_val = talib.CCI(np.array([high]), np.array([low]), np.array([close]), timeperiod=14)[-1]
    macd_val = talib.MACD(np.array([close]), fastperiod=12, slowperiod=26, signalperiod=9)[0][-1]

    input_features = np.array([[psar_trend, rsi_diff, price_change, cci_val, macd_val]])
    input_scaled = scaler.transform(input_features)
    
    predicted_signal = model.predict(input_scaled)[0]
    
    return f"Predicted Signal: {predicted_signal:.2f}%"  # Output in percentage form

# Example Prediction for New Price
new_signal = predict_trade_signal(high=175, low=170, close=172)
print(new_signal)

