import DB
import internet
from datetime import datetime as dt

if __name__ == "__main__":
    print("Date: %r" %(str(dt.now())))
    DB.update_all_crypto_fundamentals()
    DB.update_all_crypto_prices()
    DB.update_all_crypto_technicals()
    internet.update_all_crypto_price_change()
    print("Date: %r" %(str(dt.now())))
 
