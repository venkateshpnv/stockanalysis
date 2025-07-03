import asyncio
import aiohttp
import pandas as pd
from datetime import datetime as dt
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import IntegrityError
import sqlite3
import os
import threading
from pandas.tseries.holiday import USFederalHolidayCalendar
from collections import deque
import queue

API_KEY = "YOUR_API_KEY"
RATE_LIMIT_PER_MIN = 1200
MAX_REQUESTS_PER_SECOND = RATE_LIMIT_PER_MIN // 60
semaphore = asyncio.Semaphore(MAX_REQUESTS_PER_SECOND)

SENTINEL = object()

# --- Async HTTP Request with Rate Limiting ---
async def fetch_data(i, session, symbol, date_str):
    zero_records_cnt = 0
    url = f"https://www.alphavantage.co/query?function=HISTORICAL_OPTIONS&symbol={symbol}&date={date_str}&apikey={API_KEY}"
    async with semaphore:
        try:
            async with session.get(url, timeout=10) as response:
                if response.status != 200:
                    print(f"{symbol}: HTTP {response.status} on {date_str}")
                    return date_str, None
                data = await response.json()
                #if 'Note' in data:
                if 'Note' in data or 'Information' in data:
                    print(f"{symbol}: Rate limit hit. Retrying in 20s...")
                    await asyncio.sleep(20)
                    return await fetch_data(i, session, symbol, date_str)
                if 'data' in data:
                    num_records = len(data['data'])
                    print(f"{i}: {dt.now()}: {symbol}: {date_str}, num_records: {num_records}")

                return date_str, data
        except Exception as e:
            print(f"{symbol}: Fetch failed on {date_str}: {e}")
            return date_str, None

# --- DB Writer Thread ---
def db_writer_worker(sql_engine, table_name, write_queue, shutdown_flag):
    conn = sql_engine.connect()
    buffer = []
    BATCH_SIZE = 1000

    print(f"db_write_worker started for {table_name}")
    try:
        while not shutdown_flag.is_set() or not write_queue.empty():
            try:
                record = write_queue.get(timeout=1)
                if record is SENTINEL:
                    write_queue.task_done()
                    break
                buffer.append(record)
                write_queue.task_done()
            except queue.Empty:
                pass

            if len(buffer) >= BATCH_SIZE:
                # ⏱ Start timing
                start_time = time.perf_counter()

                write_batch(conn, table_name, buffer)

                end_time = time.perf_counter()
                duration = end_time - start_time
                batch_size = len(buffer)

                # 💡 Track stats
                total_inserted += batch_size
                total_duration += duration

                print(f"[{table_name}] Inserted {batch_size} rows in {duration:.4f} seconds "
                      f"→ {batch_size / duration:.2f} rows/sec")

                buffer.clear()

        # Final flush
        if buffer:
            write_batch(conn, table_name, buffer)
    finally:
        print(f"db_write_worker completed for {table_name}")
        conn.close()

def write_batch(conn, table_name, records):
    if not records:
        return
    keys = records[0].keys()
    placeholders = ', '.join(f":{col}" for col in keys)
    columns = ', '.join(f"`{col}`" for col in keys)
    sql = text(f"INSERT IGNORE INTO `{table_name}` ({columns}) VALUES ({placeholders})")
    try:
        with conn.begin():
            print(f"Writing {len(records)} to {table_name}")
            conn.execute(sql, records)
    except Exception as e:
        print(f"[DB ERROR] Failed to write batch: {e}")

