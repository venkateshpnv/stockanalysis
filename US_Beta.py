import DB
from datetime import datetime as dt
from common import is_holiday
import sys

if __name__ == "__main__":
    print("Start Time: %r" %(str(dt.now())))
    if is_holiday():
        print("Holiday today")
        sys.exit()

    DB.update_all_stock_betas('US')
    print("End Time: %r" %(str(dt.now())))
