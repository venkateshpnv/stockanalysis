import internet
import DB
from common import *
if __name__ == "__main__":
    # Get today's price from yahoo and update db and hdf5
    DB.update_all_price_volume_db('India')
    ## Calculate and store price change
    #internet.update_all_stocks_price_change('India')
    ### send email
    #internet.send_email_price_changes('India')
