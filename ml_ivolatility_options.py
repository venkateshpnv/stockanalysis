import requests
import pandas as pd
import io
import time
import mysql.connector
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import ivolatility as ivol

from common import *

# ========== 1. CONFIGURATION ==========
USERNAME = "venkateshpnv"
PASSWORD = "Ivolatility1@Pnv"
IVOL_URL = "https://www.ivolatility.com/data/historicalOptions"

MYSQL_CONFIG = {
    'user': 'root',
    'password': 'petla123',
    'host': '10.89.45.41',
    'database': 'US_Stocks_Options'
}

MAX_WORKERS = 10
RETRIES = 3
RETRY_WAIT = 5  # seconds between retries

# ========== 2. MYSQL SETUP ==========
def setup_mysql():
    conn = mysql.connector.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()
    # Create table if not exists
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS aapl_options_daily (
        id INT AUTO_INCREMENT PRIMARY KEY,
        query_date DATE,
        underlying_price FLOAT,
        expiration_date DATE,
        option_type VARCHAR(10),
        strike FLOAT,
        bid FLOAT,
        ask FLOAT,
        implied_volatility FLOAT,
        delta FLOAT,
        gamma FLOAT,
        theta FLOAT,
        vega FLOAT,
        rho FLOAT,
        open_interest INT
    )
    ''')
    conn.commit()
    return conn, cursor

# ========== 3. DATA FETCHER FUNCTION ==========
def fetch_options_for_date(date_str, option_type):
    payload = {
        "Username": "venkateshpnv",
        "Password": "Ivolatiliy1@Pnv",
        "Symbol": "AAPL",
        "Exchange": "US",
        "IncludeGreeks": "true",
        "OptionType": option_type,  # 'C' for Calls, 'P' for Puts
        "Date": date_str,
        "Format": "json"
        #"Format": "csv"
    }

    params = {
    'username': 'venkateshpnv',
    'password': 'Ivolatiliy1@Pnv',
    'symbol': 'AAPL',
    'date': date_str,
    'optType': 'ALL',
    'minuteType': 'MINUTE_1'
    }
    token = '64PI113qo3Qn5t60'
    alphavantage_token='IXS0YL6WXM7XV7PB'

    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {token}'
        }


    ## Replace with your IVolatility credentials
    #username = 'venkateshpnv'
    #password = 'Ivolatility1@Pnv'

    #ivol.setLoginParams(apiKey={token})
    #getOptionsChain = ivol.setMethod('/equities/option-series')
    #optionsChain = getOptionsChain(symbol='SPX', expFrom='2021-12-23', expTo='2025-12-23', callPut='C')
    #print(optionsChain)

    ## Obtain authentication token
    #auth_url = 'https://www.ivolatility.com/api/login'
    #auth_payload = {
    #    'username': username,
    #    'password': password
    #}

    #auth_response = requests.post(auth_url, json=auth_payload)

    #if auth_response.status_code == 200:
    #    token = auth_response.json().get('token')
    #    print(f"Authentication token: {token}")
    #else:
    #    print(f"Authentication failed with status code {auth_response.status_code}")

    url = 'https://www.restapi.ivolatility.com/equities/intraday/single-equity-option-rawiv?apiKey=64PI113qo3Qn5t60&symbol=SPY&date=2021-09-20&expDate=2022-06-17&strike=450&optType=CALL&minuteType=MINUTE_15'

    ret = requests.get(url)

    # Set the endpoint URL
    option_ids_url = 'https://www.ivolatility.com/api/equities/eod/nearest-option-tickers'
    
    # Set the request headers with the obtained token
    headers = {
        'Authorization': f'Bearer {token}'
    }
    
    # Define the parameters for the request
    params = {
        'symbol': 'AAPL',
        'dte': 30,           # Days to expiration
        'moneyness': 0,      # At-the-money
        'callPut': 'ALL'     # Retrieve both calls and puts
    }
    
    # Make the request to get option IDs
    option_ids_response = requests.get(option_ids_url, headers=headers, params=params)

    # Set the endpoint URL
    historical_data_url = 'https://www.ivolatility.com/api/equities/eod/single-stock-option-raw-iv'

    # Define the parameters for the request
    historical_params = {
        'option_id': option_ids[0],  # Use the first option ID as an example
        'from': '2015-01-01',
        'to': '2025-04-30'
    }

    # Make the request to get historical data
    historical_data_response = requests.get(historical_data_url, headers=headers, params=historical_params)

    if historical_data_response.status_code == 200:
        historical_data = historical_data_response.json()
        print(f"Retrieved historical data: {historical_data}")
    else:
        print(f"Failed to retrieve historical data with status code {historical_data_response.status_code}")
    
        if option_ids_response.status_code == 200:
            option_ids = option_ids_response.json()
            print(f"Retrieved option IDs: {option_ids}")
        else:
            print(f"Failed to retrieve option IDs with status code {option_ids_response.status_code}")


    for attempt in range(RETRIES):
        try:
            #response = requests.post(IVOL_URL, data=payload, timeout=30)
            #response = requests.get('https://restapi.ivolatility.com/dd/intraday/equity/options', params=params)
            response = requests.get('https://restapi.ivolatility.com/dd/intraday/equity/options', headers=headers, params=params)

            if response.status_code == 200:
                data = response.json()
                df = pd.DataFrame(data)
                #df = pd.read_csv(io.StringIO(response.text))
                df['QueryDate'] = date_str
                df['OptionType'] = option_type
                print(f"Fetched {option_type} for {date_str}")
                return df
            else:
                print(f"Attempt {attempt+1}: Failed {option_type} on {date_str} - Status {response.status_code}")
        except Exception as e:
            print(f"Attempt {attempt+1}: Exception on {option_type} {date_str}: {e}")
        
        time.sleep(RETRY_WAIT)  # wait before retrying
    
    print(f"Failed completely: {option_type} {date_str}")
    return None

# ========== 4. GET ALL TRADING DAYS ==========
def get_all_trading_days(start_date, end_date):
    holiday_list = get_holiday_list()
    #holidays = set(holiday_list['date'].dt.date)  # Convert holidays to a set of dates
    days = []
    current = start_date
    while current <= end_date:
        if current.weekday() < 5 and current.date() not in holiday_list:  # Exclude weekends and holidays
            days.append(current)
        current += timedelta(days=1)
    return days

# ========== 5. STORE INTO MYSQL ==========
def insert_into_mysql(cursor, df):
    for _, row in df.iterrows():
        cursor.execute('''
            INSERT INTO aapl_options_daily
            (query_date, underlying_price, expiration_date, option_type, strike, bid, ask, implied_volatility, delta, gamma, theta, vega, rho, open_interest)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            row.get('QueryDate'),
            row.get('Underlying Price', None),
            row.get('Expiration Date', None),
            row.get('OptionType', None),
            row.get('Strike Price', None),
            row.get('Bid', None),
            row.get('Ask', None),
            row.get('Implied Volatility', None),
            row.get('Delta', None),
            row.get('Gamma', None),
            row.get('Theta', None),
            row.get('Vega', None),
            row.get('Rho', None),
            row.get('Open Interest', None)
        ))

