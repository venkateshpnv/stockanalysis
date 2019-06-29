import internet
from common import *

def price_surprises():
    internet.price_surprises('US', 0.10, WEEK | DAY, 'HOT', 'SYNC_DB')

price_surprises()

