from sqlalchemy import create_engine, inspect, text
import sqlalchemy
import pandas as pd
from DB import open_sql_connection, mysql_get_columns_from_engine

# DB credentials and setup
user = "vpetla"
password = "petla123"
host1 = "10.89.45.241"
host2 = "10.89.45.83"
stocks_db = "US_Stocks"
params_db = "US_Tech_Params"

# Connect to databases
stocks_engine = create_engine(f"mysql+pymysql://{user}:{password}@{host1}/{stocks_db}")
params_engine = create_engine(f"mysql+pymysql://{user}:{password}@{host1}/{params_db}")
#params_engine = open_sql_connection(host2, user, password, db=params_db)

# Percent-change columns we care about
percent_columns = [
    'Day Change', 'Five Year Change', 'Half Year Change', 'Month Change',
    'Quarter Change', 'Ten Year Change', 'Two Week Change',
    'Week Change', 'Whole Change', 'YTD Change', 'Year Change'
]

# Create target database if not exists
with stocks_engine.connect() as conn:
    conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {params_db}"))

inspector = inspect(stocks_engine)
tables = inspector.get_table_names()

params_inspector = inspect(params_engine)
params_tables = params_inspector.get_table_names()

for i, table in enumerate(tables):
    ## If table already exists, skip and go to next table
    #if table in params_tables:
    #    print(f"{i}:table {table} exists, skipping")
    #    continue
    print(f"{i}:Processing table {table}")

    ## Get actual columns from the current table
    #actual_columns = [col["name"] for col in inspector.get_columns(table)]

    ## Find which percent change columns exist
    #present_columns = [col for col in percent_columns if col in actual_columns]
    #if not present_columns:
    #    print(f"  - No percent columns found in {table}. Skipping.")
    #    continue

    ## Step 1: Load existing percent columns
    #columns_to_select = ['Date'] + present_columns
    #select_clause = ", ".join(f"`{col}`" for col in columns_to_select)

    #with stocks_engine.connect() as conn:
    #    result = conn.execute(text(f"SELECT {select_clause} FROM `{table}`"))
    #    df = pd.DataFrame(result.fetchall(), columns=result.keys())

    ## Step 2: Save to new DB
    #df.to_sql(table, params_engine, if_exists='replace', index=False, dtype={'Date': sqlalchemy.String(12)})

    ## Step 2.1: Add primary key
    #with params_engine.connect() as conn:
    #    try:
    #        conn.execute(text(f"""
    #            ALTER TABLE `{table}` ADD PRIMARY KEY (`Date`)
    #        """))
    #    except Exception as e:
    #        print(f"  - Could not add primary key to {table}: {e}")

    # Step 3: Drop only present percent columns from original table
    table_cols = mysql_get_columns_from_engine(stocks_engine, table)
    with stocks_engine.connect() as conn:
        for col in percent_columns:
            if col not in table_cols:
                print(f"col {col} not in table {table}, skipping drop")
                continue
            try:
                conn.execute(text(f"ALTER TABLE `{table}` DROP COLUMN `{col}`"))
            except Exception as e:
                print(f"  - Could not drop column `{col}` from `{table}`: {e}")

print("✔ Migration complete.")
