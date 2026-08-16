import yfinance as yf
import pandas as pd

# Function to get stock tickers from an index
def get_tickers(index):
    tickers = []
    if index == "sp500":
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        table = pd.read_html(url)[0]
        tickers = table["Symbol"].tolist()
    elif index == "nasdaq100":
        url = "https://en.wikipedia.org/wiki/NASDAQ-100"
        table = pd.read_html(url)[4]  # Table containing tickers
        tickers = table["Symbol"].tolist()
    elif index == "russell1000":
        url = "https://en.wikipedia.org/wiki/Russell_1000_Index"
        table = pd.read_html(url)[2]
        tickers = table["Ticker"].tolist()
    return tickers

# Fetch tickers from major indices
sp500_tickers = get_tickers("sp500")
nasdaq100_tickers = get_tickers("nasdaq100")
#russell1000_tickers = get_tickers("russell1000")

# Combine all tickers and remove duplicates
all_tickers = list(set(sp500_tickers + nasdaq100_tickers))
#all_tickers = list(set(sp500_tickers + nasdaq100_tickers + russell1000_tickers))

# Function to get market capitalization
def get_market_caps(tickers):
    stock_data = []
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            market_cap = stock.info.get("marketCap", None)
            if market_cap:
                stock_data.append({"Symbol": ticker, "MarketCap": market_cap})
        except Exception as e:
            print(f"Error fetching {ticker}: {e}")
    return stock_data

# Fetch market caps
market_cap_data = get_market_caps(all_tickers)

# Convert to DataFrame and save
df = pd.DataFrame(market_cap_data)
df = df.sort_values(by="MarketCap", ascending=False)
df.to_csv("us_stock_market_caps.csv", index=False)

print("Stock market capitalization data saved to 'us_stock_market_caps.csv'.")

