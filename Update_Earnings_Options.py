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
                call_bought_premium DECIMAL(10,2),
                put_bought_premium DECIMAL(10,2),
                call_sold_premium DECIMAL(10,2),
                put_sold_premium DECIMAL(10,2),
                total_premium_paid DECIMAL(10,2),
                total_profit_loss_percent FLOAT,
                cost_of_one_contract DECIMAL(10,2),
                sold_for_one_contract DECIMAL(10,2),
                profit_on_one_contract DECIMAL(10,2),
                PRIMARY KEY (Symbol, reportDate)
            )
        """)
        conn.commit()

# 📅 Determine trade and sell dates
def get_trade_dates(report_date, time):
    rpt_dt = datetime.strptime(report_date, '%Y-%m-%d')
    trade_date = rpt_dt if time == 'AfterMarket' else rpt_dt - timedelta(days=1)
    #sell_date = rpt_dt + timedelta(days=1)
    sell_date = rpt_dt + timedelta(days=1) if time == 'AfterMarket' else rpt_dt
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

## 📈 Get option contracts
#def get_otm_contracts(conn, table, trade_date, price):
#    try:
#        df = pd.read_sql(f"SELECT * FROM `{table}` WHERE date='{trade_date}'", conn)
#        calls = df[(df['type'] == 'CALL') & (df['strike'] > price)].sort_values('strike')
#        puts = df[(df['type'] == 'PUT') & (df['strike'] < price)].sort_values('strike', ascending=False)
#        if calls.empty or puts.empty:
#            return None, None
#        return calls.iloc[0], puts.iloc[0]
#    except:
#        return None, None

# 📈 Get option contracts
def get_otm_contracts_nearest_expiry(conn, table, trade_date, report_date, price):
    try:
        df = pd.read_sql(f"SELECT * FROM `{table}` WHERE date='{trade_date}'", conn)
        df = df[df['expiration'] >= report_date]  # Filter future expirations
        if df.empty:
            return None, None

        # Find the nearest expiration date
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

# 🧮 Calculate trade metrics
def calculate_metrics(call, put, call_sell, put_sell):
    #call_buy = call['ask'] or call['mark'] or call['last']
    #put_buy = put['ask'] or put['mark'] or put['last']
    #call_sell_price = call_sell['bid'] or call_sell['mark'] or call_sell['last']
    #put_sell_price = put_sell['bid'] or put_sell['mark'] or put_sell['last']
    call_buy = (call['bid']+call['ask'])/2
    put_buy = (put['bid']+put['ask'])/2
    call_sell_price = (call_sell['bid'] + call_sell['ask']) / 2
    put_sell_price = (put_sell['bid'] + put_sell['ask']) / 2

    if any(pd.isna(x) for x in [call_buy, put_buy, call_sell_price, put_sell_price]):
        return None

    total_paid = call_buy + put_buy
    total_earned = call_sell_price + put_sell_price
    profit = total_earned - total_paid
    percent = (profit / total_paid) * 100 if total_paid else 0
    cost_contract = total_paid * 100
    profit_contract = profit * 100
    sold = cost_contract + profit_contract

    return (
        call.contractID, put.contractID,
        do_round(call.strike), do_round(put.strike),
        do_round(call_buy), do_round(put_buy),
        do_round(call_sell_price), do_round(put_sell_price),
        do_round(total_paid), do_round(percent),
        do_round(cost_contract), do_round(sold), do_round(profit_contract)
    )

def do_round(val):
    return float(round(val,2))

# 📝 Insert results
def insert_results(conn, results):
    with conn.cursor() as cur:
        cur.executemany("""
            INSERT IGNORE INTO Nasdaq_Earnings_Options (
                Symbol, Date, reportDate,
                call_contractID, put_contractID,
                call_strike, put_strike,
                call_bought_premium, put_bought_premium,
                call_sold_premium, put_sold_premium,
                total_premium_paid, total_profit_loss_percent,
                cost_of_one_contract, sold_for_one_contract, profit_on_one_contract
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, results)
        conn.commit()

# 🚀 Main function
def main():
    conn_fin = connect_db('US_Stocks_Fin', '10.89.45.241', 'vpetla', 'petla123')
    conn_opt = connect_db('US_Stocks_Options', '10.89.45.31', 'vpetla', 'petla123')
    conn_price = connect_db('US_Stocks', '10.89.45.241', 'vpetla', 'petla123')

    create_output_table(conn_fin)

    today = str(datetime.now().date())
    query = f"SELECT * FROM Nasdaq_Earnings_History where reportDate > \'2008-01-01\' and reportDate <= \'{today}\' order by marketCap desc"
    #query = f"SELECT * FROM Nasdaq_Earnings_History where reportDate > \'2008-01-01\' and reportDate <= \'{today}\' and symbol=\'ANET\' order by marketCap desc"
    earnings = pd.read_sql(query, conn_fin)
    #earnings = pd.read_sql(f"SELECT * FROM Nasdaq_Earnings_History where reportDate > \'2008-01-01\' and reportDate <= {today} and symbol=\'ANET\' order by marketCap desc", conn_fin)
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

        price, sell_open = get_stock_price(conn_price, table_name, trade_date, sell_date)
        if price is None:
            continue

        #call, put = get_otm_contracts(conn_opt, table_name, trade_date, price)
        call, put = get_otm_contracts_nearest_expiry(conn_opt, table_name, trade_date, datetime.strptime(rpt_date, "%Y-%m-%d").date(), price)
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

