
# NoSQL_DBs - repository


### Exploring NoSQL Databases  

## 1st assignement- Using Neo4j and Redis in python  

Information on breweries, beers and their reviews are stored in a neo4j database.
Exploratory questions on data and relations must be answered using python connector to neo4j (graph database).
Final answers must be submitted in a Redis database, (a fast,simple key:value database) again using the python connector.
More information on the assignement is in the notebook. 
This effort was graded 19/20, for a different interpretation on the expected results for a question.

## 2nd assignement - Using MongoDB with python connector.  

Data from european public contracts as been inserted in a MongoDB database.
In the database 4 document collections are available and should be used to answer several exploration questions.
We use the python connector to get information on a jupyter notebook.
More information on the assignement is in the notebook.
This effort was graded as 19.3/20, the only penalty for not exploring further the open question.

## Final Project - Fastest MongoDB powered interactive website.  

Given the original EU procurements database with 5.5M contracts information, we want to feed a dash powered website model with interactive graphics, while achieving the fastest possible queries fullfilling time. 

All possible optimizations using mongoDB and python are possible, including pre-calculating values, new document collections, indexing, etc... as long as:
The results are correct
Filtering interactivity continues to work fully
The app itself is not modified
New documents can also be inserted and processed.

The time is the calculated on fullfilling the queries, and in processing a new document when inserted in the database.

We were able to secure top-spot ex-equo along another group, with a final grade of 19.4/20.


### Notes

The credentials for accessing the servers were kept in a separate file not available on github - but a template of credentials file is given.  
Since without credentials the original databases are not accessible anymore, thenotebooks are made available after execution.
