import pandas as pd
import numpy as np
import requests
from datetime import datetime as dt, timedelta
from sqlalchemy import create_engine, MetaData, Table, Column, String, Float, Date, exc
import logging
import time
import DB

# --- Database and API Configuration ---
DB_HOST = 'localhost'
DB_USER = 'vpetla'  # Replace with your MySQL user
DB_PASSWORD = 'petla123'  # Replace with your MySQL password
DB_NAME = 'US_Stocks_Fin'
DB_NAME_STOCKS = 'US_Stocks'  # Database for stock general info
NASDAQ_EARNINGS_URL = 'https://api.nasdaq.com/api/calendar/earnings?date='
USER_AGENT = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:91.0) Gecko/20100101 Firefox/91.0'
MARKET_CAP_THRESHOLD = 1000000000  # 1 Billion

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
# Add console handler if not already present
if not logger.hasHandlers():
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(console_handler)

# --- Utility Functions (Refactored) ---

def create_mysql_engine(host, user, password, db):
    """Creates a SQLAlchemy engine for MySQL."""
    try:
        engine = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{db}')
        # Add a pool_recycle parameter.  This is vital for long-running
        # applications to handle MySQL server disconnects.
        engine.pool_recycle = 3600  # Recycle connections after 1 hour (or less)
        return engine
    except exc.SQLAlchemyError as e:
        logger.error(f"Error creating MySQL engine: {e}")
        raise  # Re-raise to stop execution

def check_and_create_table(engine, table_name, columns):
    """Checks if a table exists and creates it if not, with explicit column definitions."""
    metadata = MetaData()
    table = Table(table_name, metadata,
                  Column('Date', Date, primary_key=True),  # Explicit primary key
                  Column('Symbol', String(10), primary_key=True),
                  Column('companyName', String(255)),
                  Column('reportDate', String(20)),
                  Column('time', String(20)),
                  Column('epsForecast', Float),
                  Column('eps', Float),
                  Column('surprise', Float),
                  Column('lastYearEPS', Float),
                  Column('lastYearRptDt', String(20)),
                  Column('noOfEsts', Float),
                  Column('marketCap', Float),
                  Column('Sector', String(100)),
                  Column('Industry', String(100)),
                  Column('price_change', Float),  # Added price_change
                  # Add other columns as necessary, with explicit data types
                  )
    try:
        if not engine.dialect.has_table(engine, table_name):
            metadata.create_all(engine)
            logger.info(f"Table '{table_name}' created successfully.")
        else:
            logger.info(f"Table '{table_name}' already exists.")

        #Check for missing columns and add them.
        existing_columns = mysql_get_columns(engine, table_name)
        missing_columns = [col.name for col in table.columns if col.name not in existing_columns]
        if missing_columns:
            add_columns(engine, table_name, missing_columns)

    except exc.SQLAlchemyError as e:
        logger.error(f"Error creating or checking table '{table_name}': {e}")
        raise  # Re-raise to stop execution

def mysql_exists_table(engine, table_name):
    """Checks if a table exists using SQLAlchemy."""
    return engine.dialect.has_table(engine, table_name)

def mysql_get_columns(engine, table_name):
    """Gets column names from a MySQL table using SQLAlchemy."""
    try:
        inspector = engine.inspect(engine)  # Use the inspector
        return inspector.get_columns(table_name)
    except exc.SQLAlchemyError as e:
        logger.error(f"Error getting columns for table '{table_name}': {e}")
        raise
    except KeyError:
        logger.error(f"Table '{table_name}' not found.")
        return []

def add_columns(engine, table_name, columns):
    """Adds missing columns to a MySQL table using SQLAlchemy."""
    try:
        with engine.connect() as connection:
            inspector = engine.inspect(connection)
            existing_columns = [col['name'] for col in inspector.get_columns(table_name)]

            for col_name in columns:
                if col_name not in existing_columns:
                    # Determine the column type.  Default to String, adjust as necessary.
                    column_type = String(255)
                    if col_name in ['epsForecast', 'eps', 'surprise', 'lastYearEPS', 'marketCap', 'noOfEsts', 'price_change']:
                        column_type = Float
                    elif col_name in ['Date', 'lastYearRptDt']:
                        column_type = Date  # Or String, depending on your date format
                    alter_query = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {column_type}"
                    connection.execute(alter_query)
                    logger.info(f"Added column '{col_name}' to table '{table_name}'.")
    except exc.SQLAlchemyError as e:
        logger.error(f"Error adding columns to table '{table_name}': {e}")
        raise

