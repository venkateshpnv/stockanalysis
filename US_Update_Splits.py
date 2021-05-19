import DB
from datetime import datetime as dt

if __name__ == "__main__":
    print("Date: %r" %(str(dt.now().date())))
    DB.update_all_splits()
 
