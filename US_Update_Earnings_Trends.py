import DB
from datetime import datetime as dt

if __name__ == "__main__":
    today = dt.now()

    print("Date: %r" %(str(today)))
    DB.update_all_earnings_trend()

    print("Date: %r" %(str(today)))
 
