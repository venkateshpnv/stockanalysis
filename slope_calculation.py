#from calculations import calculate_dcf_all_stocks
import DB
#import internet
from common import *
#from excel import *
#from datastructures import Stock
#import hdf5
import numpy as np
from sklearn.preprocessing import MinMaxScaler, MaxAbsScaler

def US_main():
    pd.set_option('float_format', '{:f}'.format)
    mysql_engine = DB.open_sql_connection('localhost', 'root', 'petla123', db='US_Stocks_Fin')
    sym='ZM'
    duration='yearly'
    if len(sys.argv) >= 2:
        sym = sys.argv[1]
    if len(sys.argv) == 3:
        duration = sys.argv[2]

    query = "select Date, totalRevenue from Income_Statement_{} where Symbol=\'{}\'".format(duration, sym)
    df = DB.read_from_sql(query, mysql_engine)
    df = df.iloc[-4:]
    slopes = pd.DataFrame()
    slopes['slope'] = np.nan
    slopes['error'] = np.nan
    slopes_scaler = pd.DataFrame()
    slopes_scaler['slope'] = np.nan
    slopes_scaler['error'] = np.nan
    rdf = df

    scaler = MinMaxScaler()
    df_min_max = scaler.fit_transform(df[['totalRevenue']])
    df_min_max = pd.DataFrame(columns=['totalRevenue'], data=df_min_max, index=df.index)
    scaler = MaxAbsScaler()
    df_max_abs = scaler.fit_transform(df[['totalRevenue']])
    df_max_abs = pd.DataFrame(columns=['totalRevenue'], data=df_max_abs, index=df.index)

    df_normalize = (df[['totalRevenue']] - df[['totalRevenue']].min())/(df[['totalRevenue']].max() - df[['totalRevenue']].min())
    #df = (df - df.mean())/df.std()
    for i, d in df.iloc[:-1].iterrows():
        slopes_scaler.at[i,'slope'], slopes_scaler.at[i,'error'] = calculate_slope(df.loc[i:][['totalRevenue']])
    #for i in range(len(df.iloc[:-1])):
    #    tup = calculate_slope(df.iloc[i:i+2][['totalRevenue']])
    #    slopes_scaler.loc[slopes_scaler.shape[0]]=list(tup)


    #for i, d in df.iloc[:-1].iterrows():
    #    slopes.at[i,'slope'], slopes.at[i,'error'] = calculate_slope(df.loc[i:][['totalRevenue']], scaler=False)

    slopes_scaler['slope'] = slopes_scaler['slope'] * 100
    slope,nrmse = calculate_slope(slopes_scaler[['slope']], transform=False)
    slope = slope * 1000
    if isinstance(nrmse, pd.Series):    
        nrmse = nrmse[0]
    df['totalRevenue'] = df['totalRevenue'].apply(df_format)
    print("Symbol: %s" %(sym))
    df['max_abs']=df_max_abs
    df = df.join(slopes_scaler['slope'])
    print(df)
    print("slope: %r" %(slope))
    DB.close_sql_connection(mysql_engine)
US_main()


