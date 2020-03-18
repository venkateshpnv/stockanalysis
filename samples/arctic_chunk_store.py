#https://arctic.readthedocs.io/en/latest/chunkstore/

from arctic import Arctic
from hdf5 import *
a=Arctic('localhost')
a.initialize_library('test_chunk_store', lib_type=CHUNK_STORE)
lib=a['test_chunk_store']
df=get_dataframe('India', 'MARUTI')
df['date']=df.index.to_pydatetime()
lib.write('MARUTI', df, chunk_size='Y') #'D', 'M'
lib.write('MARUTI', df)
lib.list_symbols()
#['MARUTI', 'MARUTI2']
lib.delete('MARUTI')
lib.list_symbols()
#['MARUTI2']
lib.get_info('MARUTI2')
#{'chunk_count': 17, 'len': 4035, 'appended_rows': 0, 'metadata': {'columns': ['Date', 'High', 'Low', 'Open', 'Close', 'Volume', 'Adj Close', 'date']}, 'chunker': 'date', 'chunk_size': 'Y', 'serializer': 'FrameToArray'}

