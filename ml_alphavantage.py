#from sqlalchemy import create_engine, Column, String, Float, Date, Integer, MetaData, Table, insert
#import requests
#from datetime import datetime
#from sqlalchemy.exc import IntegrityError
#from sqlalchemy.dialects.mysql import insert as mysql_insert
#from DB import *
#import pandas as pd
import requests
from datetime import datetime as dt
from sqlalchemy import (
    create_engine, Column, String, Float, Date, Integer, MetaData, Table, inspect, text
)
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.exc import IntegrityError
import pymysql
import pandas as pd
from DB import *

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
sql_engine = open_sql_connection('10.89.45.208', 'root', 'petla123', db='US_Stocks_Options')
metadata = MetaData()
inspector = inspect(sql_engine)

def create_or_patch_table():
    if TABLE_NAME not in inspector.get_table_names():
        print("🔧 Creating table from scratch...")
        columns = [
            Column(col, col_type, nullable=False if col in PRIMARY_KEYS else True)
            for col, col_type in EXPECTED_COLUMNS.items()
        ]
        for col in columns:
            if col.name in PRIMARY_KEYS:
                col.primary_key = True

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
def insert_records(records):
    options_table = Table(TABLE_NAME, metadata, autoload_with=sql_engine)
    with sql_engine.begin() as conn:
        for record in records:
            # Construct placeholders and columns
            placeholders = ', '.join(f":{col}" for col in record)
            columns = ', '.join(f"`{col}`" for col in record)

            # INSERT IGNORE to skip duplicates
            sql = text(f"""
                INSERT IGNORE INTO `{TABLE_NAME}` ({columns})
                VALUES ({placeholders})
            """)
            try:
                conn.execute(sql, record)
            except Exception as e:
                print(f"⚠️ Skipping record due to error: {e}")
            #try:
            #    stmt = mysql_insert(options_table).values(**record)
            #    # No-op on conflict (avoids deprecated VALUES())
            #    stmt = stmt.on_duplicate_key_update(
            #        contractID=stmt.inserted.contractID,
            #        date=stmt.inserted.date
            #    )
            #    #stmt = stmt.on_duplicate_key_update(contractID=stmt.inserted.contractID)
            #    conn.execute(stmt)
            #except IntegrityError as e:
            #    print(f"Insert error: {e}")
            #    continue

# === MAIN RUN ===
if __name__ == "__main__":
    create_or_patch_table()
    option_records = fetch_option_records()
    insert_records(option_records)
    print(f"✅ Processed {len(option_records)} option records for {SYMBOL}.")

## Connect to DB
#sql_engine = open_sql_connection('10.89.45.208', 'root', 'petla123', db='US_Stocks_Options')
#metadata = MetaData()
#
### === Define Table with COMPOSITE PRIMARY KEY ===
##options_table = Table('historical_options', metadata,
##    Column('symbol', String(10), nullable=False),
##    Column("contract_symbol", String(30), nullable=False, primary_key=True),
##    Column('option_type', String(4)),
##    Column('strike', Float),
##    Column('expiration_date', Date),
##    Column('last_price', Float),
##    Column('volume', Integer),
##    Column('open_interest', Integer),
##    Column('implied_volatility', Float),
##    Column("date", Date, nullable=False, primary_key=True),
##    #PrimaryKey("contract_symbol", "date"),
##)
#historical_options_table = Table(
#    "historical_options",
#    metadata,
#    Column("contractID", String(30), nullable=False, primary_key=True),  # Renamed to contractID
#    Column("symbol", String(10), nullable=False),
#    Column("expiration", Date),  # Changed to Date
#    Column("strike", Float),
#    Column("type", String(4)),  # Renamed to type
#    Column("last", Float),  # Renamed to last
#    Column("mark", Float),
#    Column("bid", Float),
#    Column("bid_size", Integer),
#    Column("ask", Float),
#    Column("ask_size", Integer),
#    Column("volume", Integer),
#    Column("open_interest", Integer),
#    Column("date", Date, nullable=False, primary_key=True),
#    Column("implied_volatility", Float),
#    Column("delta", Float),
#    Column("gamma", Float),
#    Column("theta", Float),
#    Column("vega", Float),
#    Column("rho", Float),
#)
#
## Create table with correct PK
#metadata.create_all(sql_engine, checkfirst=True)
## === Fetch and parse data ===
#response = requests.get(URL)
#data = response.json()
#df = pd.DataFrame(data['data'])
##mysql_update_table(sql_engine, 'historical_options', df, check=False, insert=False, unknown_table=False, cols_type='price', temp=False, date_column=False, format_columns=False, primary_key=True, empty_table=False, fin_table=False, symbol=None, columns={})
## Parse and transform
#records = []
## Parse and transform
#records = []
#for opt in data.get('data', []):
#    try:
#        records.append({
#            'contractID': opt['contract_symbol'],
#            'symbol': SYMBOL,
#            'expiration': datetime.strptime(opt['expiration_date'], '%Y-%m-%d').date(),
#            'strike': float(opt['strike']),
#            'type': opt['option_type'],
#            'last': float(opt.get('last_price', 0)),
#            'mark': float(opt.get('mark_price', 0)),
#            'bid': float(opt.get('bid', 0)),
#            'bid_size': int(opt.get('bid_size', 0)),
#            'ask': float(opt.get('ask', 0)),
#            'ask_size': int(opt.get('ask_size', 0)),
#            'volume': int(opt.get('volume', 0)),
#            'open_interest': int(opt.get('open_interest', 0)),
#            'date': datetime.strptime(opt['date'], '%Y-%m-%d').date(),
#            'implied_volatility': float(opt.get('implied_volatility', 0)),
#            'delta': float(opt.get('delta', 0)),
#            'gamma': float(opt.get('gamma', 0)),
#            'theta': float(opt.get('theta', 0)),
#            'vega': float(opt.get('vega', 0)),
#            'rho': float(opt.get('rho', 0))
#        })
#    except Exception as e:
#        print(f"Skipping option due to error: {e}")
#
## Insert into MySQL using SQLAlchemy Core
#with engine.begin() as conn:
#    for record in records:
#        try:
#            stmt = insert(options_table).values(**record)
#            conn.execute(stmt)
#        except IntegrityError:
#            continue
#
#print(f"Inserted {len(records)} records.")