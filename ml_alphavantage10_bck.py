import requests
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from datetime import datetime as dt, timedelta

from sqlalchemy.types import Enum # Import Enum
from sqlalchemy.dialects.mysql import DECIMAL
from sqlalchemy import (
    create_engine, Column, String, Float, Date, Integer, MetaData, Table, inspect, text, Date, DECIMAL, Enum, Integer, Float, PrimaryKeyConstraint, Index
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.engine import reflection

import sqlite3
import pymysql

import sys

import time
import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar
import numpy as np
import multiprocessing
import os
import json
from pathlib import Path
from multiprocessing import Lock
from collections import deque
from multiprocessing import Manager
from DB import *
import DB
from datastructures import *
import queue
import warnings

# Suppress all warnings
warnings.filterwarnings('ignore')

# Constants
RATE_LIMIT = 1200
TIME_WINDOW = 60  # seconds
RATE_FILE = Path("/tmp/alpha_vantage_rate.json")

# CONFIGURATION
API_KEY = ''
#FREE API KEY
# API_KEY = 'T42G3VDN11BAGNWD'

# 75 calls per min key
# NEW KEY
# API_KEY = 'CXBLO1SJ3VKJJ0FN'

#PREMIUM KEY 'QV59YK6LOZIOA3KL'

# petlanvenkatesh free key
#API KEY = 'T1ODHXVLSD93IMYO'
# Premium API KEY = 'EJBQZ1CMTM557L6E'

try:
    with open('/home/vpetla/alphavantage_token_file.txt', 'r') as f:
        API_KEY = f.read().strip()
    if not API_KEY:
        print("WARNING: API key file is empty.")
except Exception as e:
    print(f"ERROR: Could not read API key from file: {e}")

## 75 calls per min key
#API_KEY = 'QV59YK6LOZIOA3KL'
#RATE_LIMIT = 70
#RATE_FILE = Path("/tmp/alpha_vantage_rate_75.json")

if not API_KEY:
    print("WARNING: Using placeholder API key. Please provide valid key in /home/vpetla/alphavantage_token_file.txt")
    API_KEY = 'YOUR_API_KEY'

SELECTED_STOCKS = ['AAPL', 'AMZN', 'MSFT']
MAX_FAIL_COUNT = 5
Bn = 1000000000
major_exchanges = ["NASDAQ", "NYSE"]

EXPECTED_COLUMNS = {
    'contractID': String(30),
    #'symbol': String(10),
    'expiration': Date,
    'strike': DECIMAL(10, 2),
    'type': Enum('CALL', 'PUT'),
    'last': DECIMAL(10, 2),
    'mark': DECIMAL(10, 2),
    'bid': DECIMAL(10, 2),
    'bid_size': Integer,
    'ask': DECIMAL(10, 2),
    'ask_size': Integer,
    'volume': Integer,
    'open_interest': Integer,
    'date': Date,
    'implied_volatility': Float,
    'delta': Float,
    'gamma': Float,
    'theta': Float,
    'vega': Float,
    'rho': Float,
}

PRIMARY_KEYS = ['contractID', 'date']

# Global lock shared across processes
rate_lock = Lock()

def get_session_with_retries():
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def read_value_from_file(file_path):
    try:
        with open(file_path, 'r') as f:
            return int(f.read().strip())
    except Exception as e:
        print(f"Error reading value: {e}")
        return None

#ratelimit_event = threading.Event()
def log_request(sym, ratelimit_event):
    with rate_lock:
        now = time.time()

        # Read current timestamps
        if RATE_FILE.exists():
            with open(RATE_FILE, "r") as f:
                try:
                    timestamps = json.load(f)
                except json.JSONDecodeError:
                    timestamps = []
        else:
            timestamps = []

        # Remove timestamps older than TIME_WINDOW
        timestamps = [ts for ts in timestamps if now - ts < TIME_WINDOW]

        # If limit exceeded, wait
        if len(timestamps) >= RATE_LIMIT:
            wait_time = TIME_WINDOW - (now - min(timestamps)) + 3
            print(f"[^^^^^^^^^^^^^^^^^^^^^^^^^^^^{sym} : PID {os.getpid()}] Rate limit hit. Sleeping {wait_time:.2f}s")
            ratelimit_event.clear()
            time.sleep(wait_time)
            print(f"[^^^^^^^^^^^^^^^^^^^^^^^^^^^^{sym} : PID {os.getpid()}] Rate limit wait over. Resuming")
            ratelimit_event.set()
            with open(RATE_FILE, "w") as f:
                pass
            now = time.time()
            #timestamps = [ts for ts in timestamps if now - ts < TIME_WINDOW]
            timestamps = []

        # Add new timestamp and write back
        timestamps.append(now)
        with open(RATE_FILE, "w") as f:
            json.dump(timestamps, f)

stop_event = threading.Event()
def log_rate_forever():
    while not stop_event.is_set():
        time.sleep(60)
        if RATE_FILE.exists():
            with open(RATE_FILE, "r") as f:
                try:
                    timestamps = json.load(f)
                    now = time.time()
                    timestamps = [ts for ts in timestamps if now - ts < TIME_WINDOW]
                    print(f"[MONITOR] Requests in last {TIME_WINDOW}s: {len(timestamps)}")
                except json.JSONDecodeError:
                    pass


def open_sql_connection(host, user, password, db):
    try:
        conn = pymysql.connect(
            host=host,
            user=user,
            password=password,
            db=db,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
        )
        engine = create_engine(f"mysql+pymysql://{user}:{password}@{host}/{db}", pool_pre_ping=True)
        return engine
    except pymysql.MySQLError as e:
        print(f"Error connecting to MySQL: {e}")
        return None

#sql_engine = open_sql_connection('10.89.45.208', 'vpetla', 'petla123', db='US_Stocks_Options')
#metadata = MetaData()
#inspector = inspect(sql_engine)

def create_and_check_indexes(engine, table_name):
    try:
        # 1. Establish database connection
        metadata = MetaData()
        metadata.bind = engine

        # 2. Define the table structure in SQLAlchemy
        #    It's important to accurately reflect the table's schema.
        table = Table(
            table_name, metadata,
            Column('contractID', String(30), primary_key=True),
            Column('expiration', Date),
            Column('strike', DECIMAL(10, 2)),
            Column('type', Enum('CALL', 'PUT')),
            Column('last', DECIMAL(10, 2)),
            Column('mark', DECIMAL(10, 2)),
            Column('bid', DECIMAL(10, 2)),
            Column('bid_size', Integer),
            Column('ask', DECIMAL(10, 2)),
            Column('ask_size', Integer),
            Column('volume', Integer),
            Column('open_interest', Integer),
            Column('date', Date, primary_key=True),
            Column('implied_volatility', Float),
            Column('delta', Float),
            Column('gamma', Float),
            Column('theta', Float),
            Column('vega', Float),
            Column('rho', Float),
            # Define the primary key explicitly as it's composite
            PrimaryKeyConstraint('contractID', 'date', name='PRIMARY')
        )

        # 3. Define the desired indexes
        #    Note: SQLAlchemy's Index object can be used to define indexes
        #    that will be created on the database.
        desired_indexes = [
            # Index on expiration date
            Index('idx_contractID_expiration', table.c.contractID, table.c.expiration),
            # Composite index on expiration, type
            Index('idx_expiration_type', table.c.expiration, table.c.type),
            # Index on date (even though it's part of PK, a separate index might help specific queries)
            Index('idx_date', table.c.date),
            ## Index on volume
            #Index('idx_volume', table.c.volume),
            ## Index on open_interest
            #Index('idx_open_interest', table.c.open_interest)
        ]

        # 4. Inspect existing indexes on the table
        inspector = reflection.Inspector.from_engine(engine)
        existing_indexes = inspector.get_indexes(table_name)
        existing_index_names = {idx['name'] for idx in existing_indexes}

        #print(f"Existing indexes on {table_name}: {existing_index_names}")

        # 5. Check and create missing indexes
        with engine.connect() as connection:
            for idx in desired_indexes:
                if idx.name not in existing_index_names:
                    #print(f"{table_name}: Creating index '{idx.name}' on columns: {[c.name for c in idx.columns]}")
                    try:
                        # Use if_not_exists=True to prevent errors if the index somehow appeared
                        # between inspection and creation, or if the script is run multiple times.
                        idx.create(connection)
                        #idx.create(connection, checkfirst=True)
                        print(f"Index '{idx.name}' created successfully.")
                    except Exception as e:
                        print(f"Error creating index '{idx.name}': {e}")
                #else:
                #   print(f"Index '{idx.name}' already exists. Skipping creation.")

    except Exception as e:
        print(f"An error occurred during index creation process: {e}")

SENTINEL = None
BATCH_SIZE = 10000

def db_writer_worker_old(sql_engine, table_name, write_queue, shutdown_flag):
    #conn = sql_engine.connect()
    while not shutdown_flag.is_set() or not write_queue.empty():
        try:
            #qsize = write_queue.qsize()
            #if qsize > 69999:
            #    print(f"{table_name}: Queue size:", qsize)
            record = write_queue.get(timeout=1)  # Wait for 1 sec
            if record is SENTINEL:
                write_queue.task_done()
                break
        except queue.Empty:
            continue  # No record to write
        with sql_engine.begin() as conn:
            try:
                placeholders = ', '.join(f":{col}" for col in record)
                columns = ', '.join(f"`{col}`" for col in record)
                sql = text(f"""
                    INSERT IGNORE INTO `{table_name}` ({columns})
                    VALUES ({placeholders})
                """)
                # OPTIMIZE TABLE STKMSFT;
                #print(record)
                conn.execute(sql, record)
            except IntegrityError as e:
                print(f"{table_name} : Record already exist")
            except sqlite3.OperationalError as e:
                #conn.rollback()
                print(f"{table_name} : Operational error like connection lost etc")
                sys.exit(1)
            except sqlite3.ProgrammingError as e:
                #conn.rollback()
                print(f"{table_name} : Programatical error")
                sys.exit(1)
            except Exception as e:
                #conn.rollback()
                print(f"{table_name} : DB write failed: {e}")
                sys.exit(1)
            finally:
                #print(f"{table_name}: closing write queue")
                write_queue.task_done()
    #conn.close()

def db_writer_worker(sql_engine, table_name, write_queue, shutdown_flag, ratelimit_event):
    conn = sql_engine.connect()
    buffer = []
    total_inserted = 0
    total_duration = 0.0

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

            #if len(buffer) >= BATCH_SIZE:# or (shutdown_flag.is_set() and buffer):
            if len(buffer) >= BATCH_SIZE or (ratelimit_event.is_set() is False and buffer):
                try:
                    keys = buffer[0].keys()
                    placeholders = ', '.join(f":{col}" for col in keys)
                    columns = ', '.join(f"`{col}`" for col in keys)

                    sql = text(f"""
                        INSERT IGNORE INTO `{table_name}` ({columns})
                        VALUES ({placeholders})
                    """)

                    # ⏱ Start timing
                    start_time = time.perf_counter()

                    with conn.begin():  # One transaction per batch
                        conn.execute(sql, buffer)

                    end_time = time.perf_counter()
                    duration = end_time - start_time
                    batch_size = len(buffer)

                    # 💡 Track stats
                    total_inserted += batch_size
                    total_duration += duration

                
                    if ratelimit_event.is_set() is False:
                        print(f"[{table_name}] Ratelimit event set: Inserted {batch_size} rows in {duration:.4f} seconds "
                                f"→ {batch_size / duration:.2f} rows/sec and waiting")
                        ratelimit_event.wait()
                        print(f"[{table_name}] Ratelimit event cleared, resuming")
                    else:
                        print(f"[{table_name}] Inserted {batch_size} rows in {duration:.4f} seconds "
                          f"→ {batch_size / duration:.2f} rows/sec")

                except IntegrityError:
                    print(f"[{table_name}] Some records already exist (ignored)")
                except Exception as e:
                    print(f"[{table_name}] DB write failed: {e}")
                    sys.exit(1)
                finally:
                    buffer.clear()

    finally:
        if buffer:  # Write remaining records
            try:
                print(f"{table_name}: Final batch write records: {len(buffer)}")
                keys = buffer[0].keys()
                placeholders = ', '.join(f":{col}" for col in keys)
                columns = ', '.join(f"`{col}`" for col in keys)
                sql = text(f"""
                    INSERT IGNORE INTO `{table_name}` ({columns})
                    VALUES ({placeholders})
                """)
                # ⏱ Start timing
                start_time = time.perf_counter()
                with conn.begin():
                    conn.execute(sql, buffer)
                end_time = time.perf_counter()
                duration = end_time - start_time
                # 💡 Track stats
                total_inserted += len(buffer)
                total_duration += duration
                print(f"[{table_name}] Last Batch Inserted {len(buffer)} rows in {duration:.4f} seconds "
                      f"→ {len(buffer) / duration:.2f} rows/sec")
            except Exception as e:
                print(f"{table_name}: Final batch write failed: {e}")

        print(f"db_write_worker completed for {table_name}")
        conn.close()
        if total_duration > 0:
            print(f"[{table_name}] Total throughput: "
                  f"{total_inserted} rows in {total_duration:.2f} seconds → "
                  f"{total_inserted / total_duration:.2f} rows/sec")

def db_writer_worker2(sql_engine, table_name, write_queue, shutdown_flag):
    conn = sql_engine.connect()
    buffer = []

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

            # Flush batch if enough records accumulated or shutdown initiated
            if len(buffer) >= BATCH_SIZE or (shutdown_flag.is_set() and buffer):
                try:
                    # Extract column names from first record
                    keys = buffer[0].keys()
                    placeholders = ', '.join(f":{col}" for col in keys)
                    columns = ', '.join(f"`{col}`" for col in keys)

                    sql = text(f"""
                        INSERT IGNORE INTO `{table_name}` ({columns})
                        VALUES ({placeholders})
                    """)

                    with conn.begin():  # One transaction for entire batch
                        conn.execute(sql, buffer)
                except IntegrityError:
                    print(f"{table_name}: Some records already exist (ignored)")
                except sqlite3.OperationalError:
                    print(f"{table_name}: Operational error (e.g., connection lost)")
                    sys.exit(1)
                except sqlite3.ProgrammingError:
                    print(f"{table_name}: Programming error")
                    sys.exit(1)
                except Exception as e:
                    print(f"{table_name}: DB write failed: {e}")
                    sys.exit(1)
                finally:
                    buffer.clear()

    finally:
        if buffer:  # Write remaining records
            try:
                keys = buffer[0].keys()
                placeholders = ', '.join(f":{col}" for col in keys)
                columns = ', '.join(f"`{col}`" for col in keys)
                sql = text(f"""
                    INSERT IGNORE INTO `{table_name}` ({columns})
                    VALUES ({placeholders})
                """)
                with conn.begin():
                    conn.execute(sql, buffer)
            except Exception as e:
                print(f"{table_name}: Final batch write failed: {e}")
        conn.close()

def db_writer_worker_new(sql_engine, table_name, write_queue, shutdown_flag, batch_size=10000):
    buffer = []
    
    def flush_buffer(buffer, conn):
        if not buffer:
            return
        try:
            placeholders = ', '.join(f":{col}" for col in buffer[0])
            columns = ', '.join(f"`{col}`" for col in buffer[0])
            sql = text(f"""
                INSERT IGNORE INTO `{table_name}` ({columns})
                VALUES ({placeholders})
            """)
            conn.execute(sql, buffer)  # pass list of dicts for batch insert
        except IntegrityError:
            print(f"{table_name}: Some records already exist (IntegrityError)")
        except sqlite3.OperationalError:
            print(f"{table_name}: Operational error like connection lost etc")
            sys.exit(1)
        except sqlite3.ProgrammingError:
            print(f"{table_name}: Programming error")
            sys.exit(1)
        except Exception as e:
            print(f"{table_name}: DB batch write failed: {e}")
            sys.exit(1)
        finally:
            buffer.clear()

    with sql_engine.begin() as conn:
        try:
            while not shutdown_flag.is_set() or not write_queue.empty():
                try:
                    record = write_queue.get(timeout=1)
                    #record = write_queue.get(timeout=1, block=True)
                    if record is SENTINEL:
                        write_queue.task_done()
                        break
                    buffer.append(record)
                    if len(buffer) >= batch_size:
                        flush_buffer(buffer, conn)
                    write_queue.task_done()
                except queue.Empty:
                    # Flush remaining if queue is empty temporarily
                    flush_buffer(buffer, conn)
                    continue
        finally:
            # Final flush on shutdown
            flush_buffer(buffer, conn)

def create_or_patch_table(engine, table_name):
    inspector = inspect(engine)
    metadata = MetaData()
    if table_name not in inspector.get_table_names():
        print(f"Creating table {table_name}...")
        columns = [
            Column(col, col_type, nullable=False if col in PRIMARY_KEYS else True, primary_key=True if col in PRIMARY_KEYS else False)
            for col, col_type in EXPECTED_COLUMNS.items()
        ]
        Table(table_name, metadata, *columns)
        metadata.create_all(engine)
    else:
        with engine.begin() as conn:
            existing_columns = {col['name'] for col in inspector.get_columns(table_name)}
            for col_name, col_type in EXPECTED_COLUMNS.items():
                if col_name not in existing_columns:
                    col_type_str = str(col_type.compile(dialect=engine.dialect))
                    conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN `{col_name}` {col_type_str}"))
            pk_constraint = inspector.get_pk_constraint(table_name)
            existing_pk = pk_constraint.get('constrained_columns', [])
            if set(existing_pk) != set(PRIMARY_KEYS):
                conn.execute(text(f"ALTER TABLE {table_name} DROP PRIMARY KEY"))
                conn.execute(text(f"ALTER TABLE {table_name} ADD PRIMARY KEY ({', '.join(PRIMARY_KEYS)})"))
            #elif 'symbol_date_index' not in [index.name for index in inspector.get_indexes(table_name)]:
            #    conn.execute(text(f"ALTER TABLE {table_name} ADD INDEX symbol_date_index (symbol, date)"))
    create_and_check_indexes(engine, table_name)

def find_first_valid_date(symbol, start_date, end_date):
    cal = USFederalHolidayCalendar()
    holidays = cal.holidays(start=start_date, end=end_date).to_pydatetime()
    business_days = pd.date_range(start=start_date, end=end_date, freq='B').difference(pd.to_datetime(holidays))

    for current_date in business_days:
        date_str = current_date.strftime('%Y-%m-%d')
        url = f'https://www.alphavantage.co/query?function=HISTORICAL_OPTIONS&symbol={symbol}&date={date_str}&apikey={API_KEY}'
        try:
            response = requests.get(url)
            data = response.json()
            if len(data.get('data', [])) > 0:
                return current_date
        except Exception as e:
            print(f"Error checking {date_str}: {e}")
            continue
    return None  # No valid date found

def fetch_and_insert_records(i, symbol, start_date, end_date, request_times, db, engine, table_name, write_queue, shutdown_flag, ratelimit_event):
    """Fetches option data for a given symbol and date range and directly inserts it into the database."""
    first_valid_date = start_date
    #first_valid_date = find_first_valid_date(symbol, start_date, end_date)
    #if not first_valid_date:
    #    print("No records found in the given date range.")
    #    return

    cal = USFederalHolidayCalendar()
    holidays = cal.holidays(start=first_valid_date, end=end_date).to_pydatetime()
    business_days = pd.date_range(start=first_valid_date, end=end_date, freq='B').difference(pd.to_datetime(holidays))

    #ratelimit_event = threading.Event()
    #ratelimit_event.set()
    db_thread = threading.Thread(target=db_writer_worker, args=(engine, table_name, write_queue, shutdown_flag, ratelimit_event))
    db_thread.start()

    zero_records_cnt = 0
    session = get_session_with_retries()
    if not business_days.empty:
        for current_date in business_days:
            date_str = current_date.strftime('%Y-%m-%d')
            URL = f'https://www.alphavantage.co/query?function=HISTORICAL_OPTIONS&symbol={symbol}&date={date_str}&apikey={API_KEY}'
            #while True:
            #    now = time.time()
            #    #if len(request_times) >= 75:
            #    #    print(f"Symbol {symbol} has reached the request limit. Waiting for the oldest request to expire.")
            #    #    oldest_time = request_times[0]
            #    #    if now - oldest_time < 60:
            #    #        time.sleep(60 - (now - oldest_time))
            #    #    else:
            #    #        request_times.popleft()
            #    #request_times.append(now)
            #    break
            #print(f"{symbol}: waiting on log_request") 
            log_request(symbol, ratelimit_event)
            #print(f"{symbol}: Sending request")
            try:
                response = session.get(URL, timeout=10)
            except RemoteDisconnected:
                print(f"[{symbol}] RemoteDisconnected: Retrying after 10s...")
                time.sleep(100)
                response = session.get(URL, timeout=10)
                continue
            except requests.exceptions.RequestException as e:
                print(f"[{symbol}] Request failed: {e}")
                time.sleep(100)
                response = session.get(URL, timeout=10)
                continue

            #response = requests.get(URL)
            if response.status_code != 200:
                print(f"Failed to get response for url {URL}")
                return
            #else:
            #    print(f"Got response for url {URL}")
            data = response.json()
            if 'Note' in data or 'Information' in data:
                print("Looks like ratelimit have reached wait for a second")
                time.sleep(20)
                response = requests.get(URL)
                data = response.json()
            if 'data' in data:
                num_records = len(data['data'])
                print(f"{i}: {dt.now()}: {symbol}: {date_str}, num_records: {num_records}")
                if num_records == 0:
                    zero_records_cnt += 1
                    DB.update_field(db.US_Stocks, symbol, "dates.options_pull_latest_entry_date", dt.combine(current_date, dt.min.time()))
                    ##print(f"{symbol}: Exiting *****************************************")
                    #if zero_records_cnt >= 5:
                    #    print(f"{symbol}: Continuously 5 zero record requests,incrementing to year *****************************************")
                    #    write_queue.put(SENTINEL)
                    #    write_queue.join()
                    #    db_thread.join()
                    #    return
                    continue
                else:
                    zero_records_cnt = 0
                #conn  = engine.connect()
                #with engine.begin() as conn:
                if True:
                    for opt in data.get('data', []):
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
                            # Insert directly into the database
                            placeholders = ', '.join(f":{col}" for col in record)
                            columns = ', '.join(f"`{col}`" for col in record)
                            sql = text(f"""
                                INSERT IGNORE INTO `{table_name}` ({columns})
                                VALUES ({placeholders})
                            """)
                            #print(record)
                            #trans = conn.begin()

                            #conn.execute(sql, record)
                            write_queue.put(record)
                            #trans.commit()
                        except IntegrityError as e:
                            print(f"{table_name} : Record already exist")
                        except sqlite3.OperationalError as e:
                            #conn.rollback()
                            print(f"{table_name} : Operational error like connection lost etci, error: {str(e)}")
                            sys.exit(1)
                        except sqlite3.ProgrammingError as e:
                            #conn.rollback()
                            print(f"{table_name} : Programatical error: {str(e)}")
                            sys.exit(1)
                        except Exception as e:
                            #conn.rollback()
                            print(f"{table_name} : DB write failed: {str(e)}")
                            #sys.exit(1)
                    #conn.close()
            else:
                print(f"No data for {symbol} on {date_str}. Response: {data}")
            time.sleep(1)

    #print(f"{i}: {table_name}: Joining db thread")
    shutdown_flag.set()
    write_queue.put(SENTINEL)
    write_queue.join()
    db_thread.join()
    #print(f"{i}: {table_name}: Joining db thread completed")

def process_symbol(sem, i, stk, cpu_affinity, request_times, ratelimit_event):
    if cpu_affinity is not None:
        try:
            os.sched_setaffinity(0, {cpu_affinity})
        except AttributeError:
            pass

    c = open_db_client()
    db = c['Stocks']
    engine = DB.open_sql_connection('10.89.45.31', 'vpetla', 'petla123', db='US_Stocks_Options')
    inspector = inspect(engine)
    #write_queue = queue.Queue(maxsize=1000000)
    #write_queue = queue.Queue(80000)
    write_queue = queue.Queue(maxsize=200_000) 
    shutdown_flag = threading.Event()

    end_date = dt.now().date()

    table_name = f"STK{stk['bscs']['symbol']}"
    create_or_patch_table(engine, table_name)
    #sem.release()
    #write_queue.join()
    #shutdown_flag.set()
    #engine.dispose()
    #print(f"{i} : Finished processing {stk['bscs']['symbol']}")
    #return
    if table_name not in inspector.get_table_names():
        if 'General' in stk.keys() and 'IPODate' in stk['General'].keys():
            try:
                start_date = dt.strptime(stk['General']['IPODate'], "%Y-%m-%d").date()
                if start_date < dt(2008, 1, 1).date():
                    start_date = dt(2008, 1, 1).date()
            except Exception as E:
                start_date = dt(2008, 1, 1).date()
    else:
        with engine.connect() as conn:
            try:
                latest_date_result = conn.execute(text(f"SELECT MAX(date) FROM {table_name}")).fetchone()
            except Exception as e:
                print(f"{i}: {stk['bscs']['symbol']}: Error : {str(e)}")
                print(f"{i}: {stk['bscs']['symbol']}: Releasing semaphore")
                if sem:
                    sem.release()
                return
            latest_date = latest_date_result[0]
            stks = db.US_Stocks.find({"bscs.symbol": stk['bscs']['symbol']})
            ipo_date = dt(2008, 1, 1).date()
            last_pull_date = ipo_date
            if stks.count() > 0:
                stk = stks[0]
                if 'options_pull_latest_entry_date' in stk['dates'].keys():
                    last_pull_date = stk['dates']['options_pull_latest_entry_date'] + datetime.timedelta(1)
                    last_pull_date = last_pull_date.date()
                else:
                    if 'General' in stk.keys() and 'IPODate' in stk['General'].keys():
                        try:
                            ipo_date = dt.strptime(stk['General']['IPODate'], "%Y-%m-%d").date()
                            if ipo_date < dt(2008, 1, 1).date():
                                ipo_date = dt(2008, 1, 1).date()
                            last_pull_date = ipo_date
                        except Exception as E:
                            last_pull_date = dt(2008, 1, 1).date()
            else:
                return
            if not latest_date or last_pull_date > latest_date:
                start_date = last_pull_date
            else:
                start_date = latest_date
            #start_date = latest_date if latest_date else last_pull_date
            #start_date = latest_date + timedelta(days=1) if latest_date else dt(2008, 1, 1).date()
    print(f"{i}:{table_name} : start_date: {start_date}") 
    if start_date <= end_date:
        fetch_and_insert_records(i, stk['bscs']['symbol'], start_date, end_date, request_times, db, engine, table_name, write_queue, shutdown_flag, ratelimit_event)
    if sem:
        print(f"{i}: {stk['bscs']['symbol']}: Releasing semaphore")
        sem.release()

    #shutdown_flag.set()
    engine.dispose()
    print(f"{i} : Finished processing {stk['bscs']['symbol']}")

if __name__ == "__main__":
    c = open_db_client()
    db = c['Stocks']
    collection = get_collection('US', db)
    engine = DB.open_sql_connection('10.89.45.31', 'vpetla', 'petla123', db='US_Stocks_Options')
    inspector = inspect(engine)
    table_names = inspector.get_table_names()

    ratelimit_event = threading.Event()
    ratelimit_event.set()

    num_cores = multiprocessing.cpu_count()
    num_cores = 30
    sem = multiprocessing.BoundedSemaphore(num_cores)
    processes = [None]*num_cores

    manager = Manager()
    request_times = manager.list(deque(maxlen=75))
    i = 0
    num_cores = multiprocessing.cpu_count()
    sort = 1
    #stocks = db.US_Stocks.find({"$and" : [
    #                                        {"General.IsDelisted": False},
    #                                        {'General.Type':'Common Stock'},
    #                                        {"$or": [
    #                                            {'General.Exchange':{"$in":major_exchanges}},
    #                                            {"$and": [
    #                                                {'General.Exchange':{"$nin":major_exchanges}},
    #                                                {'bscs.tracking':{'$exists':True}},
    #                                            ]
    #                                            },
    #                                        ]
    #                                        },
    #                                        {'dates.technicals_pull_date': {'$gte':get_latest_trading_day()}},
    #                                        {"$or": [
    #                                            {'failcount.mysql_price_failcount': {"$exists": False}},
    #                                            #{'failcount.mysql_price_failcount': {'$eq': 0}},
    #                                            {'failcount.mysql_price_failcount': {'$lt': MAX_FAIL_COUNT}},
    #                                        ]
    #                                        },
    #                                        {'Highlights.MarketCapitalization': {'$gte': 5 * Bn}},
    #                                    ]
    #                                }\
    #                                ).batch_size(10).sort([["failcount.mysql_price_failcount",1]]).allow_disk_use(True).sort([["sno",sort]]).allow_disk_use(True)
    ##stocks=db.US_Stocks.find({"$and":[{'General.Exchange':{"$in":major_exchanges}}, {'General.Type':'Common Stock'}]}).batch_size(10).sort([["failcount.mysql_price_failcount",1]]).allow_disk_use(True).sort([["sno",1]]).allow_disk_use(True)
    #stocks = collection.find({'bscs.symbol':'NVDA'},no_cursor_timeout=True).batch_size(10).sort([["sno",1]])

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
                    #{"$or":[\
                    #            {'General.Sector': {"$in": ['Technology', 'Communication Services', ]}},\
                    #            {"$and": [ \
                    #                        {'General.Sector': {"$nin": ['Technology', 'Communication Services', ]}},\
                    #                        {'General.Code' : {"$in": non_tech_stocks}},\
                    #                    ]\
                    #            },\
                    #            {"$and": [ \
                    #                        {'General.Code' : {"$in": selected_stocks}},\
                    #                    ]\
                    #            },\
                    #        ]\
                    #},\
                    {'Highlights.MarketCapitalization': {'$gte': 1 * Bn}},\
                ]

    stocks = db.US_Stocks.find({'$and':conditions}, no_cursor_timeout=True).sort([["Highlights.MarketCapitalization",-1]]).batch_size(10).allow_disk_use(True)
    #stocks = collection.find({'bscs.symbol':'TLK'},no_cursor_timeout=True).batch_size(10).sort([["sno",1]])
    print("Total non-bulk stocks: %r" %(stocks.count()))


    try:
        # Start logger
        logger_thread = threading.Thread(target=log_rate_forever, daemon=True)
        logger_thread.start()

        # ETFs
        #for i, k in enumerate(etfs):
        #    stocks = collection.find({'bscs.symbol':k},no_cursor_timeout=True).batch_size(10).sort([["sno",1]])
        #    if stocks.count() == 1:
        #        stk = stocks[0]
        #        cpu_affinity = i % num_cores
        #        sem.acquire()
        #        print("%d: ETF %r" %(i, stk['bscs']['symbol']))
        #        process_symbol(sem, i, stk, cpu_affinity, request_times, ratelimit_event)
        #        #processes[i%num_cores] = multiprocessing.Process(target=process_symbol, args=(sem, i, stk, cpu_affinity, request_times, ratelimit_event))
        #        #processes[i%num_cores].start()
 
        # Stocks
        for i, stk in enumerate(stocks):
        #for i, stk in enumerate(options_stocks):
            sem.acquire()
            cpu_affinity = i % num_cores
            if stk['bscs']['symbol'] in ['USM']:
                table_name = DB.get_symbol_table_name(stk['bscs']['symbol'])
                table_names.remove(table_name)
                continue
            print("%d: Stock %r" %(i, stk['bscs']['symbol']))
            processes[i%num_cores] = multiprocessing.Process(target=process_symbol, args=(sem, i, stk, cpu_affinity, request_times, ratelimit_event))
            processes[i%num_cores].start()

            #process_symbol(sem, i, stk, cpu_affinity, request_times, ratelimit_event)
            #process_symbol(sem, i, stk, cpu_affinity, request_times)
            table_name = DB.get_symbol_table_name(stk['bscs']['symbol'])
            if table_name in table_names:
                table_names.remove(table_name)
        #process_symbol(sem, 'AMZN', 0, request_times)
        #for symbol in datastructures.selected_stocks:
        #    sem.acquire()
        #    cpu_affinity = i % num_cores
        #    #p = multiprocessing.Process(target=process_symbol, args=(sem, stk['bscs']['symbol'], cpu_affinity, request_times))
        #    #p.start()
        #    process_symbol(sem, symbol, cpu_affinity, request_times)
        
        for i, table_name in enumerate(table_names):
            sym = table_name[3:]
            sem.acquire()
            cpu_affinity = i % num_cores
            print("%d: Stock %r" %(i, sym))
            stks = db.US_Stocks.find({"bscs.symbol" : sym})
            if stks.count() > 1:
                stk = stks[0]
            processes[i%num_cores] = multiprocessing.Process(target=process_symbol, args=(sem, i, stk, cpu_affinity, request_times, ratelimit_event))
            processes[i%num_cores].start()

    finally:
        stop_event.set()
        logger_thread.join()
        for j in range(len(processes)):
            if processes[j] is not None:
                processes[j].join()
 
        close_db_client(c)
        close_sql_connection(engine)

    print("Finished processing all symbols.")
