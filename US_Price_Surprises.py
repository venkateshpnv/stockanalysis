import internet
from common import *
if __name__ == "__main__":
    #internet.price_surprises('US', 0.10, ALL, 'SYNC_DB', 'NO_EXCEL')
    internet.price_surprises('US', 0.10, DAY, 'NO_SYNC_DB', 'EXCEL')
