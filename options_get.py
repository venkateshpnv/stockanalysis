import requests
import datetime
import time
import pymysql
import sqlalchemy
import pandas as pd

#API_KEY = "YOUR_POLYGON_API_KEY"
#API_KEY = "e0qK5Ek50Y7dwPE2U2EnAH2Lxcmz5iQj"
API_KEY = "2AucpFF4dCC31HNXfUKanrHGilcwp4Qy"

# Database setup
MYSQL_USER = 'your_mysql_user'
MYSQL_PASSWORD = 'your_mysql_password'
MYSQL_HOST = 'localhost'
MYSQL_PORT = 3306
MYSQL_DATABASE = 'options_db'

#engine = sqlalchemy.create_engine(
#    f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
#)

def get_all_put_contracts(symbol, as_of_date):
    """Fetch all PUT contracts for the given date."""
    url = f"https://api.polygon.io/v3/reference/options/contracts?underlying_ticker={symbol}&as_of={as_of_date}&contract_type=put&expired=false&limit=1000&apiKey={API_KEY}"
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Failed fetching contracts for {as_of_date}")
        return []
    contracts = response.json().get('results', [])
    return contracts

def get_option_snapshot(option_symbol):
    """Fetch snapshot to get bid/ask/last and greeks."""
    url = f"https://api.polygon.io/v3/snapshot/options/{option_symbol}?apiKey={API_KEY}"
    response = requests.get(url)
    if response.status_code != 200:
        return None
    return response.json().get('results', None)

def main():
    start_date = datetime.date(2025, 4, 25)
    end_date = datetime.date.today()

    current_date = start_date

    batch = []

    while current_date <= end_date:
        print(f"Fetching for date: {current_date}")
        
        try:
            contracts = get_all_put_contracts("AAPL", current_date.strftime("%Y-%m-%d"))
        except Exception as e:
            print(f"Error on {current_date}: {e}")
            contracts = []

        if contracts:
            for c in contracts:
                option_symbol = c.get('ticker')
                snapshot = get_option_snapshot(option_symbol)
                time.sleep(0.2)  # Sleep to avoid rate limits

                if snapshot:
                    bid = snapshot.get('last_quote', {}).get('bid', None)
                    ask = snapshot.get('last_quote', {}).get('ask', None)
                    last = snapshot.get('last_quote', {}).get('last', None)

                    greeks = snapshot.get('greeks', {})
                    delta = greeks.get('delta', None)
                    gamma = greeks.get('gamma', None)
                    theta = greeks.get('theta', None)
                    vega = greeks.get('vega', None)
                    implied_volatility = greeks.get('iv', None)

                    batch.append({
                        "as_of_date": current_date,
                        "contract_symbol": option_symbol,
                        "expiration_date": c.get('expiration_date'),
                        "strike_price": c.get('strike_price'),
                        "contract_type": c.get('contract_type'),
                        "exercise_style": c.get('exercise_style'),
                        "shares_per_contract": c.get('shares_per_contract'),
                        "underlying_ticker": c.get('underlying_ticker'),
                        "bid": bid,
                        "ask": ask,
                        "last_price": last,
                        "delta": delta,
                        "gamma": gamma,
                        "theta": theta,
                        "vega": vega,
                        "implied_volatility": implied_volatility
                    })
                else:
                    print(f"No snapshot for {option_symbol}")

        # Bulk save every 3000 records
        if len(batch) >= 3000:
            df = pd.DataFrame(batch)
            df.to_sql('aapl_put_options_full', con=engine, if_exists='append', index=False)
            print(f"Saved {len(batch)} records to MySQL.")
            batch = []

        current_date += datetime.timedelta(days=1)
        time.sleep(0.5)  # Be polite to API limits

    # Save any remaining
    if batch:
        df = pd.DataFrame(batch)
        df.to_sql('aapl_put_options_full', con=engine, if_exists='append', index=False)
        print(f"Saved final {len(batch)} records to MySQL.")

if __name__ == "__main__":
    main()