def trading_day(date):
    """Returns the trading day for a given date (skips weekends)."""
    if date.weekday() >= 5:  # Saturday or Sunday
        days_to_subtract = date.weekday() - 4
        return date - timedelta(days=days_to_subtract)
    return date

def fetch_nasdaq_earnings(date):
    """Fetches earnings data from the Nasdaq API for a given date."""
    url = f'{NASDAQ_EARNINGS_URL}{date}'
    headers = {'User-Agent': USER_AGENT}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching data from Nasdaq API for date {date}: {e}")
        return None
    except ValueError as e:
        logger.error(f"Error decoding JSON from Nasdaq API for date {date}: {e}")
        return None

def parse_nasdaq_earnings_data(data, date):
    """Parses and transforms the raw JSON data from the Nasdaq API."""
    if not data or 'data' not in data or 'rows' not in data['data']:
        return pd.DataFrame()

    df = pd.DataFrame(data['data']['rows'])
    if df.empty:
        return df

    df = df.rename(columns={'symbol': 'Symbol'})

    def convert_marketcap(value):
        try:
            if not value:
                return 0
            value = value.replace('$', '').replace(',', '')
            return float(value)
        except (ValueError, AttributeError) as e:
            logger.warning(f"Invalid marketCap value: '{value}'.  Returning 0. Error: {e}")
            return 0

    df['marketCap'] = df['marketCap'].apply(convert_marketcap)
    df['Date'] = pd.to_datetime(df['fiscalQuarterEnding'], format='%b/%Y') + pd.offsets.MonthEnd(0)
    df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
    del df['fiscalQuarterEnding']
    df['reportDate'] = str(pd.to_datetime(date).date())  # Use the provided date
    if 'lastYearRptDt' in df.columns:
        df['lastYearRptDt'] = pd.to_datetime(df['lastYearRptDt'], errors='coerce').dt.strftime('%Y-%m-%d')
    df['time'] = df['time'].replace({'time-after-hours': 'AfterMarket',
                                     'time-pre-market': 'BeforeMarket',
                                     'time-not-supplied': np.nan})

    def convert_amount(value):
        if value == 'N/A' or not value:
            return np.nan
        if isinstance(value, str) and value.startswith('(') and value.endswith(')'):
            value = '-' + value[1:-1]
        value = value.replace('$', '')
        try:
            return float(value)
        except ValueError:
            return np.nan

    for col in ['lastYearEPS', 'epsForecast', 'eps', 'surprise']:
        if col in df.columns:
            df[col] = df[col].apply(convert_amount)
            if col == 'surprise':
                df[col] = df[col] / 100
    if 'noOfEsts' in df.columns:
        df['noOfEsts'] = pd.to_numeric(df['noOfEsts'], errors='coerce').fillna(0).astype(float)
    return df

def get_stock_info_from_mongodb(db, symbols):
    """Fetches stock sector and industry information from MongoDB."""
    if not symbols:
        return {}
    try:
        stocks = db.US_Stocks.find({'General.Code': {'$in': symbols}},
                                    {'General.Code': 1, 'General.Sector': 1,
                                     'General.Industry': 1, '_id': 0},
                                    no_cursor_timeout=True)
        return {stock['General']['Code']: {
            'Sector': stock['General'].get('Sector'),
            'Industry': stock['General'].get('Industry')
        } for stock in stocks}
    except Exception as e:
        logger.error(f"Error fetching stock info from MongoDB: {e}")
        return {}

def update_stock_earnings_dates(db, earnings_data):
    """Updates the last earnings date in MongoDB for each stock."""
    for index, row in earnings_data.iterrows():
        symbol = row['Symbol']
        try:
            earnings_date = dt.combine(dt.strptime(row['reportDate'], "%Y-%m-%d").date(), dt.min.time())
            time_of_day = row['time']
            update_fields = {"dates.ndaq_last_earnings_date": earnings_date}
            if time_of_day:
                update_fields["dates.ndaq_last_earnings_time"] = time_of_day
            db.US_Stocks.update({'General.Code': symbol}, {'$set': update_fields})
        except Exception as e:
            logger.error(f"Error updating earnings date for symbol {symbol}: {e}")

def fetch_existing_earnings_data(engine, start_date, table_name):
    """Fetches existing earnings data from the database for comparison."""
    #query = f"SELECT * FROM {table_name} WHERE reportDate >= '{start_date}' ORDER BY Date, Symbol"
    query = f"SELECT * FROM {table_name} ORDER BY Date, Symbol"
    try:
        return pd.read_sql(query, engine)
    except exc.SQLAlchemyError as e:
        logger.error(f"Error fetching existing earnings data: {e}")
        return pd.DataFrame()

