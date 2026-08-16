import DB
from datastructures import major_exchanges
from sqlalchemy import create_engine, inspect, text
import sqlalchemy

c  = DB.open_db_client()
db = c['Stocks']
params_engine = DB.open_sql_connection('localhost', 'root', 'petla123', db='US_Tech_Params')
stocks=db.US_Stocks.find({"$and":[ \
                                    {'General.Type':'Common Stock'}, \
                                    {'General.IsDelisted': False}, \
                                    {"$or": [\
                                                {'General.Exchange':{"$in":major_exchanges}},\
                                                {"$and": [ \
                                                            {'General.Exchange':{"$nin":major_exchanges}},\
                                                            {'bscs.tracking':{'$exists':True}}, \
                                                        ] \
                                                },\
                                            ]\
                                    },\
                                    {'$or':[\
                                            {'failcount.mysql_price_failcount': {"$exists": False}},\
                                            {'failcount.mysql_price_failcount': {'$eq': 0}},\
                                            ]\
                                    },\
                                    ##{'failcount.mysql_price_failcount': {'$lt': MAX_FAIL_COUNT}},\
                                    #{'dates.technicals_pull_date': {'$gte':get_latest_trading_day()}}, \
                                    #{'$or':[\
                                    #        {'technicals.date': {"$exists": False}},\
                                    #        {'technicals.date':{'$lt': get_latest_trading_day()}}
                                    #        ]\
                                    #},\
                                    #{'dates.mysql_price_pull_success':True}, \
                                    #{'dates.mysql_price_date':{'$gte': get_latest_trading_day()}}
                                ]}).batch_size(10).sort([["General.Code",-1]]).allow_disk_use(True)
print("Tech analysis, total stocks:", stocks.count())
stks = []
for i, stk in enumerate(stocks):
    stks.append(stk['bscs']['symbol'])

params_inspector = inspect(params_engine)
params_tables = params_inspector.get_table_names()
params_stks = [s[3:] for s in params_tables]
cnt = 0
with params_engine.connect() as conn:
    for i, stk in enumerate(params_stks):
        if stk not in stks:
            print(f"{stk} not in required")
            cnt = cnt + 1
            try:
                table='STK'+stk
                conn.execute(text(f"DROP TABLE `{table}`"))
            except Exception as e:
                print(f"  - Could not drop column `{table}`: {e}")



print(f"Total unnecessary tables: {cnt}")
DB.close_db_client(c)
DB.close_sql_connection(params_engine)
