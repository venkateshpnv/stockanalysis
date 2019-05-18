from inspect import currentframe
import os

#Supportive calls
def PRINT_ERR(x):
    print("ERR: %s" %(x))
def PRINT_DBG(x):
    None
    #print(x)
def PRINT(x):
    None
    #print(x)

def goto(linenum):
    global line
    line=linenum

def p2f(x):
    try:
        val = float(x.strip('%'))
    except ValueError:
        return 0
    return val

def str_to_int(x):
    try:
        val = int(x)
    except ValueError:
        return 0
    return val

def str_to_float(x):
    try:
        #val = float(x)
        val = float(x.lstrip().rstrip().replace("$","").replace(",","").replace("%",""))
    except ValueError:
        return 0
    except TypeError:
        return 0
    return val

def str_to_float_valid(x):
    try:
        val = float(x)
        return True
    except ValueError:
        return False

def get_linenumber():
    cf = currentframe()
    return cf.f_back.f_lineno

def write_to_file(html, html_file):
    f = open(html_file, "w")
    f.write(html)
    f.close()

def write_to_unparsed(stock):
    f = open("US_unparsed.txt", "a")
    f.write(stock)
    f.write("\n")
    f.close()
 
def lowest(a, b):
    if a < b:
        return a
    return b

def lowest_3(a, b, c):
    if a < b:
        low = a
    low = b
    if b < c:
        return b
    return c

#Print Stock Info
def print_stock_info(stk):
    PRINT("Name: %r" %(stk.bscs.name))
    PRINT("Symbol: %r" %(stk.bscs.symbol))
    PRINT("Price: %r" %(stk.bscs.price))
    PRINT("Face Value: %r" %(stk.bscs.face_value))
    PRINT("Promoter Stake: %r" %(stk.bscs.promoter_stake))
    PRINT("Corporate Stake: %r" %(stk.bscs.corp_stake))
    PRINT("Public Stake: %r" %(stk.bscs.pub_stake))
    PRINT("FII Stake: %r" % (stk.bscs.fii_stake))
    PRINT("DII Stake: %r" % (stk.bscs.dii_stake))
    PRINT("Others Stake: %r" % (stk.bscs.others_stake))

def remove_dir(path):
    filelist = [f for f in os.listdir(path)]
    for f in filelist:
        file_path = "%s/%s" %(path, f)
        os.remove(file_path)
    os.rmdir(path)
