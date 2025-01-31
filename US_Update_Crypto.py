import DB
import internet
from datetime import datetime as dt
from common import is_holiday
import sys

if __name__ == "__main__":
    print("Date: %r" %(str(dt.now())))
    if is_holiday():
        print("Holiday today")
        sys.exit()

    DB.update_all_crypto_fundamentals()
    DB.update_all_crypto_prices()
    DB.update_all_crypto_technicals()
    internet.update_all_crypto_price_change()
    print("Date: %r" %(str(dt.now())))
 
