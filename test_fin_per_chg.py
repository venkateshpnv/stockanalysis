from DB import *
import pandas as pd
from common import *

db = open_db('Stocks')
stocks = db.US_Stocks.find({'bscs.symbol':'AAPL'}, no_cursor_timeout=True).batch_size(10).sort([["sno",1]])
stk = stocks[0]

income_stmt=stk['fig']['financial-statements']['income-statement']
balance_stmt=stk['fig']['financial-statements']['balance-sheet']
cash_stmt=stk['fig']['financial-statements']['cash-flow']

try:
    del balance_stmt['date']
    #del dates[dates.index('date')]
except:
    pass
try:
    del income_stmt['date']
except:
    pass
try:
    del cash_stmt['date']
except:
    pass

dates=list(balance_stmt.keys())

entry={}
for d in dates:
    stmt = balance_stmt[d]
    fields = list(stmt.keys())
    for f in fields:
        entry.update(stmt.pop(f,{}))
    balance_stmt[d] = entry
    entry = {}

income_df=pd.DataFrame.from_dict(income_stmt)
#del income_df['date']
income_dft=pd.DataFrame.transpose(income_df)
print(income_dft)
income_dft.sort_index(ascending=True, inplace=True)
print(income_dft)


#pretty_print(balance_stmt)
df=pd.DataFrame.from_dict(balance_stmt)
#del df['date']
dft=pd.DataFrame.transpose(df)
print(dft)
dft.sort_index(ascending=True, inplace=True)
print(dft)

#dates=list(cash_stmt.keys())
#try:
#    del dates[dates.index('date')]
#except:
#    pass

entry={}
for d in dates:
    stmt = cash_stmt[d]
    fields = list(stmt.keys())
    for f in fields:
        entry.update(stmt.pop(f,{}))
    cash_stmt[d] = entry
    entry = {}

#pretty_print(cash_stmt)
df=pd.DataFrame.from_dict(cash_stmt)
#del df['date']
dft=pd.DataFrame.transpose(df)
print(dft)
dft.sort_index(ascending=True, inplace=True)
print(dft)