# --- Fetch and Insert for One Symbol ---
async def fetch_and_insert_one(i, symbol, start_date, end_date, engine, table_name):
    shutdown_flag = threading.Event()
    write_queue = queue.Queue()

    # Start DB writer thread
    db_thread = threading.Thread(target=db_writer_worker, args=(engine, table_name, write_queue, shutdown_flag))
    db_thread.start()

    # Get business days
    cal = USFederalHolidayCalendar()
    holidays = cal.holidays(start=start_date, end=end_date).to_pydatetime()
    business_days = pd.date_range(start=start_date, end=end_date, freq='B').difference(pd.to_datetime(holidays))

    async with aiohttp.ClientSession() as session:
        zero_count = 0
        tasks = [fetch_data(i, session, symbol, day.strftime('%Y-%m-%d')) for day in business_days]
        for coro in asyncio.as_completed(tasks):
            date_str, data = await coro
            if not data or 'data' not in data:
                print(f"{i}: No valid data for {symbol} on {date_str}")
                zero_count += 1
                if zero_count >= 5:
                    print(f"{i}: {symbol}: 5 consecutive empty responses. Stopping further fetches.")
                    break
                continue
            elif len(data['data']) == 0:
                zero_count += 1
                print(f"{i}: {symbol}: 0 records on {date_str}. Zero count: {zero_count}")
                if zero_count >= 5:
                    print(f"{i}: {symbol}: 5 consecutive zero-record days. Stopping fetch.")
                    break
                continue
            else:
                zero_count = 0

            num_records = len(data['data'])
            print(f"{i}: {dt.now()}: {symbol}: {date_str}, num_records: {num_records}")

            for opt in data['data']:
                try:
                    try:
                        strike = float(opt['strike'])
                    except Exception as e:
                        print(f"Error parsing strike for {symbol} on {date_str}, setting -1: {e}")
                        strike = -1
                    try:
                        last = float(opt.get('last', 0))
                    except Exception as e:
                        print(f"Error parsing last for {symbol} on {date_str}, setting -1: {e}")
                        last = -1
                    try:
                        mark = float(opt.get('mark', 0))
                    except Exception as e:
                        print(f"Error parsing mark for {symbol} on {date_str}, setting -1: {e}")
                        mark = -1
                    try:
                        bid = float(opt.get('bid', 0))
                    except Exception as e:
                        print(f"Error parsing bid for {symbol} on {date_str}, setting -1: {e}")
                        bid = -1
                    try:
                        bid_size = int(opt.get('bid_size', 0))
                    except Exception as e:
                        print(f"Error parsing bid_size for {symbol} on {date_str}, setting -1: {e}")
                        bid_size = -1
                    try:
                        ask = float(opt.get('ask', 0))
                    except Exception as e:
                        print(f"Error parsing ask for {symbol} on {date_str}, setting -1: {e}")
                        ask = -1
                    try:
                        ask_size = int(opt.get('ask_size', 0))
                    except Exception as e:
                        print(f"Error parsing ask_size for {symbol} on {date_str}, setting -1: {e}")
                        ask_size = -1
                    try:
                        volume = int(opt.get('volume', 0))
                    except Exception as e:
                        print(f"Error parsing volume for {symbol} on {date_str}, setting -1: {e}")
                        volume = -1
                    try:
                        open_interest = int(opt.get('open_interest', 0))
                    except Exception as e:
                        print(f"Error parsing open_interest for {symbol} on {date_str}, setting -1: {e}")
                        open_interest = -1
                    try:
                        implied_volatility = float(opt.get('implied_volatility', 0))
                    except Exception as e:
                        print(f"Error parsing implied_volatility for {symbol} on {date_str}, setting -1: {e}")
                        implied_volatility = -1
                    try:
                        delta = float(opt.get('delta', 0))
                    except Exception as e:
                        print(f"Error parsing delta for {symbol} on {date_str}, setting -1: {e}")
                        delta = -1
                    try:
                        gamma = float(opt.get('gamma', 0))
                    except Exception as e:
                        print(f"Error parsing gamma for {symbol} on {date_str}, setting -1: {e}")
                        gamma = -1
                    try:
                        theta = float(opt.get('theta', 0))
                    except Exception as e:
                        print(f"Error parsing theta for {symbol} on {date_str}, setting -1: {e}")
                        theta = -1
                    try:
                        vega = float(opt.get('vega', 0))
                    except Exception as e:
                        print(f"Error parsing vega for {symbol} on {date_str}, setting -1: {e}")
                        vega = -1
                    try:
                        rho = float(opt.get('rho', 0))
                    except Exception as e:
                        print(f"Error parsing rho for {symbol} on {date_str}, setting -1: {e}")
                        rho = -1

                    record = {
                        'contractID': opt['contractID'],
                        #'symbol': opt['symbol'],
                        'expiration': dt.strptime(opt['expiration'], '%Y-%m-%d').date(),
                        'strike': strike,
                        'type': opt['type'],
                        'last': last,
                        'mark': mark,
                        'bid': bid,
                        'bid_size': bid_size,
                        'ask': ask,
                        'ask_size': ask_size,
                        'volume': volume,
                        'open_interest': open_interest,
                        'date': dt.strptime(opt['date'], '%Y-%m-%d').date(),
                        'implied_volatility': implied_volatility,
                        'delta': delta,
                        'gamma': gamma,
                        'theta': theta,
                        'vega': vega,
                        'rho': rho
                    }

                    #record = {
                    #    'contractID': opt['contractID'],
                    #    'expiration': dt.strptime(opt['expiration'], '%Y-%m-%d').date(),
                    #    'strike': float(opt.get('strike', -1)),
                    #    'type': opt['type'],
                    #    'last': float(opt.get('last', 0)),
                    #    'mark': float(opt.get('mark', 0)),
                    #    'bid': float(opt.get('bid', 0)),
                    #    'bid_size': int(opt.get('bid_size', 0)),
                    #    'ask': float(opt.get('ask', 0)),
                    #    'ask_size': int(opt.get('ask_size', 0)),
                    #    'volume': int(opt.get('volume', 0)),
                    #    'open_interest': int(opt.get('open_interest', 0)),
                    #    'date': dt.strptime(opt['date'], '%Y-%m-%d').date(),
                    #    'implied_volatility': float(opt.get('implied_volatility', 0)),
                    #    'delta': float(opt.get('delta', 0)),
                    #    'gamma': float(opt.get('gamma', 0)),
                    #    'theta': float(opt.get('theta', 0)),
                    #    'vega': float(opt.get('vega', 0)),
                    #    'rho': float(opt.get('rho', 0))
                    #}
                    write_queue.put(record)
                except Exception as e:
                    print(f"Error parsing option data for {symbol} on {date_str}: {e}")

    # Shutdown
    write_queue.put(SENTINEL)
    write_queue.join()
    shutdown_flag.set()
    db_thread.join()

