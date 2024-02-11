import DB
import internet
from datetime import datetime as dt

if __name__ == "__main__":
    print("Date: %r" %(str(dt.now())))
    DB.update_symbol_changes()
    print("Date: %r" %(str(dt.now())))
 
