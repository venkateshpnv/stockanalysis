import requests

# Your MarketData.app API key
token = 'dHVKZE1BOFltVVEwLWhsdF9scC15N2h5X1NaVjF6Yldtdnlzd21mTV85ND0'

# The stock symbol for which you want to fetch option contracts
stock_symbol = 'CRWD'  # Example: 'AAPL' for Apple Inc.

# Base URL for cached options data
url = f'https://api.marketdata.app/v1/options/{stock_symbol}/cached'

headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer '+token
        }

# Make the request
response = requests.get(url, headers=headers)

# Check the response status and print the data
if response.status_code == 200:
    data = response.json()
    print(data)
else:
    print(f"Error: {response.status_code}")
    print(response.text)

