import asyncio
import aiohttp
import pandas as pd
from datetime import datetime as dt
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import IntegrityError
import sqlite3
import calendar
import queue
import threading
import os
import multiprocessing
from multiprocessing import Manager
from collections import deque
from pandas.tseries.holiday import USFederalHolidayCalendar

RATE_LIMIT_PER_MIN = 1200
MAX_REQUESTS_PER_SECOND = RATE_LIMIT_PER_MIN // 60
semaphore = asyncio.Semaphore(MAX_REQUESTS_PER_SECOND)

SENTINEL = object()

# CONFIGURATION
API_KEY = ''
try:
    with open('/home/vpetla/alphavantage_token_file.txt', 'r') as f:
        API_KEY = f.read().strip()
    if not API_KEY:
        print("WARNING: API key file is empty.")
except Exception as e:
    print(f"ERROR: Could not read API key from file: {e}")

if not API_KEY:
    print("WARNING: Using placeholder API key. Please provide valid key in /home/vpetla/alphavantage_token_file.txt")
    API_KEY = 'YOUR_API_KEY'

# --- Async HTTP Request with Rate Limiting ---
async def fetch_data(session, symbol, date_str):
    url = f"https://www.alphavantage.co/query?function=HISTORICAL_OPTIONS&symbol={symbol}&date={date_str}&apikey={API_KEY}"
    async with semaphore:
        try:
            async with session.get(url, timeout=10) as response:
                data = await response.json()
                if 'Note' in data:
                    print(f"{symbol}: Rate limit hit. Retrying in 20s...")
                    await asyncio.sleep(20)
                    return await fetch_data(session, symbol, date_str)
                return date_str, data
        except Exception as e:
            print(f"{symbol}: Fetch failed on {date_str}: {e}")
            return date_str, None

# --- DB Writer Thread ---
def db_writer_worker(sql_engine, table_name, write_queue, shutdown_flag):
    conn = sql_engine.connect()
    buffer = []
    BATCH_SIZE = 1000

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
                write_batch(conn, table_name, buffer)
                buffer.clear()

        # Final flush
        if buffer:
            write_batch(conn, table_name, buffer)
    finally:
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
            conn.execute(sql, records)
    except Exception as e:
        print(f"[DB ERROR] Failed to write batch: {e}")

# --- Main Async Fetch and Insert Logic ---
async def fetch_and_insert_records(i, symbol, start_date, end_date, engine, table_name):
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
        tasks = [fetch_data(session, symbol, day.strftime('%Y-%m-%d')) for day in business_days]
        for coro in asyncio.as_completed(tasks):
            date_str, data = await coro
            if not data or 'data' not in data:
                print(f"No valid data for {symbol} on {date_str}")
                continue
            for opt in data['data']:
                try:
                    record = {
                        'contractID': opt['contractID'],
                        'expiration': dt.strptime(opt['expiration'], '%Y-%m-%d').date(),
                        'strike': float(opt.get('strike', -1)),
                        'type': opt['type'],
                        'last': float(opt.get('last', 0)),
                        'mark': float(opt.get('mark', 0)),
                        'bid': float(opt.get('bid', 0)),
                        'bid_size': int(opt.get('bid_size', 0)),
                        'ask': float(opt.get('ask', 0)),
                        'ask_size': int(opt.get('ask_size', 0)),
                        'volume': int(opt.get('volume', 0)),
                        'open_interest': int(opt.get('open_interest', 0)),
                        'date': dt.strptime(opt['date'], '%Y-%m-%d').date(),
                        'implied_volatility': float(opt.get('implied_volatility', 0)),
                        'delta': float(opt.get('delta', 0)),
                        'gamma': float(opt.get('gamma', 0)),
                        'theta': float(opt.get('theta', 0)),
                        'vega': float(opt.get('vega', 0)),
                        'rho': float(opt.get('rho', 0))
                    }
                    write_queue.put(record)
                except Exception as e:
                    print(f"Error parsing option data for {symbol} on {date_str}: {e}")

    # Shutdown
    write_queue.put(SENTINEL)
    write_queue.join()
    shutdown_flag.set()
    db_thread.join()

# --- Entry Point per Symbol ---
def process_symbol(sem, i, stk, cpu_affinity, request_times):
    if cpu_affinity is not None:
        try:
            os.sched_setaffinity(0, {cpu_affinity})
        except AttributeError:
            pass

    engine = create_engine("mysql+mysqlconnector://vpetla:petla123@10.89.45.21/US_Stocks_Options")
    inspector = inspect(engine)
    shutdown_flag = threading.Event()

    end_date = dt.now().date()
    table_name = f"STK{stk['bscs']['symbol']}"

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
        asyncio.run(fetch_and_insert_records(i, stk['bscs']['symbol'], start_date, end_date, engine, table_name))
    if sem:
        print(f"{i}: {stk['bscs']['symbol']}: Releasing semaphore")
        sem.release()

    engine.dispose()
    print(f"{i} : Finished processing {stk['bscs']['symbol']}")

if __name__ == "__main__":
    c = open_db_client()
    db = c['Stocks']
    collection = get_collection('US', db)

    ratelimit_event = threading.Event()
    ratelimit_event.set()

    num_cores = multiprocessing.cpu_count()
    num_cores = 30
    sem = multiprocessing.BoundedSemaphore(num_cores)
    manager = Manager()
    request_times = manager.list(deque(maxlen=75))
    i = 0
    num_cores = multiprocessing.cpu_count()
    sort = 1
    conditions = [ \
                    {"General.IsDelisted": False},\
                    {'General.Type':'Common Stock'},\
                    {"$or": [\
                                {'General.Exchange':{"$in":major_exchanges}},\
                                {"$and": [ \
                                            {'General.Exchange':{"$nin":major_exchanges}},\
                                            {'bscs.tracking':{'$exists':True}}, \
                                        ] \
                                },\
                            ]\
                    },\
                    {'Highlights.MarketCapitalization': {'$gte': 5 * Bn}},\
                ]

    stocks = db.US_Stocks.find({'$and':conditions}, no_cursor_timeout=True).sort([["Highlights.MarketCapitalization",-1]]).batch_size(10).allow_disk_use(True)
    print("Total non-bulk stocks: %r" %(stocks.count()))

    # Start logger
    threading.Thread(target=log_rate_forever, daemon=True).start()
    for i, stk in enumerate(stocks):
        sem.acquire()
        cpu_affinity = i % num_cores
        print("%d: Stock %r" %(i, stk['bscs']['symbol']))
        #p = multiprocessing.Process(target=process_symbol, args=(sem, i, stk, cpu_affinity, request_times))
        #p.start()
        process_symbol(sem, i, stk, cpu_affinity, request_times)
    stop_event.set()
    logger_thread.join()
        
    print("Finished processing all symbols.")