# ========== 6. MAIN EXECUTION ==========
def main():
    start_date = datetime(2015, 1, 1)
    end_date = datetime.now()

    trading_days = get_all_trading_days(start_date, end_date)
    date_strings = [d.strftime("%Y-%m-%d") for d in trading_days]

    #conn, cursor = setup_mysql()

    all_futures = []

    #with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    #    for date_str in date_strings:
    #        # Fetch PUTS
    #        future_put = executor.submit(fetch_options_for_date, date_str, "P")
    #        all_futures.append(future_put)
    #        # Fetch CALLS
    #        future_call = executor.submit(fetch_options_for_date, date_str, "C")
    #        all_futures.append(future_call)

    #    for future in as_completed(all_futures):
    #        df = future.result()
    #        if df is not None:
    #            insert_into_mysql(cursor, df)
    #            conn.commit()

    for date_str in date_strings:
        future_put = fetch_options_for_date(date_str, "P")
        all_futures.append(future_put)
        # Fetch CALLS
        future_call = fetch_options_for_date(date_str, "C")
        all_futures.append(future_call)
    for future in as_completed(all_futures):
        df = future.result()
        if df is not None:
            insert_into_mysql(cursor, df)
            conn.commit()

    conn.close()
    print("✅ All data saved into MySQL database!")

if __name__ == "__main__":
    main()
