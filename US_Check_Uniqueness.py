import DB
from datetime import datetime as dt

if __name__ == "__main__":
    print("Date: %r" %(str(dt.now())))
    DB.check_all_stocks_uniqueness()
    print("Date: %r" %(str(dt.now())))
 