# --- Entry Point: All Symbols ---
async def main():
    from DB import open_db_client, get_collection
    major_exchanges = ["NASDAQ", "NYSE"]
    Bn = 1000000000

    c = open_db_client()
    db = c['Stocks']
    collection = get_collection('US', db)

    conditions = [
        {"General.IsDelisted": False},
        {'General.Type': 'Common Stock'},
        {"$or": [
            {'General.Exchange': {"$in": major_exchanges}},
            {"$and": [
                {'General.Exchange': {"$nin": major_exchanges}},
                {'bscs.tracking': {'$exists': True}},
            ]},
        ]},
        {"$or":[\
                    {'General.Sector': {"$in": ['Technology', 'Communication Services', ]}},\
                    {"$and": [ \
                                {'General.Sector': {"$nin": ['Technology', 'Communication Services', ]}},\
                                {'General.Code' : {"$in": non_tech_stocks}},\
                            ]\
                    },\
                    {"$and": [ \
                                {'General.Code' : {"$in": selected_stocks}},\
                            ]\
                    },\
                ]\
        },\
        {'Highlights.MarketCapitalization': {'$gte': 5 * Bn}},
    ]

    stocks = db.US_Stocks.find({'$and': conditions}, no_cursor_timeout=True).sort([("Highlights.MarketCapitalization", -1)]).batch_size(10).allow_disk_use(True)
    print("Total non-bulk stocks: %r" %(stocks.count()))
    max_connections = 1000
    tasks = []
    semaphore_limit = asyncio.Semaphore(max_connections )  # limits concurrent fetch_and_insert_one tasks

    engine = create_engine(
        "mysql+mysqlconnector://vpetla:petla123@10.89.45.31/US_Stocks_Options",
        pool_size=max_connections,
        max_overflow=5,
        pool_timeout=30,
        pool_recycle=1800
    )

    for i, stk in enumerate(stocks):
        #engine = create_engine("mysql+mysqlconnector://vpetla:petla123@10.89.45.21/US_Stocks_Options")
        inspector = inspect(engine)

        print("%d: Stock %r" %(i, stk['bscs']['symbol']))
        table_name = f"STK{stk['bscs']['symbol']}"
        table_name = table_name.replace("-", "_")
        end_date = dt.now().date()

        if table_name not in inspector.get_table_names():
            ipo_date = dt(2008, 1, 1).date()
            if 'General' in stk and 'IPODate' in stk['General']:
                try:
                    ipo_date = dt.strptime(stk['General']['IPODate'], "%Y-%m-%d").date()
                    if ipo_date < dt(2008, 1, 1).date():
                        ipo_date = dt(2008, 1, 1).date()
                except:
                    ipo_date = dt(2008, 1, 1).date()
            start_date = ipo_date
        else:
            with engine.connect() as conn:
                latest_date = conn.execute(text(f"SELECT MAX(date) FROM {table_name}")).scalar()
            ipo_date = dt(2008, 1, 1).date()
            if 'General' in stk and 'IPODate' in stk['General']:
                try:
                    ipo_date = dt.strptime(stk['General']['IPODate'], "%Y-%m-%d").date()
                    if ipo_date < dt(2008, 1, 1).date():
                        ipo_date = dt(2008, 1, 1).date()
                except:
                    ipo_date = dt(2008, 1, 1).date()
            start_date = latest_date if latest_date else ipo_date

        print(f"{i}:{table_name} : start_date: {start_date}")
        if start_date <= end_date:
            async def guarded(i, symbol, start_date, end_date, table_name):
                async with semaphore_limit:
                    await fetch_and_insert_one(i, symbol, start_date, end_date, engine, table_name)

            tasks.append(guarded(i, stk['bscs']['symbol'], start_date, end_date, table_name))
            #tasks.append(fetch_and_insert_one(i, stk['bscs']['symbol'], start_date, end_date, engine, table_name))

    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())

