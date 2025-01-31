import DB
import pdb
from common import is_holiday
import sys

if __name__ == "__main__":
    if is_holiday():
        print("Holiday today")
        sys.exit()

    DB.build_US_all_EPS()
