import pymysql
import pandas as pd
from datetime import datetime, timedelta

# 🔌 Database connections
def connect_db(db_name, host, user, password):
    return pymysql.connect(host, user, password, db=db_name)

# 🧱 Ensure output table exists
def create_output_table(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS Nasdaq_Earnings_Options (
                Symbol VARCHAR(12),
                Date VARCHAR(12),
                reportDate VARCHAR(12),
                call_contractID VARCHAR(30),
                put_contractID VARCHAR(30),
                call_strike DECIMAL(10,2),
                put_strike DECIMAL(10,2),
                straddle_total_paid DECIMAL(10,2),
                straddle_total_earned DECIMAL(10,2),
                straddle_profit DECIMAL(10,2),
                straddle_profit_percent DECIMAL(10,2),
                call_buy_price DECIMAL(10,2),
                call_sell_price DECIMAL(10,2),
                call_profit DECIMAL(10,2),
                call_profit_percent DECIMAL(10,2),
                put_buy_price DECIMAL(10,2),
                put_sell_price DECIMAL(10,2),
                put_profit DECIMAL(10,2),
                put_profit_percent DECIMAL(10,2),
                PRIMARY KEY (Symbol, reportDate)
            )
        """)
        conn.commit()

# 📅 Determine trade and sell dates
def get_trade_dates(report_date, time):
    rpt_dt = datetime.strptime(report_date, '%Y-%m-%d')
    trade_date = rpt_dt if time == 'AfterMarket' else rpt_dt - timedelta(days=1)
    sell_date = rpt_dt + timedelta(days=1)
    #sell_date = rpt_dt + timedelta(days=1) if time == 'AfterMarket' else rpt_dt
    return trade_date.strftime('%Y-%m-%d'), sell_date.strftime('%Y-%m-%d')

# 💵 Get stock price data
def get_stock_price(conn, table, trade_date, sell_date):
    try:
        df = pd.read_sql(f"SELECT * FROM `{table}` WHERE Date IN ('{trade_date}', '{sell_date}')", conn, index_col='Date')
        if trade_date not in df.index or sell_date not in df.index:
            return None, None
        price = (df.loc[trade_date]['Open'] + df.loc[trade_date]['Close']) / 2
        sell_open = df.loc[sell_date]['Open']
        return price, sell_open
    except:
        return None, None

# 📈 Get nearest expiry OTM contracts
def get_otm_contracts_nearest_expiry(conn, table, trade_date, report_date, price):
    try:
        report_date = datetime.strptime(report_date, "%Y-%m-%d").date()
        df = pd.read_sql(f"SELECT * FROM `{table}` WHERE date='{trade_date}'", conn)
        df = df[df['expiration'] >= report_date]
        if df.empty:
            return None, None

        nearest_exp = df['expiration'].min()
        df_exp = df[df['expiration'] == nearest_exp]

        calls = df_exp[(df_exp['type'] == 'CALL') & (df_exp['strike'] > price)].sort_values('strike')
        puts = df_exp[(df_exp['type'] == 'PUT') & (df_exp['strike'] < price)].sort_values('strike', ascending=False)

        if calls.empty or puts.empty:
            return None, None

        return calls.iloc[0], puts.iloc[0]
    except:
        return None, None

# 💰 Get sell premiums
def get_sell_premiums(conn, table, sell_date, call_id, put_id):
    try:
        df = pd.read_sql(f"""
            SELECT * FROM `{table}` 
            WHERE date='{sell_date}' AND contractID IN ('{call_id}', '{put_id}')
        """, conn)
        if df.empty or call_id not in df.contractID.values or put_id not in df.contractID.values:
            return None, None
        call = df[df['contractID'] == call_id].iloc[0]
        put = df[df['contractID'] == put_id].iloc[0]
        return call, put
    except:
        return None, None

# 🧮 Calculate combined and individual metrics
def calculate_metrics(call, put, call_sell, put_sell):
#    call_buy = call['ask'] or call['mark'] or call['last']
#    put_buy = put['ask'] or put['mark'] or put['last']
#    call_sell_price = call['mark'] or (call['bid'] + call['ask']) / 2 or call['last']
#    put_sell_price = put['mark'] or (put['bid'] + put['ask']) / 2 or put['last']
    call_buy_price = (call['bid']+call['ask'])/2
    put_buy_price = (put['bid']+put['ask'])/2
    call_sell_price = (call_sell['bid'] + call_sell['ask']) / 2
    put_sell_price = (put_sell['bid'] + put_sell['ask']) / 2

    if any(pd.isna(x) for x in [call_buy_price, put_buy_price, call_sell_price, put_sell_price]):
        return None

    # Combined straddle
    straddle_total_paid = call_buy_price + put_buy_price
    straddle_total_earned = call_sell_price + put_sell_price
    straddle_profit = straddle_total_earned - straddle_total_paid
    
    straddle_profit_percent = (straddle_profit / straddle_total_paid) * 100 if straddle_total_paid else 0
    straddle_cost_contract = straddle_total_paid * 100
    straddle_profit_contract = straddle_profit * 100

    # Individual legs
    call_profit = call_sell_price - call_buy_price
    put_profit = put_sell_price - put_buy_price
    call_profit_percent = (call_profit / call_buy_price) * 100 if call_buy_price else 0
    put_profit_percent = (put_profit / put_buy_price) * 100 if put_buy_price else 0
    call_cost = call_buy_price * 100
    put_cost = put_buy_price * 100
    call_profit_contract = call_profit * 100
    put_profit_contract = put_profit * 100

    return (
        call.contractID, 
        put.contractID,
        do_round(call.strike), 
        do_round(put.strike),
        do_round(straddle_total_paid), 
        do_round(straddle_total_earned), 
        do_round(straddle_profit),
        do_round(straddle_profit_percent),
        do_round(call_buy_price), 
        do_round(call_sell_price), 
        do_round(call_profit), 
        do_round(call_profit_percent), 
        do_round(put_buy_price),
        do_round(put_sell_price),
        do_round(put_profit),
        do_round(put_profit_percent)
    )

def do_round(val):
    return float(round(val,2))

# 📝 Insert results
def insert_results(conn, results):
    with conn.cursor() as cur:
        cur.executemany("""
            INSERT IGNORE INTO Nasdaq_Earnings_Options (
                Symbol, 
                Date, 
                reportDate,
                call_contractID, 
                put_contractID,
                call_strike, 
                put_strike,
                straddle_total_paid, 
                straddle_total_earned,
                straddle_profit,
                straddle_profit_percent,
                call_buy_price,  
                call_sell_price,
                call_profit,
                call_profit_percent,
                put_buy_price,
                put_sell_price,
                put_profit,
                put_profit_percent
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, results)
        conn.commit()

# 🚀 Main function
def main():
    conn_fin = connect_db('US_Stocks_Fin', '10.89.45.241', 'vpetla', 'petla123')
    conn_opt = connect_db('US_Stocks_Options', '10.89.45.31', 'vpetla', 'petla123')
    conn_price = connect_db('US_Stocks', '10.89.45.241', 'vpetla', 'petla123')

    create_output_table(conn_fin)

    #earnings = pd.read_sql("SELECT * FROM Nasdaq_Earnings_History", conn_fin)
    #existing = pd.read_sql("SELECT Symbol, reportDate FROM Nasdaq_Earnings_Options", conn_fin)
    today = str(datetime.now().date())
    query = f"SELECT * FROM Nasdaq_Earnings_History where reportDate > \'2008-01-01\' and reportDate <= \'{today}\' order by marketCap desc"
    #query = f"SELECT * FROM Nasdaq_Earnings_History where reportDate > \'2008-01-01\' and reportDate <= \'{today}\' and symbol=\'ANET\' order by marketCap desc"
    earnings = pd.read_sql(query, conn_fin)
    existing = pd.read_sql("SELECT Symbol, reportDate FROM Nasdaq_Earnings_Options", conn_fin)
    existing_set = set(zip(existing.Symbol, existing.reportDate))
    today = datetime.today().strftime('%Y-%m-%d')

    results = []

    for _, row in earnings.iterrows():
        symbol, rpt_date, time = row['Symbol'], row['reportDate'], row['time']
        if not rpt_date or (symbol, rpt_date) in existing_set or rpt_date > today:
            continue

        table_name = f"STK{symbol}"
        trade_date, sell_date = get_trade_dates(rpt_date, time)
        print(f"Symbol : {symbol}, report_date: {rpt_date}, buy_date: {trade_date}, sell_date: {sell_date}, time: {time}")

        price, sell_open = get_stock_price(conn_price, table_name, trade_date, sell_date)
        if price is None:
            continue

        call, put = get_otm_contracts_nearest_expiry(conn_opt, table_name, trade_date, rpt_date, price)
        if call is None or put is None:
            continue

        call_sell, put_sell = get_sell_premiums(conn_opt, table_name, sell_date, call.contractID, put.contractID)
        if call_sell is None or put_sell is None:
            continue

        metrics = calculate_metrics(call, put, call_sell, put_sell)
        if metrics is None:
            continue

        results.append((symbol, trade_date, rpt_date) + metrics)

    insert_results(conn_fin, results)
    print(f"Inserted {len(results)} new entries.")

if __name__ == "__main__":
    main()
