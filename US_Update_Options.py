import DB
from datetime import datetime as dt

if __name__ == "__main__":
    print("Date: %r" %(str(dt.now())))
    DB.update_all_put_call_ratios()
    print("Date: %r" %(str(dt.now())))
 
