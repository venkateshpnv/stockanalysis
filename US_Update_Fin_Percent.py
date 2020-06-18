# Read fin statements from mongodb, calculate and store the percentage changes in mysql.

import DB

if __name__ == "__main__":
    DB.update_all_US_fin_percent_change()
