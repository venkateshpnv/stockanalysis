import DB
from datetime import datetime as dt

if __name__ == "__main__":
    print("Start Time: %r" %(str(dt.now())))
    DB.update_all_stock_betas('US', recession_only=True)
    print("End Time: %r" %(str(dt.now())))
