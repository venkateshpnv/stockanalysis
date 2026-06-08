import aiohttp
import asyncio
import pandas as pd
import time
import math
import multiprocessing
import DB
from common import get_eod_token_id, pretty_print, list_difference, percent_change
from datastructures import *
from telegram import dataframe_to_image2, send_telegram_photo
from datetime import datetime as dt

DB.percent_change = percent_change
API_TOKEN = get_eod_token_id()
BASE_URL = 'https://eodhistoricaldata.com/api/real-time/'

# Example list of tickers from Market Cap ≥ $5B filter
large_cap_tickers = ['AAPL', 'MSFT', 'GOOG', 'NVDA', 'AMZN', 'META', 'TSLA', 'UNH', 'LLY', 'JPM']  # etc.
stocks = non_tech_stocks + selected_stocks + options_stocks
stocks = list(set(stocks))
#stocks = ['MARA', 'HOOD', 'SNOW']
#stocks = ['CBRS']

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
                if abs(change_percent) >= 3.0:
                    return {
                        "Symbol": ticker,
                        "Price": close,
                        "Change": round(change_percent, 2),
                        #"Change": f"{round(change, 2)}%",
                        "Open": data['open'],
                        "High": data['high'],
                        "Low": data['low'],
                        "Close": data['close'],
                        "Volume": data.get('volume', 0)
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

def get_last_three_values(s):
    try:
        values = s.split(',')
        if len(values) > 1:
            return ','.join(values[-5:])
        else:
            return ""
    except AttributeError:
        return ""

def trim_name(name):
    l = 14
    name = name.strip()
    if len(name) <= l:
        return name
    space_indices = [i for i, c in enumerate(name[:l + 1]) if c == ' ']
    if len(space_indices) >= 2:
        return name[:space_indices[1]]
    return name[:l]

def normalize_live_price_dataframe(df):
    if 'Close' not in df.columns or 'Adj Close' not in df.columns:
        print("Columns 'Close' or 'Adj Close' doesn't exist, available columns: %r" % (df.columns))
        return pd.DataFrame()

    df = df.copy()
    numeric_cols = ['Open', 'High', 'Low', 'Volume', 'Close', 'Adj Close']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    mask = (
        df['Close'].notna() &
        df['Adj Close'].notna() &
        (df['Close'] != 0) &
        (df['Close'] != df['Adj Close'])
    )
    ratio = df.loc[mask, 'Adj Close'] / df.loc[mask, 'Close']

    for col in ['Open', 'High', 'Low', 'Close']:
        if col in df.columns:
            df.loc[mask, col] = df.loc[mask, col] * ratio

    if 'Volume' in df.columns:
        df.loc[mask, 'Volume'] = df.loc[mask, 'Volume'] / ratio

    return df.dropna(subset=['High', 'Low', 'Adj Close'])

def fetch_price_dataframe(sym, mysql_engine):
    table_name = DB.get_symbol_table_name(sym)
    if not DB.mysql_exists_table(mysql_engine, table_name):
        print("%s: price table does not exist" % sym)
        return pd.DataFrame()

    yesterday = DB.get_previous_trading_day()
    query = "select Date, Open, High, Low, Volume, Close, `Adj Close` from {} where Date <= '{}'".format(
        table_name,
        yesterday.strftime("%Y-%m-%d")
    )
    df = DB.read_from_sql(query, mysql_engine)
    if df.empty:
        print("%s: empty price dataframe" % sym)
        return df
    return normalize_live_price_dataframe(df)

def append_live_price_row(df, result):
    today = DB.get_latest_trading_day()
    live_row = pd.DataFrame(
        {
            "Date": [today.strftime("%Y-%m-%d")],
            "Open": [result["Open"]],
            "High": [result["High"]],
            "Low": [result["Low"]],
            "Volume": [result.get("Volume", 0)],
            "Close": [result["Close"]],
            "Adj Close": [result["Close"]],
        },
        index=[pd.Timestamp(today)]
    )
    df = df[df.index.date < today.date()]
    df = pd.concat([df, live_row])
    return normalize_live_price_dataframe(df)

def ensure_tech_params_table(params_engine, table_name):
    if not DB.mysql_exists_table(params_engine, table_name):
        print("%s: creating technical params table" % table_name)
        DB.mysql_check_n_create_table(params_engine, table_name, primary_key=True)

    table_cols = DB.mysql_get_columns_from_engine(params_engine, table_name)
    missing_cols = list_difference([*tech_param_fields], table_cols)
    if len(missing_cols) > 0:
        print("%s: Adding missing technical columns: %r" % (table_name, missing_cols))
        DB.mysql_add_columns(params_engine, table_name, missing_cols, remove_spaces=False)

def update_live_technical_params_for_symbol(result, collection, mysql_engine, params_engine):
    sym = result["Symbol"]

    try:
        table_name = DB.get_symbol_table_name(sym)
        df = fetch_price_dataframe(sym, mysql_engine)
        if df.empty or len(df.index) <= 1:
            return

        ensure_tech_params_table(params_engine, table_name)
        df = append_live_price_row(df, result)
        print("%s: calculating SAR" % sym)
        DB.update_SAR_params(params_engine, collection, sym, df, db_update=False)
        print("%s: calculating RSI" % sym)
        DB.update_RSI_params(params_engine, collection, sym, df, db_update=False)
        #DB.update_field(collection, sym, "technicals.date", dt.combine(dt.now(), dt.min.time()))
    except Exception as e:
        print("%s: failed to update live technicals: %s" % (sym, str(e)))

def live_technical_worker(task_queue):
    c = None
    mysql_engine = None
    params_engine = None

    try:
        c = DB.open_db_client()
        db = c['Stocks']
        collection = DB.get_collection('US', db)
        mysql_engine = DB.open_sql_connection('localhost', 'vpetla', 'petla123', db='US_Stocks')
        params_engine = DB.open_sql_connection('localhost', 'vpetla', 'petla123', db='US_Tech_Params')

        while True:
            result = task_queue.get()
            if result is None:
                break
            update_live_technical_params_for_symbol(result, collection, mysql_engine, params_engine)
    finally:
        if mysql_engine is not None:
            DB.close_sql_connection(mysql_engine)
        if params_engine is not None:
            DB.close_sql_connection(params_engine)
        if c is not None:
            DB.close_db_client(c)

def update_live_technical_params(results):
    if len(results) == 0:
        return

    num_processes = min(DB.num_cores, len(results))
    task_queue = multiprocessing.Queue()
    processes = [
        multiprocessing.Process(target=live_technical_worker, args=(task_queue,))
        for _ in range(num_processes)
    ]
    print("Updating live technicals with %d parallel processes" % num_processes)

    for process in processes:
        process.start()

    for result in results:
        task_queue.put(result)

    for _ in processes:
        task_queue.put(None)

    for process in processes:
        process.join()

    task_queue.close()
    task_queue.join_thread()

def safe_round(value, digits=2, default=0):
    try:
        if value is None:
            return default
        if isinstance(value, float) and math.isnan(value):
            return default
        return round(value, digits)
    except:
        return default

def safe_percent(value):
    return safe_round(safe_round(value, 6) * 100)

def build_live_uptrend_df(results, collection):
    fields = {
        'Name': '',
        'Trend': int(),
        'Prev_Trend': int(),
        'Price': float(),
        'Chg': float(),
        'Trade': float(),
        'RSI': float(),
        'MinRSI': float(),
        'DMRSI': int(),
        'Slope': float(),
        'Trend_Sequence_Change': '',
        'Prev_Trend_Change': float(),
        'Cur_Trend_Change': float(),
        'MCap': float()
    }
    df = pd.DataFrame(fields, index=[])

    for result in results:
        sym = result["Symbol"]
        stocks = collection.find({'bscs.symbol': sym})
        if stocks.count() == 0:
            continue

        instrument = stocks[0]
        try:
            sar = instrument['technicals']['sar']
            rsi = instrument['technicals']['rsi']
            trend = sar['ta_psar_trend']
            days_from_minrsi = (dt.now().date() - rsi['60day_min_price_date'].date()).days

            price = safe_round(result.get('Price'))
            avg_volume = safe_round(instrument.get('price_change', {}).get('avg_volume', 0), 2)
            avg_trade = safe_round((price * avg_volume) / 1000000)
            mcap = safe_round(instrument.get('Highlights', {}).get("MarketCapitalizationMln", 0) / 1000)

            df.loc[sym] = [
                instrument.get('General', {}).get('Name', sym),
                trend,
                sar.get('ta_psar_prev_trend', 0),
                price,
                safe_round(result.get('Change')),
                avg_trade,
                safe_round(rsi.get('latest')),
                safe_round(rsi.get('with_60day_min')),
                days_from_minrsi,
                safe_round(rsi.get('5day_slope'), 3),
                str(sar.get('ta_psar_trend_pcnt_change', '')),
                safe_percent(sar.get('ta_psar_prev_trend_price_change')),
                safe_percent(sar.get('ta_psar_cur_trend_price_change')),
                mcap,
            ]
        except Exception as e:
            print("%s: failed to add uptrend row: %s" % (sym, str(e)))

    return df

def sort_like_get_uptrend(uptrend_df):
    if len(uptrend_df) == 0:
        return uptrend_df

    trend1 = uptrend_df[(uptrend_df['Trend'] == 1) & ((uptrend_df['Prev_Trend_Change'] < -10) | (uptrend_df['Prev_Trend'] <= -14))]
    trend1 = trend1[trend1.Trade >= 60]
    trend1 = trend1.sort_values(by='Prev_Trend_Change', ascending=True)

    trend3 = uptrend_df[uptrend_df.Cur_Trend_Change <= -10]
    trend3 = trend3[trend3.Trade >= 60]
    trend3 = trend3.sort_values(by=['Cur_Trend_Change'], ascending=True)

    cdf = pd.concat([trend1, trend3])
    cdf.drop_duplicates(keep=False, inplace=True)
    return cdf

def send_live_uptrend_image(results, collection):
    uptrend_df = build_live_uptrend_df(results, collection)
    uptrend_df = sort_like_get_uptrend(uptrend_df)
    if len(uptrend_df) == 0:
        return

    uptrend_df['Trend_Sequence_Change'] = uptrend_df['Trend_Sequence_Change'].apply(get_last_three_values)
    uptrend_df.rename(
        columns={
            'Trend': 'Tr',
            'Prev_Trend_Change': 'PTChg',
            'Cur_Trend_Change': 'CTChg',
            'Trend_Sequence_Change': 'Tr_Seq'
        },
        inplace=True
    )
    uptrend_df['Name'] = uptrend_df['Name'].apply(trim_name)
    uptrend_df['Sym'] = uptrend_df.index
    uptrend_df['PTChg'] = uptrend_df['PTChg'].astype(str) + '%'
    uptrend_df['CTChg'] = uptrend_df['CTChg'].astype(str) + '%'
    uptrend_df['MCap'] = uptrend_df['MCap'].astype(str) + 'Bn'
    uptrend_df['Trade'] = uptrend_df['Trade'].astype(str) + 'Mn'
    uptrend_df['Chg'] = uptrend_df['Chg'].astype(str) + '%'

    count = 15
    for start in range(0, len(uptrend_df), count):
        df = uptrend_df.iloc[start:start + count]
        if len(df) == 0:
            break
        image_path = dataframe_to_image2(
            df[['Sym', 'Name', 'Price', 'Chg', 'Tr', 'MinRSI', 'DMRSI', 'Slope', 'Tr_Seq', 'Trade', 'MCap']],
            banner="Live Uptrend: " + str(dt.now().strftime('%Y-%m-%d %I:%M %p'))
        )
        send_telegram_photo(image_path, token='stock_notify')

if __name__ == '__main__':

    c = None
    results = []
    i = -1

    try:
        print("Fetching live prices with rate limit handling...")
        results = asyncio.run(fetch_all_prices(stocks))
        if len(results) > 0:
            print("Updating live tech params")
            update_live_technical_params(results)

            c = DB.open_db_client()
            db = c['Stocks']
            collection = DB.get_collection('US', db)

            print("Preparing telegram df")
            for i, r in enumerate(results):
                results[i]['Name'] = results[i].get('Symbol', '')
                results[i]['MCap'] = ''
                results[i]['Trend'] = ''
                stk = collection.find({'bscs.symbol':r['Symbol']})
                if stk.count() > 0:
                    stk = stk[0]
                    if 'technicals' in stk.keys() and 'sar' in stk['technicals'].keys():
                        results[i]['Trend'] = stk['technicals']['sar']['ta_psar_trend_pcnt_change']
                        results[i]['Trend'] = ",".join(results[i]['Trend'].split(',')[-4:])
                        if 'Highlights' in stk.keys() and 'MarketCapitalizationMln' in stk['Highlights'].keys():
                            results[i]['MCap'] = str(round(stk['Highlights']["MarketCapitalizationMln"]/1000,2)) + 'Bn'
                        results[i]['Name'] = stk['bscs']['name']
                        results[i]['Name'] = " ".join(results[i]['Name'].split(' ')[:2])
            df = pd.DataFrame(results)
            df = df[['Symbol', 'Name', 'Price', 'Change', 'MCap', 'Trend']]
            df = df.sort_values(by='Change', ascending=False)
            df['Change'] = df['Change'].astype(str) + '%'
            if not df.empty:
                image_path = dataframe_to_image2(df, banner="Live Price Change: " + str(dt.now().strftime('%Y-%m-%d %I:%M %p')) )
                send_telegram_photo(image_path, token='strong_buy_pure')
            send_live_uptrend_image(results, collection)
    except Exception as E:
        if 0 <= i < len(results):
            print("i: %d, results[i]: %r, Error: %s" %(i, results[i], str(E)))
        else:
            print("Live price change error: %s" %(str(E)))
    finally:
        if c is not None:
            DB.close_db_client(c)
