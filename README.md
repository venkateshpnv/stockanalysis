# stockanalysis


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

List documents by query
ex: List documents where name=hello
>db.my_collection.find({"name":"hello"}).pretty()

ex: List documents where name=hello and age > 50
>db.my_collection.find($and: [{"name":"hello"}, {"age":{$gte:50}}]).pretty()

ex: List documents where name=hello or age > 50
>db.my_collection.find($or: [{"name":"hello"}, {"age":{$gte:50}}]).pretty()

ex: Both and and or (likes > 50 and (name=hello or age > 50))
>db.my_collection.find({"likes":{$gte:50}}, $or: [{"name":"hello"}, {"age":{$gte:50}}]).pretty()

Update a field
> db.my_collection.update({"title":"Mongo"},{$set:{"title":"New Title"}})

Update a field or two in a particular document
>db.my_collection.save({"_id": ObjectId(5983548781331adf45ec5), "title": "New Title", "name": "New Name"}

Delete where condition
>db.my_collection.remove({"title" : "SomeTitle"})

Delete one record
>db.my_collection.remove({"title" : "SomeTitle"},1)

Take Backup
  mongodump -db mydb -out /tmp/mongo/

Restore Backup
  mongorestore --dir /tmp/mongo/


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
