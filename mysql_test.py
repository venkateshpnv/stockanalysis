from DB import *
import pandas as pd
from sqlalchemy import *
import sqlalchemy

df=pd.read_excel("/tmp/df.xls")
colums=list(df.columns)
del colums[1]
df=df[colums]
df.index = df['Date']
mysql_engine = sqlalchemy.create_engine("mysql+pymysql://root:petla123@localhost:3306/US_Stocks")
mysql_update_table(mysql_engine, 'STKSP500', df, check=False)

