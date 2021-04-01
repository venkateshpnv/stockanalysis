# stockanalysis

Quandl Key
==========
JUCdxdDQ4LDzprPBrgsk

Python
======
e2.decode('utf-8') -> bytes to string

Update all packages
$ pip3 freeze > /tmp/r.txt
$ pip3 install -r /tmp/r.txt --upgrade

Mongodb
========
Table -> Collection
Tuple -> Document
Column -> Field
Primary Key -> Primary Key, default _id
Show Dbs
mongo
> show dbs

create database
> use mydb

delete database
> use mydb
>db.dropDatabase()

check current selected database
> db

create a collection
> db.my_collection.insert({"name":"new document"})
This creates my_collection and a document with fields "name"

show collections
> show collections

Delete collection
> db.my_collection.drop()

List documents in a collection
> db.my_collection.find().pretty()

List a particular field
> db.US_Stocks.find({"bscs.symbol":"BAC"},{"fig":1}).pretty()

List documents by query
ex: List documents where name=hello
>db.my_collection.find({"name":"hello"}).pretty()

ex: List documents where name=hello and age > 50
>db.my_collection.find($and: [{"name":"hello"}, {"age":{$gte:50}}]).pretty()

ex: List documents where name=hello or age > 50
>db.my_collection.find($or: [{"name":"hello"}, {"age":{$gte:50}}]).pretty()

ex: Both and and or (likes > 50 and (name=hello or age > 50))
>db.my_collection.find({"likes":{$gte:50}}, $or: [{"name":"hello"}, {"age":{$gte:50}}]).pretty()

stocks between 1bn and 5bn
db.US_Stocks.find({ 'bscs.mcap' : { $gt :  1000, $lt : 5000}},{"bscs.symbol":1, '_id':false}).count()

stocks between 100bn and 1 trillion
db.US_Stocks.find({ 'bscs.mcap' : { $gt :  100000, $lt : 1000000}},{"bscs.symbol":1, '_id':false}).count()

stocks above 1 trillion and less than 10 trillion with day price change in descending order
db.US_Stocks.find({ 'bscs.mcap' : { $gt :  1000000, $lt : 10000000}}, {'bscs.symbol':1, 'sno':1, 'price_change':1, '_id':false}).sort({"price_change.day":-1}).pretty()

Dividend greater than zero
db.US_Stocks.find({"bscs.industry":"Military/Government/Technical", "Dividend.yld":{$gt:0}},{"bscs.name":1, '_id':false}).pretty()

If field exists
> db.US_Stocks.find({"bscs.price_failcount": {"$exists": true }}, {"bscs.symbol":1}).count()

Update a field
> db.my_collection.update({"title":"Mongo"},{'$set':{"title":"New Title"}})

