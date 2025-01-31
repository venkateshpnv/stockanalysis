import DB
from datetime import datetime as dt
from common import is_holiday
import sys

if __name__ == "__main__":
    today = dt.now()

    # On every weekend, get all stocks splits information
    all = (False,True)[today.isoweekday() > 5]
    print("Date: %r" %(str(today)))
    if is_holiday():
        print("Holiday today")
        sys.exit()

    DB.update_all_splits(all=all)

    print("Date: %r" %(str(today)))
 
