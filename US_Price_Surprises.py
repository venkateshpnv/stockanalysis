import internet
from common import *
if __name__ == "__main__":
    internet.price_surprises('US', 0.10, WEEK | MONTH | QUARTER, 'COLD', 'SYNC_DB')
    #internet.price_surprises('US', 0.10, MONTH | QUARTER | YEAR, 'COLD', 'SYNC_DB')
