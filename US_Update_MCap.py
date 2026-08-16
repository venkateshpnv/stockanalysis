import DB
from datastructures import major_exchanges
from bson import Int64
import time
import requests

API_KEY='MoBAdAwyPhgpROvmDE4aUCC0Zbk2onlN'

# Step 2: Batch tickers into chunks (FMP allows ~100 per call)
def chunks(lst, n):
    """Yield successive n-sized chunks from list."""
    for i in range(0, len(lst), n):
        yield lst[i:i+n]

def update_mcap():
    c = DB.open_db_client()
    db = c['Stocks']
    try:
        url = f"https://financialmodelingprep.com/api/v3/stock/list?apikey={API_KEY}"
        response = requests.get(url)
        symbols_data = response.json()
        
        print(f"Total symbols fetched: {len(symbols_data)}")
        
        # Extract just the ticker symbols
        #symbols = [s["symbol"] for s in symbols_data if s.get("symbol")]
        us_exchanges = {"NASDAQ", "NYSE", "AMEX"}
        symbols = [s["symbol"] for s in symbols_data if s.get("exchangeShortName") in us_exchanges]

        symbols = [
                        s["symbol"]
                        for s in symbols_data
                        if s.get("exchangeShortName") in us_exchanges and s.get("type") == "stock"
                    ]

 
        #items = db.US_Stocks.find({"$and" : [ \
        #                                        #{"$or": [\
        #                                        #            {"dates.mysql_price_date": {"$exists": False }},\
        #                                        #            #{"dates.mysql_price_date": {"$lte": DB.get_latest_trading_day()}}\
        #                                        #            {"dates.mysql_price_date": {"$lt": DB.get_latest_trading_day()}}\
        #                                        #        ]\
        #                                        #},\
        #                                        #{"$or": [\
        #                                        #            {"dates.mysql_price_pull_date": {"$exists": False }},\
        #                                        #            {"dates.mysql_price_pull_date": {"$lt": DB.get_latest_trading_day()}}\
        #                                        #            #{"dates.mysql_price_pull_date": {"$lte": DB.get_latest_trading_day()}}\
        #                                        #        ]\
        #                                        #},\
        #                                        {"General.IsDelisted": False},\
        #                                        {'General.Type':'Common Stock'},\
        #                                        {"$or": [\
        #                                                    {'General.Exchange':{"$in":major_exchanges}},\
        #                                                    {"$and": [ \
        #                                                                {'General.Exchange':{"$nin":major_exchanges}},\
        #                                                                {'bscs.tracking':{'$exists':True}}, \
        #                                                            ] \
        #                                                    },\
        #                                                ]\
        #                                        },\
        #                                        #{'dates.technicals_pull_date': {'$gte':get_latest_trading_day()}},\
        #                                        {"$or": [\
        #                                                    {'failcount.mysql_price_failcount': {"$exists": False}},\
        #                                                    #{'failcount.mysql_price_failcount': {'$eq': 0}},\
        #                                                    {'failcount.mysql_price_failcount': {'$lt': DB.MAX_FAIL_COUNT}},\
        #                                                ]\
        #                                        }
        #                                    ]\
        #                            }\
        #                            ).batch_size(10).sort([["failcount.mysql_price_failcount",1]]).allow_disk_use(True)

        #symbols = []
        #for i in items:
        #    symbols.append(i['General']['Code'])

        for batch in chunks(symbols, 100):  # adjust batch size if needed
            symbols_str = ",".join(batch)
            quote_url = f"https://financialmodelingprep.com/api/v3/quote/{symbols_str}?apikey={API_KEY}"

            try:
                resp = requests.get(quote_url)
                data = resp.json()
                for item in data:
                    #stocks_with_marketcap.append({
                    #    "symbol": item.get("symbol"),
                    #    "name": item.get("name"),
                    #    "exchange": item.get("exchange"),
                    #    "marketCap": item.get("marketCap")
                    #})
                    symbol = item.get("symbol")
                    if symbol == 'FIC':
                        print('FIC')
                    marketCap = item.get("marketCap")
                    print("Updating mcap for %s: %s" %(item['symbol'], item['name']))
                    DB.update_field(db.US_Stocks, symbol, 'Highlights.MarketCapitalization', Int64(int(marketCap)))
                    DB.update_field(db.US_Stocks, symbol, 'Highlights.MarketCapitalizationMln', round(int(marketCap)/1000000,2))
                    DB.update_field(db.US_Stocks, symbol, 'General.Code', symbol)
                    DB.update_field(db.US_Stocks, symbol, 'General.Name', item['name'])
                    DB.update_field(db.US_Stocks, symbol, 'General.IsDelisted', False)
                    DB.update_field(db.US_Stocks, symbol, 'General.Type','Common Stock')
                    DB.update_field(db.US_Stocks, symbol, 'General.Exchange',item['exchange'])
            except Exception as e:
                print(f"Error fetching batch {batch[:3]}...: {e}")

            # respect API limits — free tier = 250 requests/day
            time.sleep(0.5)

    finally:
        DB.close_db_client(c)

if __name__ == "__main__":
    update_mcap()
