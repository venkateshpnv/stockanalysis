import DB
from datetime import datetime as dt
from common import is_holiday
import sys

if __name__ == "__main__":
    today = dt.now()
    print("Date: %r" %(str(today)))
    if is_holiday():
        print("Holiday today")
        sys.exit()

    DB.update_nasdaq_all_earnings()

    print("Date: %r" %(str(today)))
 