def update_earnings_data_to_sql(engine, table_name, new_data, existing_data, mysql_engine):
    """
    Updates earnings data in the SQL database, handling both new and updated records.

    Args:
        engine: SQLAlchemy engine.
        table_name: Name of the table.
        new_data: DataFrame of new earnings data.
        existing_data: DataFrame of existing earnings data from the database.
    """
    try:
        with engine.connect() as connection:
            if existing_data.empty:
                logger.info("Earnings data table is empty or no recent data, inserting all fetched data.")
                #new_data.to_sql(name=table_name, con=connection, if_exists='append', index=False)
                DB.mysql_update_table(mysql_engine, table_name, new_data, check=True, insert=False, unknown_table=False, cols_type='values', temp=False, date_column=False, format_columns=False, primary_key=False, empty_table=False, fin_table=True, symbol=None)
                return

            existing_data['Index'] = existing_data['Date'].astype(str) + '_' + existing_data['Symbol'].astype(str)
            new_data['Index'] = new_data['Date'].astype(str) + '_' + new_data['Symbol'].astype(str)

            existing_data.set_index('Index', inplace=True)
            new_data.set_index('Index', inplace=True)

            # Separate new and existing entries
            new_entries_df = new_data[~new_data.index.isin(existing_data.index)].reset_index()
            existing_entries_df = new_data[new_data.index.isin(existing_data.index)].reset_index()
            db_existing_entries_df = existing_data[existing_data.index.isin(new_data.index)].reset_index()

            if not existing_entries_df.empty and not db_existing_entries_df.empty:
                # Merge on Date and Symbol to compare
                merged_df = pd.merge(existing_entries_df, db_existing_entries_df, on=['Date', 'Symbol'], suffixes=('_new', '_db'), how='inner')

                updates_to_apply = []
                for _, row in merged_df.iterrows():
                    diff = {}
                    #for col in ['noOfEsts', 'reportDate', 'epsForecast', 'lastYearRptDt', 'lastYearEPS', 'time', 'eps', 'surprise']:
                    for col in ['eps', 'surprise', 'time', 'epsForecast', 'noOfEsts', 'reportDate']:
                        new_val = row[f'{col}_new']
                        db_val = row[f'{col}_db']
                        if pd.notna(new_val) and pd.notna(db_val):
                            if isinstance(new_val, (int, float)) and isinstance(db_val, (int, float)):
                                if abs(new_val - db_val) > 1e-6:  # Tolerance for float comparison
                                    diff[col] = new_val
                            elif new_val != db_val:
                                diff[col] = new_val
                        elif pd.notna(new_val) and pd.isna(db_val):
                            diff[col] = new_val
                    if diff:
                        update_row = {'Date': row['Date'], 'Symbol': row['Symbol'], **diff}  # Include Date and Symbol
                        updates_to_apply.append(update_row)

                if updates_to_apply:
                    # Use a more efficient update mechanism.  This example constructs a single UPDATE statement
                    # for each unique Date/Symbol combination.  This assumes that your combined primary key
                    # is Date and Symbol.  Adapt the query if your primary key is different.
                    for update_data in updates_to_apply:
                        conditions = f"Date = '{update_data['Date']}' AND Symbol = '{update_data['Symbol']}'"
                        set_clauses = ', '.join(f"{col} = %s" for col in update_data if col not in ['Date', 'Symbol'])
                        values = [val for col, val in update_data.items() if col not in ['Date', 'Symbol']]
                        query = f"UPDATE {table_name} SET {set_clauses} WHERE {conditions}"
                        try:
                            connection.execute(query, values)
                            logger.info(f"Updated record in {table_name} with conditions: {conditions}")
                        except exc.SQLAlchemyError as e:
                            logger.error(f"Error updating record in {table_name} with conditions: {conditions}: {e}")

            if not new_entries_df.empty:
                # Insert new entries
                cols = list(new_data.columns)
                if 'Date' not in cols:
                    cols = cols + ['Date']
                if 'Symbol' not in cols:
                    cols = cols + ['Symbol']
                new_entries_df = new_entries_df[cols]
                print(f"Inserting new entries: {new_entries_df}")
                DB.mysql_update_table(mysql_engine, table_name, new_entries_df, check=True, insert=False, unknown_table=False, cols_type='values', temp=False, date_column=False, format_columns=False, primary_key=False, empty_table=False, fin_table=True, symbol=None)
                #new_entries_df.to_sql(name=table_name, con=connection, if_exists='append', index=False)
                #logger.info(f"Inserted {len(new_entries_df)} new entries into {table_name}.")

    except exc.SQLAlchemyError as e:
        logger.error(f"Error updating table '{table_name}': {e}")
        raise  # Re-raise to stop execution

