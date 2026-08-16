import requests
from datetime import datetime as dt
from sqlalchemy import (
    create_engine, Column, String, Float, Date, Integer, MetaData, Table, inspect, text
)
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.exc import IntegrityError
import pymysql
import pandas as pd

#from DB import * #Removed this import
#See the updated open_sql_connection function
# CONFIGURATION
API_KEY = 'Q1ZDXMK2ZBJHPHFV'  # Use real API key
SYMBOL = 'NVDA'
URL = f'https://www.alphavantage.co/query?function=HISTORICAL_OPTIONS&symbol={SYMBOL}&apikey={API_KEY}'

TABLE_NAME = 'historical_options'

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
    
sql_engine = open_sql_connection('10.89.45.208', 'vpetla', 'petla123', db='US_Stocks_Options')
metadata = MetaData()
inspector = inspect(sql_engine)

def create_or_patch_table():
    if TABLE_NAME not in inspector.get_table_names():
        print("🔧 Creating table from scratch...")
        columns = [
            Column(col, col_type, nullable=False if col in PRIMARY_KEYS else True, primary_key=True if col in PRIMARY_KEYS else False) #Added primary key here
            for col, col_type in EXPECTED_COLUMNS.items()
        ]


        Table(TABLE_NAME, metadata, *columns)
        metadata.create_all(sql_engine)
    else:
        print("✅ Table exists — verifying schema...")
        existing_columns = {col['name'] for col in inspector.get_columns(TABLE_NAME)}

        with sql_engine.begin() as conn:
            for col_name, col_type in EXPECTED_COLUMNS.items():
                if col_name not in existing_columns:
                    print(f"➕ Adding missing column: {col_name}")
                    col_type_str = str(col_type.compile(dialect=sql_engine.dialect))
                    conn.execute(text(f"ALTER TABLE {TABLE_NAME} ADD COLUMN `{col_name}` {col_type_str}"))

            # Check if primary key is correct
            pk_constraint = inspector.get_pk_constraint(TABLE_NAME)
            existing_pk = pk_constraint.get('constrained_columns', [])
            if set(existing_pk) != set(PRIMARY_KEYS):
                print("⚠️  Incorrect/missing primary key. Fixing...")
                # Recreate PK: Drop old + add correct one
                conn.execute(text(f"ALTER TABLE {TABLE_NAME} DROP PRIMARY KEY"))
                conn.execute(text(f"ALTER TABLE {TABLE_NAME} ADD PRIMARY KEY ({', '.join(PRIMARY_KEYS)})"))
            else:
                print("✅ Primary key OK")

# === FETCH & PARSE DATA ===
def fetch_option_records():
    response = requests.get(URL)
    data = response.json()
    records = []
    for opt in data.get('data', []):
        try:
            records.append({
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
            })
        except Exception as e:
            print(f"Skipping bad record: {e}")
    return records

# === INSERT RECORDS SAFELY (NO DUPLICATES) ===
def insert_records(records, engine, table_name): #Added engine and table_name
    """
    Inserts data into the specified table.

    Args:
        records: A list of dictionaries, where each dictionary
                 represents a row to insert.  The keys of the
                 dictionaries should match the column names.
    """
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
                print(f"Inserted record: {record['contractID']}, {record['date']}")  # Added print
            except Exception as e:
                print(f"⚠️ Skipping record due to error: {e}")
        print(f"Successfully inserted data into {table_name}")

# === MAIN RUN ===
if __name__ == "__main__":
    create_or_patch_table()
    option_records = fetch_option_records()
    insert_records(option_records, sql_engine, TABLE_NAME) #Added engine and tablename
    print(f"✅ Processed {len(option_records)} option records for {SYMBOL}.")
    sql_engine.dispose() #Added to dispose the engine
