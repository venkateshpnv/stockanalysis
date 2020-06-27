# Read the latest updated financial statements information from barchart and update the mongodb

import DB
import pdb

if __name__ == "__main__":
    DB.update_US_all_stock_information()