Update a field or two in a particular document
>db.my_collection.save({"_id": ObjectId(5983548781331adf45ec5), "title": "New Title", "name": "New Name"}

Delete where condition
>db.my_collection.remove({"title" : "SomeTitle"})

Delete one record
>db.my_collection.remove({"title" : "SomeTitle"},1)

Delete a field
> db.US_Stocks.update({"bscs.symbol":"WM"}, {$unset: {field_name:1}}, false, true)

Mongod start
  /usr/bin/mongod --unixSocketPrefix=/run/mongodb --config /etc/mongodb.conf
Take Backup
  mongodump --db=Stocks --out=./dump
Restore Backup
  mongorestore -d Stocks  ~/work/gdrive/mongodb_backup/Stocks
  mongorestore --dir /tmp/mongo/

Duplicate Database
db.copyDatabase("Stocks", "Stocks_copy", "127.0.0.1")

Rename a field in a collection for all documents
db.Indian_Stocks.update({},{$rename:{"fig.Return on Equity": "fig.ROE"}}, false, true)

Delete a field in a collection for all documents
db.US_Stocks.update({}, {$unset:{"fig.SPLIT_History":1}}, {multi:true})

# Add since fields to the docs that doesnt have since
db.US_Stocks.update({'bscs.since':{'$exists': false}},{'$set':{'bscs.since':'1900-01-01'}}, false, true)

Randomly get records from db
One record:
db.US_Stocks.aggregate([{$sample: {size:1}}])

All records with particular field
db.US_Stocks.aggregate([{$sample: {size:5612}},{$project: {'bscs.symbol':1}}])

All records count
db.US_Stocks.aggregate([{$sample: {size:5612}}], {allowDiskUse:true}).toArray().length
db.US_Stocks.aggregate([{$sample: {size:5612}},{$project: {'bscs.symbol':1}}],{allowDiskUse:true}).toArray().length -> Use this as memory exceeds with the earlier one.

Records with mcap > 1 trillion. 
db.US_Stocks.aggregate([{$sample: {size:5612}},{$match : {'bscs.mcap':{$gte:1000000}}}], {allowDiskUse:true}).toArray().length

Large File git commits
$ git lfs track "*.bson"

Ignore files from git commit
git update-index --assume-unchanged "main/dontcheckmein.txt"

mongodb create index
-----------------------
db.US_Stocks.createIndex({'bscs.symbol': -1},{unique:true}) # Create unique index
db.US_Stocks.createIndex({'price_change.day': -1})
db.US_Stocks.createIndex({sno: -1})
db.US_Stocks.createIndex({ "$**": "text" },{ name: "TextIndex" })

MYSQL
=====
CREATE

select Date, FORMAT(Free_Cash_Flow,2) as Free_Cash_Flow, FORMAT(Common_Stock_Issued,2) as Common_Stock, FORMAT(Debt_Issued,2) as Debt_Issued, FORMAT(Debt_Repayment,2) as Debt_Paid from cash_table
where Symbol='MFA';

mysql> select Date, FORMAT(Sales,2) as Sales, FORMAT(Operating_Expenses,2) as Operating_Expenses, FORMAT(Total_expenses,2) as Total_expenses, FORMAT(Gross_Profit,2) as Gross_Profit, FORMAT(`Net_Income_$M
`,2) as Net_Income, FORMAT(Ebitda,2) as Ebitda, FORMAT(`Interest_expense_(net_of_interest_income)`,2) as Interest_Expense from income_table where Symbol='MFA'; 

select FORMAT(`Total_Assets_$M`,2) as Tot_Assets, FORMAT(Total_Liabilities,2) as Tot_Liabilities, FORMAT(Total_Current_Assets,2) as Tot_Cur_Assets, FORMAT(Total_Current_Liabilities,2) as Tot_Cur_Liablilities, FORMAT(`Long_Term_Debt_$M`,2) as LongTerm_Debt, FORMAT(`Short_Term_Debt`,2) as ShortTerm_Debt, FORMAT(`PPE_Gross`,2) as PPE, FORMAT(`Intangibles`,2) as Intangibles, FORMAT(`Cash_&_Cash_Equivalents`,2) as Cash, FORMAT(`Common_Shares`,2) as Common_Shares, FORMAT(`Shares_Outstanding,_K`,2) as Tot_Shares from balance_table where Symbol='MFA';


ysql> DELIMITER $$
mysql> CREATE PROCEDURE cash_quart(IN sym CHAR(12)) BEGIN   select Date, FORMAT(Free_Cash_Flow,2) as Free_Cash_Flow, FORMAT(Common_Stock_Issued,2) as Common_Stock, FORMAT(Debt_Issued,2) as Debt_Issued, FORMAT(Debt_Repayment,2) as Debt_Paid from cash_quart_table where Symbol=sym;
    -> END $$
mysql> DELIMITER ;


mysql> DELIMITER $$
mysql> CREATE PROCEDURE income(IN sym CHAR(12)) BEGIN   select Date, FORMAT(Sales,2) as Sales, FORMAT(Operating_Expenses,2) as Operating_Expenses, FORMAT(Total_expenses,2) as Total_expenses, FORMAT(Gross_Profit,2) as Gross_Profit, FORMAT(`Net_Income_$M`,2) as Net_Income, FORMAT(Ebitda,2) as Ebitda, FORMAT(`Interest_expense_(net_of_interest_income)`,2) as Interest_Expense from income_table where Symbol=sym; END$$
Query OK, 0 rows affected (0.01 sec)

mysql> DELIMITER ;

mysql> DELIMITER $$
mysql> CREATE PROCEDURE balance(IN sym CHAR(12))
    -> BEGIN
    ->   select FORMAT(`Total_Assets_$M`,2) as Tot_Assets, FORMAT(Total_Liabilities,2) as Tot_Liabilities, FORMAT(Total_Current_Assets,2) as Tot_Cur_Assets, FORMAT(Total_Current_Liabilities,2) as Tot_Cur_Liablilities, FORMAT(`Long_Term_Debt_$M`,2) as LongTerm_Debt, FORMAT(`Short_Term_Debt`,2) as ShortTerm_Debt, FORMAT(`PPE_Gross`,2) as PPE, FORMAT(`Intangibles`,2) as Intangibles, FORMAT(`Cash_&_Cash_Equivalents`,2) as Cash, FORMAT(`Common_Shares`,2) as Common_Shares, FORMAT(`Shares_Outstanding,_K`,2) as Tot_Shares from balance_table where Symbol=sym;
    -> END $$
Query OK, 0 rows affected (0.02 sec)

mysql> DELIMITER ;

mysql> DELIMITER $$
mysql> CREATE PROCEDURE balance_quart(IN sym CHAR(12)) BEGIN   select FORMAT(`Total_Assets_$M`,2) as Tot_Assets, FORMAT(Total_Liabilities,2) as Tot_Liabilities, FORMAT(`Long_Term_Debt_$M`,2) as LongTerm_Debt, FORMAT(`Short_Term_Debt`,2) as ShortTerm_Debt, FORMAT(`PPE_Gross`,2) as PPE, FORMAT(`Intangibles`,2) as Intangibles, FORMAT(`Cash_&_Cash_Equivalents`,2) as Cash, FORMAT(`Common_Shares`,2) as Common_Shares, FORMAT(`Shares_Outstanding,_K`,2) as Tot_Shares from balance_quart_table where Symbol=sym; END$$
Query OK, 0 rows affected (0.02 sec)

mysql> DELIMITER ;
mysql> call balance_quart('MFA');


Installing TA-Lib
==================
https://ta-lib.org/hdr_dw.html
$ wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
$ tar -xvzf ta-lib-0.4.0-src.tar.gz
$ cd ta-lib
$ ./configure && make && make install

Pandas
======================
timestamp to datetime
df.index[0].to_pydatetime()

How to add new column at a particular position
df.columns[0] = 'New_ID'

How to add incremental values to a column 'row_id'. 0 is the position of the column
df.insert(0,'row_id',range(start, start+len(df)))

PyMongo python package
======================
Read all documents one by one
for i in mydatabase.myTable.find({title: 'MongoDB and Python'}) 
	print(i) 

Count number of documents
print(mydatabase.myTable.count({title: 'MongoDB and Python'})) 

YahooFinancials python package
=============================
https://github.com/JECSand/yahoofinancials.git


Stock Splits
===============
https://www.motilaloswal.com/markets/stock-market-live/StockSplits.aspx

Insider Info
============
insiderarbitrage.com
openinsider.com

Data Science Beta
=================
http://gouthamanbalaraman.com/blog/calculating-stock-beta.html

SSH to VM
=========
.\VBoxManage.exe modifyvm "ubuntu VM" --natpf1 "SSH,tcp,127.0.0.1,2522,10.0.2.15,22"

.\VBoxManage.exe showvminfo "ubuntu VM"

rclone mount petlafingdrive: ~/gdrive


curl -s --compressed 'ftp://ftp.nasdaqtrader.com/SymbolDirectory/nasdaqlisted.txt' > nasdaq.txt
https://datahub.io/core/nyse-other-listings

Split Data from Yahoo Finance
import yfinance as yf
tick = yf.Ticker('AAPL')
tick.get_info() -> Complete info of the stock

import pandas_datareader.data as data
data.get_iex_symbols()
