from collections import namedtuple
#import namedtupled

import json

def _json_object_hook(d):
    return namedtuple('X', d.keys())(*d.values())

def json2obj(data):
    return json.loads(data, object_hook=_json_object_hook)

def build_json_object(stock):
    y=json.dumps(stock, indent=4, default=lambda x:x.__dict__)
    #print(y)
    obj = json.loads(y)
    obj['fig']['Years'] = stock.fig.Years
    obj['fig']['Sales'] = stock.fig.Sales
    obj['fig']['PBT'] = stock.fig.PBT
    obj['fig']['Taxes'] = stock.fig.Taxes
    obj['fig']['EBIT'] = stock.fig.EBIT
    obj['fig']['PAT'] = stock.fig.PAT
    obj['fig']['PAT_M'] = stock.fig.PAT_M
    obj['fig']['EPS'] = stock.fig.EPS
    obj['fig']['CASH'] = stock.fig.CASH
    obj['fig']['BOOK'] = stock.fig.BOOK
    obj['fig']['ROE'] = stock.fig.ROE
    obj['fig']['ROA'] = stock.fig.ROA
    obj['fig']['ROCE'] = stock.fig.ROCE
    obj['fig']['DtoE'] = stock.fig.DtoE
    obj['fig']['INTR'] = stock.fig.INTR
    #print(json.dumps(obj, indent=4, default=lambda o:o.__dict__))
#    obj = json.dumps(obj)
#    obj = json.loads(obj)
    return obj




