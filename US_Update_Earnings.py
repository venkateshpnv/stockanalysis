import DB
from datetime import datetime as dt

if __name__ == "__main__":
    today = dt.now()

    # On every weekend, get all stocks earnings information
    all = (False,True)[today.isoweekday() > 5]
    #all=True
    print("Date: %r" %(str(today)))
    DB.update_all_earnings(all=all)

    print("Date: %r" %(str(today)))
 
