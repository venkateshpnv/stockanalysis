from calculations import calculate_dcf_all_stocks

if __name__ == "__main__":
    calculate_dcf_all_stocks('US', 5, 'NO_CALC', 'ALL', 'BETA', 'NO_SYNC', 'EXCEL',prices_only=True,radar_stocks=True)
    #calculate_dcf_all_stocks('US', 5, 'COLD', 'ALL', 'BETA', 'SYNC_DB', 'EXCEL')
 
