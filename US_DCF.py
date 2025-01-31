from calculations import calculate_dcf_all_stocks
from common import is_holiday
import sys

if __name__ == "__main__":
    if is_holiday():
        print("Holiday today")
        sys.exit()

    #calculate_dcf_all_stocks('US', 5, 'NO_CALC', 'ALL', 'BETA', 'NO_SYNC', 'EXCEL')
    calculate_dcf_all_stocks('US', 5, 'COLD', 'ALL', 'BETA', 'SYNC_DB', 'EXCEL')
 
