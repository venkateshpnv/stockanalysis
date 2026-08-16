import requests
from datetime import datetime as dt, timedelta
from sqlalchemy import (
    create_engine, Column, String, Float, Date, Integer, MetaData, Table, inspect, text, func
)
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.exc import IntegrityError
import pymysql
import time  # Import the time module
import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar

# CONFIGURATION
API_KEY = '0VSJCBP413AEAYV5'  # Replace with your actual API key
SELECTED_STOCKS = ['AAPL', 'AMZN', 'MSFT', 'META', 'TSLA', 'MSTR', 'COIN', 'AVGO', 'ROKU', 'PANW', 'ANET', 'INTC', 'CRWD', 'NFLX', 'MARA', 'PLAY', 'PLTR', 'MU', 'AMD', 'NVDA', 'ARM', 'GSPC']
# BASE_URL = 'https://www.alphavantage.co/query?function=HISTORICAL_OPTIONS&symbol={symbol}&apikey={apikey}' #Removed
# TABLE_NAME = 'historical_options' #No longer needed.

# === DEFINE EXPECTED TABLE SCHEMA ===
EXPECTED_COLUMNS = {
    'contractID': String(30),
    'symbol': String(10),
    'expiration': Date,
    'strike': Float,
    'type': String(4),
    'last': Float,
    'mark': Float,
    'bid': Float,
    'bid_size': Integer,
    'ask': Float,
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

# === CONNECT TO DATABASE ===
def open_sql_connection(host, user, password, db):
    """Opens a SQL connection using pymysql and returns a SQLAlchemy engine."""
    try:
        conn = pymysql.connect(
            host=host,
            user=user,
            password=password,
            db=db,
            charset="utf8mb4",  # Important for handling various character sets
            cursorclass=pymysql.cursors.DictCursor,  # Return rows as dictionaries
        )
        # Create a SQLAlchemy engine from the pymysql connection
        engine = create_engine(f"mysql+pymysql://{user}:{password}@{host}/{db}", pool_pre_ping=True)
        return engine
    except pymysql.MySQLError as e:
        print(f"Error connecting to MySQL: {e}")
        return None  # Important: Return None on failure

sql_engine = open_sql_connection('10.89.45.208', 'vpetla', 'petla123', db='US_Stocks_Options') #changed user
metadata = MetaData()
inspector = inspect(sql_engine)


def create_or_patch_table(engine, table_name):
    """Creates or patches the table schema in the database."""
    if table_name not in inspector.get_table_names(): #changed this line
        print(f"🔧 Creating table {table_name} from scratch...")
        columns = [
            Column(col, col_type, nullable=False if col in PRIMARY_KEYS else True, primary_key=True if col in PRIMARY_KEYS else False)
            for col, col_type in EXPECTED_COLUMNS.items()
        ]
        Table(table_name, metadata, *columns)
        metadata.create_all(engine)
    else:
        print(f"✅ Table {table_name} exists — verifying schema...")
        existing_columns = {col['name'] for col in inspector.get_columns(table_name)}

        with engine.begin() as conn:
            for col_name, col_type in EXPECTED_COLUMNS.items():
                if col_name not in existing_columns:
                    print(f"➕ Adding missing column: {col_name} to {table_name}")
                    col_type_str = str(col_type.compile(dialect=engine.dialect))
                    conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN `{col_name}` {col_type_str}"))

            # Check if primary key is correct
            pk_constraint = inspector.get_pk_constraint(table_name)
            existing_pk = pk_constraint.get('constrained_columns', [])
            if set(existing_pk) != set(PRIMARY_KEYS):
                print(f"⚠️  Incorrect/missing primary key on {table_name}. Fixing...")
                # Recreate PK: Drop old + add correct one
                conn.execute(text(f"ALTER TABLE {table_name} DROP PRIMARY KEY"))
                conn.execute(text(f"ALTER TABLE {table_name} ADD PRIMARY KEY ({', '.join(PRIMARY_KEYS)})"))
            else:
                print(f"✅ Primary key OK on {table_name}")



# === FETCH & PARSE DATA ===
def fetch_option_records(symbol, start_date, end_date):
    """Fetches option data for a given symbol and date range from the Alpha Vantage API, skipping weekends and holidays."""
    records = []
    cal = USFederalHolidayCalendar()
    holidays = cal.holidays(start=start_date, end=end_date).to_pydatetime()
    # Generate business days, excluding weekends and holidays
    all_weekdays = pd.date_range(start=start_date, end=end_date, freq='B')
    business_days = all_weekdays.difference(pd.to_datetime(holidays))
    if not business_days.empty: # Changed condition
        for current_date in business_days:
            date_str = current_date.strftime('%Y-%m-%d')
            URL = f'https://www.alphavantage.co/query?function=HISTORICAL_OPTIONS&symbol={symbol}&date={date_str}&apikey={API_KEY}'
            response = requests.get(URL)
            data = response.json()
            if 'data' in data:
                for opt in data.get('data', []):
                    try:
                        record = {
                            'contractID': opt['contractID'],
                            'symbol': opt['symbol'],
                            'expiration': dt.strptime(opt['expiration'], '%Y-%m-%d').date(),
                            'strike': float(opt['strike']),
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
                        records.append(record)
                    except Exception as e:
                        print(f"Skipping bad record: {e} for {symbol} on {date_str}")
            else:
                print(f"⚠️  No data received for symbol {symbol} on {date_str}.  Response was: {data}")
            time.sleep(1)
    return records



# === INSERT RECORDS SAFELY (NO DUPLICATES) ===
def insert_records(records, engine, table_name):
    """
    Inserts data into the specified table.

    Args:
        records: A list of dictionaries, where each dictionary
                 represents a row to insert.
        engine:  The SQLAlchemy engine
        table_name: The name of the table.
    """
    if not records:
        print(f"No records to insert into {table_name}")
        return

    with engine.begin() as conn:
        for record in records:
            try:
                # Construct placeholders and columns dynamically based on the record's keys
                placeholders = ', '.join(f":{col}" for col in record)
                columns = ', '.join(f"`{col}`" for col in record)

                # INSERT IGNORE to skip duplicates
                sql = text(f"""
                    INSERT IGNORE INTO `{table_name}` ({columns})
                    VALUES ({placeholders})
                """)

                conn.execute(sql, record)
                print(f"Inserted record: {record['contractID']}, {record['date']} into {table_name}")  # Added table name to print
            except Exception as e:
                print(f"⚠️ Skipping record due to error: {e}")
        print(f"Successfully inserted data into {table_name}")



# === MAIN RUN ===
if __name__ == "__main__":
    engine = sql_engine  # Use the global sql_engine
    end_date = dt.now().date()

    for symbol in SELECTED_STOCKS:
        table_name = f"STK{symbol}"
        print(f"Processing symbol: {symbol}, table: {table_name}")
        create_or_patch_table(engine, table_name)

        # Determine the start date for fetching data
        #if inspector.has_table(table_name):
        if table_name not in inspector.get_table_names():
            # If table exists, fetch only from the latest date in the table
            with engine.connect() as conn:
                latest_date_result = conn.execute(text(f"SELECT MAX(date) FROM {table_name}")).fetchone()
                latest_date = latest_date_result[0]
                if latest_date:
                    start_date = latest_date + timedelta(days=1)  # Start from the day after the latest date
                else:
                    start_date = dt(2008, 1, 1).date() #If table is empty
        else:
            # If table doesn't exist, fetch from the beginning
            start_date = dt(2008, 1, 1).date()

        if start_date <= end_date:
            option_records = fetch_option_records(symbol, start_date, end_date)
            insert_records(option_records, engine, table_name)
        else:
            print(f"No new data to fetch for {symbol}")

    sql_engine.dispose()
    print("Finished processing all symbols.")
