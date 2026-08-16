import requests
from datetime import datetime, timedelta
import DB

# Your Polygon.io API key
api_key = 'e0qK5Ek50Y7dwPE2U2EnAH2Lxcmz5iQj'

# The stock symbol for which you want to fetch option contracts
stock_symbol = 'CRWD'  # Example: 'AAPL' for Apple Inc.

# Get the current stock price
def get_current_stock_price(symbol):
    #url = f'https://api.polygon.io/v2/last/trade/{symbol}'
    #params = {'apiKey': api_key}
    #response = requests.get(url, params=params)
    url='https://eodhd.com/api/real-time/{}.US?api_token={}&fmt=json'.format(symbol, DB.get_eod_token_id())
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data['close']
    else:
        print(f"Error fetching stock price: {response.status_code}")
        return None

# Calculate the dates
today = datetime.now()
end_date = today + timedelta(days=10)
today_str = today.strftime('%Y-%m-%d')
end_date_str = end_date.strftime('%Y-%m-%d')

# Get the current stock price
#current_price = get_current_stock_price(stock_symbol)
current_price = 308.69

if current_price:
    # Base URL for options contracts
    url = 'https://api.polygon.io/v3/reference/options/contracts'

    # Headers
    headers = {
        'Authorization': f'Bearer {api_key}'
    }

    # Parameters
    params = {
        'underlying_ticker': stock_symbol,
        'expiration_date.gte': today_str,
        'expiration_date.lte': end_date_str,
        'strike_price.gte': current_price,
        'contract_type': 'call',
        'limit': 1
        #'sort': 'strike_price.asc'  # Sort by strike price ascending to get the first OTM call
    }

    ## Make the request
    #response = requests.get(url, headers=headers, params=params)

    ## Check the response status and print the data
    #if response.status_code == 200:
    #    data = response.json()
    #    print(data)
    #else:
    #    print(f"Error: {response.status_code}")
    #    print(response.text)

    #call_contract = data['results'][0]['ticker']
    call_contract = 'O:CRWD240607C00310000'
    #url = f'https://api.polygon.io/v3/reference/options/contracts/{call_contract}'
    url = 'https://api.polygon.io/v3/snapshot/options/{}/{}?apiKey={}'.format(stock_symbol, call_contract, api_key)

    response = requests.get(url, headers=headers)
    # Check the response status and print the data
    if response.status_code == 200:
        data = response.json()
        print(data)
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

