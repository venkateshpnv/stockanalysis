import DB
from datetime import datetime as dt

if __name__ == "__main__":
    today = dt.now().date()

    # On every weekend, get all stocks dividend information
    all = (False,True)[today.isoweekday() > 5]
    print("Date: %r" %(str(today)))
    DB.update_all_dividends(all=all)

    print("Date: %r" %(str(today)))
 
