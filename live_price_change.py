import aiohttp
import asyncio
import pandas as pd
import time
from common import get_eod_token_id, pretty_print
from datastructures import *
import DB
from telegram import dataframe_to_image2, send_telegram_photo
from datetime import datetime as dt

API_TOKEN = get_eod_token_id()
BASE_URL = 'https://eodhistoricaldata.com/api/real-time/'

# Example list of tickers from Market Cap ≥ $5B filter
large_cap_tickers = ['AAPL', 'MSFT', 'GOOG', 'NVDA', 'AMZN', 'META', 'TSLA', 'UNH', 'LLY', 'JPM']  # etc.
stocks = non_tech_stocks + selected_stocks + options_stocks
stocks = list(set(stocks))

async def fetch_price(session, ticker):
    url = f"{BASE_URL}{ticker}?api_token={API_TOKEN}&fmt=json"
    while True:
        async with session.get(url) as response:
            headers = response.headers
            rate_remaining = int(headers.get("X-RateLimit-Remaining", 1))
            rate_reset = int(headers.get("X-RateLimit-Reset", 1))

            if response.status == 429 or rate_remaining == 0:
                print(f"[{ticker}] Rate limit hit. Waiting {rate_reset + 1}s to retry...")
                await asyncio.sleep(rate_reset + 1)
                continue  # Retry this request after wait

            if response.status != 200:
                print(f"[{ticker}] Failed with status {response.status}")
                return None

            data = await response.json()
            try:
                close = data.get("close")
                prev_close = data.get("previousClose")
                change_percent = ((close - prev_close) / prev_close) * 100
                if abs(change_percent) >= 5.0:
                    return {
                        "Symbol": ticker,
                        "Price": close,
                        "Change": round(change_percent, 2)
                        #"Change": f"{round(change, 2)}%"
                    }
            except:
                return None
            return None

async def fetch_all_prices(tickers):
    results = []
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_price(session, ticker) for ticker in tickers]
        for future in asyncio.as_completed(tasks):
            try:
                result = await future
                if result:
                    results.append(result)
            except Exception as e:
                print(f"Error: {e}")
    return results

if __name__ == '__main__':

    c = DB.open_db_client()
    db = c['Stocks']
    collection = DB.get_collection('US', db)

    try:
        print("Fetching live prices with rate limit handling...")
        results = asyncio.run(fetch_all_prices(stocks))
        if len(results) > 0:
            for i, r in enumerate(results):
                stk = collection.find({'bscs.symbol':r['Symbol']})
                if stk.count() > 0:
                    stk = stk[0]
                    if 'technicals' in stk.keys() and 'sar' in stk['technicals'].keys():
                        results[i]['Trend'] = stk['technicals']['sar']['ta_psar_trend_pcnt_change']
                        results[i]['Trend'] = ",".join(results[i]['Trend'].split(',')[-4:])
                        if 'Highlights' in stk.keys() and 'MarketCapitalizationMln' in stk['Highlights'].keys():
                            results[i]['MCap'] = str(round(stk['Highlights']["MarketCapitalizationMln"]/1000,2)) + 'Bn'
                        results[i]['Name'] = stk['General']['Name']
                        results[i]['Name'] = " ".join(results[i]['Name'].split(' ')[:2])
            df = pd.DataFrame(results)
            df = df[['Symbol', 'Name', 'Price', 'Change', 'MCap', 'Trend']]
            df = df.sort_values(by='Change', ascending=False)
            df['Change'] = df['Change'].astype(str) + '%'
            if not df.empty:
                image_path = dataframe_to_image2(df, banner="Live Price Change: " + str(dt.now().strftime('%Y-%m-%d %I:%M %p')) )
                send_telegram_photo(image_path, token='strong_buy_pure')
    finally:
        DB.close_db_client(c)

