import DB
from datetime import datetime as dt
from common import is_holiday
import sys

if __name__ == "__main__":
    print("Date: %r" %(str(dt.now().date())))
    if is_holiday():
        print("Holiday today")
        sys.exit()

    DB.update_all_short_interests()
 
