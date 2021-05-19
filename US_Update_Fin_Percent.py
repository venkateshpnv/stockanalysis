# Read fin statements from mongodb, calculate and store the percentage changes in mysql.

import DB
from datetime import datetime as dt

if __name__ == "__main__":
    print("Date: %r" %(str(dt.now().date())))
    DB.update_all_US_fin_percent_change()
