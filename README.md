# stockanalysis

Quandl Key
==========
JUCdxdDQ4LDzprPBrgsk

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

Take Backup
  mongodump --db=Stocks --out=./dump
Restore Backup
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

