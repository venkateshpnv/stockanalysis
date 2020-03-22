import mysql.connector

def mysql_open_connection(db_name=None):
    db = mysql.connector.connect(host='localhost', user='root',passwd='petla123', port=3306)
    if db_name:
        mysql_use_db(db.cursor(),db_name)
    return db

def mysql_close_connection(db):
    db.close()

def mysql_get_cursor(db):
    return db.cursor()

def mysql_open_and_get_cursor(db_name=None):
    db = mysql_open_connection(db_name)
    return db, mysql_get_cursor(db)

def mysql_execute_query(cursor, query):
    cursor.execute(query)

def mysql_create_database(cursor, db_name):
    if db_name in mysql_get_databases(cursor):
        print("DB %s already exists" %(db_name))
        return False

    query = 'create database %s' %(db_name)
    mysql_execute_query(cursor, query)
    return True

def mysql_list_databases(cursor):
    query = 'show databases'
    mysql_execute_query(cursor, query)
    dbs = []
    for db in cursor.fetchall():
        dbs.append(db[0])

    return dbs

def mysql_get_current_db(cursor):
    query = 'SELECT DATABASE() FROM DUAL;'
    mysql_execute_query(cursor, query)
    db = cursor.fetchone()
    if db:
        return db[0]
    return None

def mysql_use_db(cursor,db_name):
    query = 'use %s' %(db_name)
    mysql_execute_query(cursor, query)

def mysql_list_tables(cursor, table_name=None, flag=False):
    tables = []
    if not table_name and flag is False:
        return tables
    elif flag and not table_name:
        query  = 'show tables'
    else:
        query  = 'show tables like %r' %(table_name)
    mysql_execute_query(cursor, query)

    for entry in cursor.fetchall():
        tables.append(entry[0])
    return tables

def mysql_check_if_exists(cursor, table_name):
    query  = 'show tables like %r;' %(table_name)
    mysql_execute_query(cursor, query)

    if cursor.fetchone() is None:
        return False
    return True

#def mysql_create_table(cursor, table_name, columns):
def get_symbol_table_name(symbol):
    symbol = symbol.replace('.','_')
    return 'STK'+symbol.replace('.','_')

def mysql_get_column_names(cursor, table_name):
    columns = []

    if mysql_check_if_exists(cursor, table_name):
        query  = 'select * from %s limit 10;' %(table_name)
        mysql_execute_query(cursor, query)
        num_cols=len(cursor.description)
        columns = [i[0] for i in cursor.description]
        cursor.fetchall() # Read everything. Else we can't proceed with next commands
    else:
        print("Table %s doesnt exist" %(table_name))

    return columns

def mysql_create_table(cursor, table_name, fields):
    if mysql_check_if_exists(cursor, table_name):
        print("Table already exists")
        return False

    columns = []
    for f in fields:
        col = '{} {}'.format(f[0], f[1])
        columns.append(col)

    query = 'create table {} ({})'.format('sample_table', ', '.join([c for c in columns]))
    print(query)
    try:
        mysql_execute_query(cursor, query)
    except Exception as E:
        if 'already exists' in str(E):
            print("Table %r already exists" %(table_name))
        else:
            print("Error while creating table %r: %r" %(table_name, str(E)))


def mysql_insert_into_table(cursor, table_name, df):

    if mysql_check_if_exists(cursor, table_name) is None:
        query = 'create table '+ table_name + ' like test2;'
        mysql_execute_query(cursor, query)
        #query = 'alter table ' + table_name +' add index(Date);'
        #engine.execute(query)
    query = 'select * from '+ table_name
    #query = 'select * from '+ table_name + ' where Symbol=%r' %(symbol)
    rdf = pd.read_sql_query(query, engine)
 
