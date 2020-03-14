from DB import *
import pandas as pd
from common import *

db = open_db('Stocks')
stocks = db.US_Stocks.find({'bscs.symbol':'AAPL'}, no_cursor_timeout=True).batch_size(10).sort([["sno",1]])
stk = stocks[0]

balance_stmt=stk['fig']['financial-statements']['balance-sheet']
cash_stmt=stk['fig']['financial-statements']['cash-flow']

dates=list(balance_stmt.keys())
try:
    del dates[dates.index('date')]
except:
    pass

entry={}
for d in dates:
    stmt = balance_stmt[d]
    fields = list(stmt.keys())
    for f in fields:
        entry.update(stmt.pop(f,{}))
    balance_stmt[d] = entry
    entry = {}

pretty_print(balance_stmt)

dates=list(cash_stmt.keys())
try:
    del dates[dates.index('date')]
except:
    pass

entry={}
for d in dates:
    stmt = cash_stmt[d]
    fields = list(stmt.keys())
    for f in fields:
        entry.update(stmt.pop(f,{}))
    cash_stmt[d] = entry
    entry = {}

pretty_print(cash_stmt)