def update_market_cap(db, engine, df):
    from bson import Int64
    """
    Placeholder for updating market cap in a separate table or location.
    This function should be implemented according to your specific requirements
    and database schema.  This version logs the data.
    """
    if not df.empty:
        logger.info(f"Market Cap Data to be updated: \n{df.to_string()}")
        for index,d in df.iterrows():
            DB.update_field(db.US_Stocks, d['Symbol'], 'Highlights.MarketCapitalization', Int64(int(d['marketCap'])))
            DB.update_field(db.US_Stocks, d['Symbol'], 'Highlights.MarketCapitalizationMln', round(d['marketCap']/1000000,2))

def main():
    """Main function to orchestrate the data update process."""
    start_time = time.time()
    mysql_engine = DB.open_sql_connection('localhost', 'vpetla', 'petla123', db='US_Stocks_Fin')
    price_engine = DB.open_sql_connection('localhost', 'root', 'petla123', db='US_Stocks')
    c = DB.open_db_client() # This is a placeholder.  Replace with your actual MongoDB client.
    db = c['Stocks']

    try:
        table_name = 'Nasdaq_Earnings_History'
        DB.mysql_check_n_create_table(mysql_engine, table_name, fin_table=True)
        if DB.mysql_exists_table(mysql_engine, table_name):
            table_cols = DB.mysql_get_columns_from_engine(mysql_engine, table_name)
            if 'price_change' not in table_cols:
                print("%s: Adding missing columns: %r"%(table_name, ['price_change']))
                miss = DB.mysql_add_columns(mysql_engine, table_name, ['price_change'], remove_spaces=False)
                if miss > 0:
                    PRINT_ERR("Failed to add %r columns to table %r" %(miss, table_name))
                    PRINT_ERR("Columns: ",['price_change'])
                    sys.exit(1)
 
        start_date = trading_day(dt.now().date() - timedelta(5))
        end_date = trading_day(dt.now().date() + timedelta(45))
        all_earnings_data = pd.DataFrame()

        #start_date = end_date = dt.now().date()-timedelta(1)
        d = start_date
        while d <= end_date:
            nasdaq_data = fetch_nasdaq_earnings(d)
            if nasdaq_data:
                earnings_data = parse_nasdaq_earnings_data(nasdaq_data, d) # Pass the date d
                if not earnings_data.empty:
                    all_earnings_data = pd.concat([all_earnings_data, earnings_data], ignore_index=True)
            d = trading_day(d + timedelta(3) if d.weekday() == 4 else d + timedelta(1))

        if all_earnings_data.empty:
            logger.info("No earnings data fetched from Nasdaq API.")
            return  # Exit if no data

        # Filter by market cap
        all_earnings_data = all_earnings_data[all_earnings_data['marketCap'] >= MARKET_CAP_THRESHOLD]

        # Get stock info from MongoDB
        symbols = all_earnings_data['Symbol'].unique().tolist()
        stock_info = get_stock_info_from_mongodb(db, symbols) if db else {}  # Pass the db
        for index, row in all_earnings_data.iterrows():
            symbol = row['Symbol']
            if symbol in stock_info:
                all_earnings_data.loc[index, 'Sector'] = stock_info[symbol]['Sector']
                all_earnings_data.loc[index, 'Industry'] = stock_info[symbol]['Industry']

        # Update last earnings dates in MongoDB
        if db: # check if db is not None
            update_stock_earnings_dates(db, all_earnings_data)

        # Fetch existing data and update
        existing_earnings_data = fetch_existing_earnings_data(mysql_engine, start_date, table_name)
        update_earnings_data_to_sql(mysql_engine, table_name, all_earnings_data, existing_earnings_data, mysql_engine)

        # Update market cap (placeholder)
        update_market_cap(db, price_engine, all_earnings_data[['Symbol', 'marketCap']])

        end_time = time.time()
        logger.info(f"Earnings data update process completed in {end_time - start_time:.2f} seconds.")
    except Exception as E:
        pass
    try:
        print("Calculating price changes")
        query = 'select `Date`, `Symbol`, `reportDate`, `time`, `price_change` from {} where price_change is NULL and reportDate <= CURDATE() order by reportDate'.format(table_name)
        pr_df = DB.read_from_sql(query, mysql_engine)
        pr_df['reportDate'] = pd.to_datetime(pr_df['reportDate'])
        pr_df = pr_df[pr_df['reportDate'] <= pd.to_datetime(dt.now().date())]
        pr_df['reportDate'] = pr_df['reportDate'].dt.strftime('%Y-%m-%d')

        pr_df['Index'] = pr_df['reportDate'] + '_' + pr_df['Symbol']
        pr_df.set_index('Index', inplace=True)
        for index, d in pr_df.iterrows():
            # If the results are announced after market. Consider the next day's price change.
            report_date = d['reportDate']
            price_table = DB.get_symbol_table_name(d['Symbol'])
            if not mysql_exists_table(price_engine, price_table):
                print("price data for %s doesn't exist" %(price_table))
                continue
            rdate = pd.to_datetime(d['reportDate'])
            if d['time'] == None:
                if rdate < dt.now().date():
                    prev = DB.get_previous_trading_day(rdate)
                    after = DB.get_next_trading_day(rdate)
                    query1 = 'select Date, `Adj Close` from {} where Date = \'{}\' order by Date desc limit 1'.format(price_table, str(prev.date()))
                    query2 = 'select Date, `Adj Close` from {} where Date = \'{}\' order by Date asc limit 1'.format(price_table, str(after.date()))
                else:
                    continue
            elif 'AfterMarket' in d['time']:
                if rdate >= dt.now().date():
                    continue
                prev = rdate
                after = DB.get_next_trading_day(rdate)
                query1 = 'select Date, `Adj Close` from {} where Date = \'{}\' order by Date desc limit 1'.format(price_table, str(prev.date()))
                query2 = 'select Date, `Adj Close` from {} where Date = \'{}\' order by Date asc limit 1'.format(price_table, str(after.date()))
            elif 'BeforeMarket' in d['time']:
                if rdate > dt.now().date():
                    continue
                prev = DB.get_previous_trading_day(rdate)
                after = rdate
                query1 = 'select Date, `Adj Close` from {} where Date = \'{}\' order by Date desc limit 1'.format(price_table, str(prev.date()))
                query2 = 'select Date, `Adj Close` from {} where Date = \'{}\' order by Date asc limit 1'.format(price_table, str(after.date()))
            else:
                continue
            # select Date, `Adj Close` from (select Date, `Adj Close` from STKDELL where Date < '2024-05-30' order by Date desc limit 2) as sub order by Date asc;
            #query1 = 'select Date, `Adj Close` from {} where Date < \'{}\' order by Date desc limit 1'.format(price_table, report_date)
            #query2 = 'select Date, `Adj Close` from {} where Date > \'{}\' order by Date asc limit 1'.format(price_table, report_date)
            df1 = DB.read_from_sql(query1, price_engine)
            df2 = DB.read_from_sql(query2, price_engine)

            #query='select Date, `Adj Close` from {} where Date > %r order by Date limit 1'.format(price_table) %(report_date)
            #pdf = read_from_sql(query, price_engine)

            if len(df1) == 0:
                change = 0
            elif len(df2) == 0:
                if dt.strptime(report_date, "%Y-%m-%d").date() > dt.now().date()-timedelta(3):
                    change = None
                    print("Change is None")
                else:
                    change = 0
                    print("Change is zero")
            else:
                change = DB.percent_change(df1.iloc[0]['Adj Close'], df2.iloc[0]['Adj Close'])
            pr_df.at[index,'price_change'] = change
            db.US_Stocks.update({'General.Code': d['Symbol']}, {'$set': {"price_change.ndaq_earnings_change": change}})
            db.US_Stocks.update({'General.Code': d['Symbol']}, {'$set': {"dates.ndaq_earnings_calc_date": dt.combine(dt.now(), dt.min.time())}})

            #if not pdf.empty:
            #    pr_df.at[index,'price_change'] = pdf.iloc[-1]['Day Change']

        if not pr_df.empty:
            pr_df = pr_df.drop(['reportDate'], axis=1)
            pr_df = pr_df.drop(['time'], axis=1)
            pr_df.index= pr_df['Date']
            pr_df = pr_df.dropna()
            pr_df['price_change'] = pr_df['price_change'].astype(float)
            DB.mysql_update_table(mysql_engine, table_name, pr_df, check=True, insert=False, unknown_table=False, cols_type='earnings', temp=False, date_column=False, format_columns=False, primary_key=False, empty_table=False, fin_table=True, symbol=None)

    finally:
        DB.close_db_client(c)
        DB.close_sql_connection(mysql_engine)
        DB.close_sql_connection(price_engine)
if __name__ == "__main__":
    main()

