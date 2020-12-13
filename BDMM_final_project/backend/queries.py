from pymongo import MongoClient
from backend.DB import eu
from backend.DB import db
from datetime import datetime
import credentials as cred

host=cred.mongo_host
port=cred.mongo_port
user=cred.mongo_user
password=cred.mongo_pass
protocol="mongodb"

client = MongoClient(f"{protocol}://{user}:{password}@{host}:{port}")
db = client.contracts
eu = db.eu

countries = ['NO', 'HR', 'HU', 'CH', 'CZ', 'RO', 'LV', 'GR', 'UK', 'SI', 'LT',
             'ES', 'FR', 'IE', 'SE', 'NL', 'PT', 'PL', 'DK', 'MK', 'DE', 'IT',
             'BG', 'CY', 'AT', 'LU', 'BE', 'FI', 'EE', 'SK', 'MT', 'LI', 'IS']

########################################################################################################################
'''                                                     COMMENTS

1. As the 'UK' ISO_COUNTRY_CODE in the eu collection does not have any correspondent alpha-2 in iso_codes collection, 
we tried to understand what was going on and we found that the 'UK' code is not a real alpha-2 and the code 
corresponding to 'UK' is indeed 'GB'. Although we believe the best solution would be replacing 'UK' for 'GB' in the eu 
collection documents, this would bring some problems in the dashboard and so we decided to replace 'GB' with 'UK' in 
the iso_codes collection document using the following commented code.

# db.iso_codes.update_many(
#     {'alpha-2': {'$exists': True}},
#     [
#         {"$set": {
#             "alpha-2": {'$cond': [{'$eq': [ "$alpha-2", 'GB' ] }, # condition
#                                            'UK',  # true case
#                                            "$alpha-2" # false case
#                                           ] 
#                                 }
#         } }
#     ]
# )

2. We found there are some documents without CPV codes which is odd because it is mandatory since 2006.

3. FOR ALL THE MAPS WE CHANGED THE LOCATIONMODE TO ISO3 IN DCC_FUNCTIONS

4. In the queries where we have a division, it might happen that the denominator is zero when applying filters 
(year and country) leading to a division by zero. To prevent this from happening, in those queries we applied an "exists"
condition.

5. We found there were outliers in VALUE_EURO (as transmitted by the professors), so in all the queries that used 
VALUE_EURO we applied a filter not to take them into account. We believe this is a problem only in the VALUE_EURO field 
and not on the contracts themselves, so in the cases where VALUE_EURO is not needed for querying, we did not apply it. 
For example, when querying the number of offers, we used all the contracts. Instead of applying this filter in every
single query, we used it when creating the pre-computed collections and everytime a new document is inserted

6. The companies' names are not standardized which causes incongruencies along the queries from the 15th question 
forward, making it slower to work with and having duplicates for the same company with minimal differences 
(quotations marks, accent marks and special characters). One of the possible solutions could be removing these characters
from all the names and also convert them to lower case, standardizing the names for a correct comparison.
However, since the database holds companies' names in different languages and without knowing the proper rules for each
language we could be creating errors in the database by merging different companies as one. We would suggest the 
companies should be identified by a unique id, like the european VAT identification, instead of the name.

7. To avoid displaying invalid query messages on the dashboard, which seems like an error occurred in the code, but in
reality are due to combinations of countries/years that don't have values for a specific query, we return a list with
the specified parameters all with a value of 0. This way, instead of the error message we get an empty visualization.
'''

########################################################################################################################

def ex0_cpv_example(bot_year=2008, top_year=2020):
    """
    Returns all contracts in given year 'YEAR' range and cap to 100000000 the 'VALUE_EURO'

    Expected Output (list of documents):
    [{'result': count_value(int)}]
    """

    def year_filter(bot_year, top_year):
        filter_ = {
            '$match': {
                '$and': [{'YEAR': {'$gte': bot_year}}, {'YEAR': {'$lte': top_year}}],
                'VALUE_EURO': {'$lt': 100000000}
            }}

        return filter_

    count = {
        '$count': 'result'
    }

    pipeline = [year_filter(bot_year, top_year), count]

    list_documents = list(eu.aggregate(pipeline))

    return list_documents

########################################################################################################################

def year_filter(bot_year, top_year, country_list):
    filter_ = {
        '$match': {
            '$and': [{'_id.YEAR': {'$gte': bot_year}}, {'_id.YEAR': {'$lte': top_year}}],
            '_id.ISO_COUNTRY_CODE': {'$in': country_list}
           # 'VALUE_EURO': {'$lt': 100000000}
           # We already applied this filter when calculating our pre-computed tables 
        }}

    return filter_

def year_filter_eu(bot_year, top_year, country_list):
    filter_ = {
        '$match': {
            '$and': [{'YEAR': {'$gte': bot_year}}, {'YEAR': {'$lte': top_year}}],
            'ISO_COUNTRY_CODE': {'$in': country_list}
           # 'VALUE_EURO': {'$lt': 100000000}
           # We already applied this filter when calculating our pre-computed tables
        }}

    return filter_

def ex1_cpv_box(bot_year=2008, top_year=2020, country_list=countries):
    """
    Returns five metrics, described below
    Result filterable by floor year, roof year and country_list

    Expected Output:
    (avg_cpv_euro_avg, avg_cpv_count, avg_cpv_offer_avg, avg_cpv_euro_avg_y_eu, avg_cpv_euro_avg_n_eu)

    Where:
    avg_cpv_euro_avg = average value of each CPV's division contracts average 'VALUE_EURO', (int)
    avg_cpv_count = average value of each CPV's division contract count, (int)
    avg_cpv_offer_avg = average value of each CPV's division contracts average NUMBER_OFFERS', (int)
    avg_cpv_euro_avg_y_eu = average value of each CPV's division contracts average VALUE_EURO' with 'B_EU_FUNDS', (int)
    avg_cpv_euro_avg_n_eu = average value of each CPV's division contracts average 'VALUE_EURO' with out 'B_EU_FUNDS' (int)
    """

    # For this query, as we divide the sum always by count, with the filters it might happen that we divide by zero if
    # we don't check the condition "if exists", therefore, we will separate all queries (A,B,C,D and E) for the question 1
    # in all the sections (cpv_divisions, countries and companies)

    # 1A
    pipeline = [
        year_filter(bot_year, top_year, country_list),
        { '$match': {
            'Count_Contracts_with_Value_Euro': {'$exists': True}
        } },
        { '$group': {
            '_id': '$_id.CPV_Division',
            'Sum_CPV_Spending': {'$sum': '$Sum_Value_Euro'},
            'Count_contracts_CPV_Spending': {'$sum': '$Count_Contracts_with_Value_Euro'}
        } },
        { '$project': {
            'Avg_CPV_Spending': {'$divide': ['$Sum_CPV_Spending', '$Count_contracts_CPV_Spending']}
        } },
        { '$group': {
            '_id': False,
            'Avg_Spending_Total': {'$avg': '$Avg_CPV_Spending'}
        } },
        { '$project': {
            '_id': 0,
            'Avg_Spending_Total': 1
        } }
    ]

    avg_cpv_euro_avg = list(db.cpv_divisions_all_data.aggregate(pipeline))[0].get('Avg_Spending_Total')

    # 1B
    pipeline = [
        year_filter(bot_year, top_year, country_list),
        { '$group': {
            '_id': '$_id.CPV_Division',
            'Count_contracts_CPV': {'$sum': '$Count_Contracts_Total'}
        } },
        { '$group': {
            '_id': False,
            'Avg_Count_Contracts_Total': {'$avg': '$Count_contracts_CPV'}
        } }, 
        { '$project': {
            '_id': 0,
            'Avg_Count_Contracts_Total': 1
        } }
    ]

    avg_cpv_count = list(db.cpv_divisions_all_data.aggregate(pipeline))[0].get('Avg_Count_Contracts_Total')

    # 1C
    pipeline = [
        year_filter(bot_year, top_year, country_list),
        { '$match': {
            'Count_Contracts_with_Nr_Offers': {'$exists': True}
        } },
        { '$group': {
            '_id': '$_id.CPV_Division',
            'Sum_CPV_Offers': {'$sum': '$Sum_Nr_Offers'},
            'Count_contracts_CPV_Offers': {'$sum': '$Count_Contracts_with_Nr_Offers'}
        } },
        { '$project': {
            'Avg_CPV_Offers': {'$divide': ['$Sum_CPV_Offers', '$Count_contracts_CPV_Offers']}
        }},
        { '$group': {
            '_id': False,
            'Avg_NR_Offers_Total': {'$avg': '$Avg_CPV_Offers'}
        } }, 
        { '$project': {
            '_id': 0,
            'Avg_NR_Offers_Total': 1
        } }
    ]

    avg_cpv_offer_avg = list(db.cpv_divisions_all_data.aggregate(pipeline))[0].get('Avg_NR_Offers_Total')

    # 1D
    pipeline = [
        year_filter(bot_year, top_year, country_list),
        { '$match': {
            'Count_Contracts_B_EU_Y': {'$exists': True}
        } },
        { '$group': {
            '_id': '$_id.CPV_Division',
            'Sum_CPV_Funds': {'$sum': '$Sum_Value_Euro_B_EU_Y'},
            'Count_contracts_CPV_Funds': {'$sum': '$Count_Contracts_B_EU_Y'}
        } },
        { '$project': {
            'Avg_CPV_Spending_Funds': {'$divide': ['$Sum_CPV_Funds', '$Count_contracts_CPV_Funds']}
        }},
        { '$group': {
            '_id': False,
            'Avg_Spending_Funds_Total': {'$avg': '$Avg_CPV_Spending_Funds'}
        } }, 
        { '$project': {
            '_id': 0,
            'Avg_Spending_Funds_Total': 1
        } }
    ]

    avg_cpv_euro_avg_y_eu = list(db.cpv_divisions_all_data.aggregate(pipeline))[0].get('Avg_Spending_Funds_Total')

    # 1E
    pipeline = [
        year_filter(bot_year, top_year, country_list),
        { '$match': {
            'Count_Contracts_B_EU_N': {'$exists': True}
        } },
        { '$group': {
            '_id': '$_id.CPV_Division',
            'Sum_CPV_No_Funds': {'$sum': '$Sum_Value_Euro_B_EU_N'},
            'Count_contracts_CPV_No_Funds': {'$sum': '$Count_Contracts_B_EU_N'}
        } },
        { '$project': {
            'Avg_CPV_Spending_No_Funds': {'$divide': ['$Sum_CPV_No_Funds', '$Count_contracts_CPV_No_Funds']}
        }},
        { '$group': {
            '_id': False,
            'Avg_Spending_No_Funds_Total': {'$avg': '$Avg_CPV_Spending_No_Funds'}
        } }, 
        { '$project': {
            '_id': 0,
            'Avg_Spending_No_Funds_Total': 1
        } }
    ]

    avg_cpv_euro_avg_n_eu = list(db.cpv_divisions_all_data.aggregate(pipeline))[0].get('Avg_Spending_No_Funds_Total')

    return avg_cpv_euro_avg, avg_cpv_count, avg_cpv_offer_avg, avg_cpv_euro_avg_y_eu, avg_cpv_euro_avg_n_eu


def ex2_cpv_treemap(bot_year=2008, top_year=2020, country_list=countries):
    """
    Returns the count of contracts for each CPV Division
    Result filterable by floor year, roof year and country_list

    Expected Output (list of documents):
    [{cpv: value_1, count: value_2}, ....]

    Where:
    value_1 = CPV Division description, (string) (located in cpv collection as 'cpv_division_description')
    value_2 = contract count of each CPV Division, (int)
    """

    pipeline = [
        year_filter(bot_year, top_year, country_list),
        {'$group': {
            '_id': {'CPV_Division': '$_id.CPV_Division', 'CPV_Description': '$CPV_Description'},
            'Count_contracts_CPV': {'$sum': '$Count_Contracts_Total'}
        }},
        {'$project': {
            '_id': 0,
            'cpv': '$_id.CPV_Description',
            'count': '$Count_contracts_CPV'
        }}
    ]

    list_documents = list(db.cpv_divisions_all_data.aggregate(pipeline))

    if not list_documents:
        list_documents = [{'cpv': 0, 'count': 0}]

    return list_documents


def ex3_cpv_bar_1(bot_year=2008, top_year=2020, country_list=countries):
    """
    Per CPV Division and get the average 'VALUE_EURO' return the highest 5 cpvs
    Result filterable by floor year, roof year and country_list

    Expected Output (list of 5 sorted documents):
    [{cpv: value_1, avg: value_2}, ....]

    Where:
    value_1 = CPV Division description, (string) (located in cpv collection as 'cpv_division_description')
    value_2 = average 'VALUE_EURO' of each CPV Division, (float)
    """

    pipeline = [
        year_filter(bot_year, top_year, country_list),
        { '$match': {
            'Count_Contracts_with_Value_Euro': {'$exists': True}
        } },
        {'$group': {
            '_id': {'CPV_Division': '$_id.CPV_Division', 'CPV_Description': '$CPV_Description'},
            'Sum_CPV_Spending': {'$sum': '$Sum_Value_Euro'},
            'Count_contracts_CPV_Spending': {'$sum': '$Count_Contracts_with_Value_Euro'}
        }},
        {'$project': {
            '_id': 0,
            'cpv': '$_id.CPV_Description',
            'avg': {'$divide': ['$Sum_CPV_Spending', '$Count_contracts_CPV_Spending']}
        }},
        {'$sort': {
            'avg': -1
        }},
        {'$limit': 5}
    ]

    list_documents = list(db.cpv_divisions_all_data.aggregate(pipeline))

    if not list_documents:
        list_documents = [{'cpv': 0, 'avg': 0}]

    return list_documents


def ex4_cpv_bar_2(bot_year=2008, top_year=2020, country_list=countries):
    """
    Per CPV Division and get the average 'VALUE_EURO' return the lowest 5 cpvs
    Result filterable by floor year, roof year and country_list

    Expected Output (list of 5 sorted documents):
    [{cpv: value_1, avg: value_2}, ....]

    Where:
    value_1 = CPV Division description, (string) (located in cpv collection as 'cpv_division_description')
    value_2 = average 'VALUE_EURO' of each CPV Division, (float)
    """

    pipeline = [
        year_filter(bot_year, top_year, country_list),
        { '$match': {
            'Count_Contracts_with_Value_Euro': {'$exists': True}
        } },
        {'$group': {
            '_id': {'CPV_Division': '$_id.CPV_Division', 'CPV_Description': '$CPV_Description'},
            'Sum_CPV_Spending': {'$sum': '$Sum_Value_Euro'},
            'Count_contracts_CPV_Spending': {'$sum': '$Count_Contracts_with_Value_Euro'}
        }},
        {'$project': {
            '_id': 0,
            'cpv': '$_id.CPV_Description',
            'avg': {'$divide': ['$Sum_CPV_Spending', '$Count_contracts_CPV_Spending']}
        }},
        {'$sort': {
            'avg': 1
        }},
        {'$limit': 5}
    ]

    list_documents = list(db.cpv_divisions_all_data.aggregate(pipeline))

    if not list_documents:
        list_documents = [{'cpv': 0, 'avg': 0}]

    return list_documents


def ex5_cpv_bar_3(bot_year=2008, top_year=2020, country_list=countries):
    """
    Per CPV Division and get the average 'VALUE_EURO' return the highest 5 cpvs for contracts which recieved european funds ('B_EU_FUNDS') 
    Result filterable by floor year, roof year and country_list

    Expected Output (list of 5 sorted documents):
    [{cpv: value_1, avg: value_2}, ....]

    Where:
    value_1 = CPV Division description, (string) (located in cpv collection as 'cpv_division_description')
    value_2 = average 'VALUE_EURO' of each CPV Division, (float)
    """

    pipeline = [
        year_filter(bot_year, top_year, country_list),
        {'$match': {
            'Count_Contracts_B_EU_Y': {'$exists': True},
        }},
        {'$group': {
            '_id': {'CPV_Division': '$_id.CPV_Division', 'CPV_Description': '$CPV_Description'},
            'Sum_CPV_Funds': {'$sum': '$Sum_Value_Euro_B_EU_Y'},
            'Count_contracts_CPV_Funds': {'$sum': '$Count_Contracts_B_EU_Y'}
        }},
        {'$project': {
            '_id': 0,
            'cpv': '$_id.CPV_Description',
            'avg': {'$divide': ['$Sum_CPV_Funds', '$Count_contracts_CPV_Funds']}
        }},
        {'$sort': {
            'avg': -1
        }},
        {'$limit': 5}
    ]

    list_documents = list(db.cpv_divisions_all_data.aggregate(pipeline))

    if not list_documents:
        list_documents = [{'cpv': 0, 'avg': 0}]

    return list_documents


def ex6_cpv_bar_4(bot_year=2008, top_year=2020, country_list=countries):
    """
    Per CPV Division and get the average 'VALUE_EURO' return the highest 5 cpvs for contracts which did not recieve european funds ('B_EU_FUNDS') 
    Result filterable by floor year, roof year and country_list

    Expected Output (list of 5 sorted documents):
    [{cpv: value_1, avg: value_2}, ....]

    Where:
    value_1 = CPV Division description, (string) (located in cpv collection as 'cpv_division_description')
    value_2 = average 'VALUE_EURO' of each CPV Division, (float)
    """

    pipeline = [
        year_filter(bot_year, top_year, country_list),
        {'$match': {
            'Count_Contracts_B_EU_N': {'$exists': True},
        }},
        {'$group': {
            '_id': {'CPV_Division': '$_id.CPV_Division', 'CPV_Description': '$CPV_Description'},
            'Sum_CPV_No_Funds': {'$sum': '$Sum_Value_Euro_B_EU_N'},
            'Count_contracts_CPV_No_Funds': {'$sum': '$Count_Contracts_B_EU_N'}
        }},
        {'$project': {
            '_id': 0,
            'cpv': '$_id.CPV_Description',
            'avg': {'$divide': ['$Sum_CPV_No_Funds', '$Count_contracts_CPV_No_Funds']}
        }},
        {'$sort': {
            'avg': -1
        }},
        {'$limit': 5}
    ]

    list_documents = list(db.cpv_divisions_all_data.aggregate(pipeline))

    if not list_documents:
        list_documents = [{'cpv': 0, 'avg': 0}]

    return list_documents


def ex7_cpv_map(bot_year=2008, top_year=2020, country_list=countries):
    """
    Returns the highest CPV Division on average 'VALUE_EURO' per country 'ISO_COUNTRY_CODE'

    Result filterable by floor year, roof year and country_list

    Expected Output (list of documents):
    [{cpv: value_1, avg: value_2, country: value_3}, ....]

    Where:
    value_1 = CPV Division description, (string) (located in cpv collection as 'cpv_division_description')
    value_2 = highest CPV Division average 'VALUE_EURO' of country, (float)
    value_3 = country in ISO-3 format (string) (located in iso_codes collection)
    """

    pipeline = [
        year_filter(bot_year, top_year, country_list),
        # not all documents have VALUE_EURO and in this case, as the group by is more partitioned, they lead to a division by zero
        # so we have to guarantee that Count_Contracts_with_Value_Euro exists
        {'$match': {
            'Count_Contracts_with_Value_Euro': {'$exists': True}
        }},
        {'$group': {
            '_id': {
                'ISO_CODE': '$Alpha3',
                'CPV_Division': '$_id.CPV_Division',
                'CPV_Description': '$CPV_Description'
            },
            'Sum_CPV_Spending': {'$sum': '$Sum_Value_Euro'},
            'Count_contracts_CPV_Spending': {'$sum': '$Count_Contracts_with_Value_Euro'}
        }},
        {'$project': {
            '_id': 0,
            'cpv': '$_id.CPV_Description',
            'avg': {'$divide': ['$Sum_CPV_Spending', '$Count_contracts_CPV_Spending']},
            'country': '$_id.ISO_CODE'
        }},
        {'$sort': {
            'country': -1,
            'avg': -1
        }},
        {'$group': {
            '_id': "$country",
            'winner': {
                '$push': {
                    'cpv': "$cpv",
                    'avg': "$avg",
                }
            }
        }},
        {'$project': {
            'winner': {
                '$slice': ["$winner", 1]
            }
        }},
        {'$project': {
            '_id': 0,
            'cpv': {'$arrayElemAt': ['$winner.cpv', 0]},
            'avg': {'$arrayElemAt': ['$winner.avg', 0]},
            'country': '$_id'
        }}
    ]

    list_documents = list(db.cpv_divisions_all_data.aggregate(pipeline))

    if not list_documents:
        list_documents = [{'cpv': 0, 'avg': 0, 'country': 0}]

    return list_documents


def ex8_cpv_hist(bot_year=2008, top_year=2020, country_list=countries, cpv='50'):
    """
    Produce an histogram where each bucket has the contract counts of a particular cpv
     in a given range of values (bucket) according to 'VALUE_EURO'

    Choose 10 buckets of any partition
    Buckets Example:
     0 to 100000
     100000 to 200000
     200000 to 300000
     300000 to 400000
     400000 to 500000
     500000 to 600000
     600000 to 700000
     700000 to 800000
     800000 to 900000
     900000 to 1000000

    So given a CPV Division code (two digit string) return a list of documents where each document as the bucket_id,
    and respective bucket count.

    Result filterable by floor year, roof year and country_list

    Expected Output (list of documents):
    [{bucket: value_1, count: value_2}, ....]

    Where:
    value_1 = lower limit of respective bucket (if bucket position 0 of example then bucket:0 )
    value_2 = contract count for that particular bucket, (int)
    """

    pipeline = [
        year_filter_eu(bot_year, top_year, country_list),
        {'$match': {
            'CPV_Division': {'$eq': cpv}
        }},
        {'$bucketAuto': {
            'groupBy': "$VALUE_EURO",
            'buckets': 10,
            'granularity': 'R20'
        }},
        {'$project': {
            'bucket': '$_id.min',
            '_id': 0,
            'count': 1
        }}
    ]

    list_documents = list(db.contracts_value_euro.aggregate(pipeline))

    if not list_documents:
        list_documents = [{'bucket': 0, 'count': 0}]

    return list_documents


def ex9_cpv_bar_diff(bot_year=2008, top_year=2020, country_list=countries):
    """
    Returns the average time and value difference for each CPV, return the highest 5 cpvs

    time difference = 'DT-DISPATCH' - 'DT-AWARD'
    value difference = 'AWARD_VALUE_EURO' - 'VALUE_EURO'

    Result filterable by floor year, roof year and country_list

    Expected Output (list of documents):
    [{cpv: value_1, time_difference: value_2, value_difference: value_3}, ....]

    Where:
    value_1 = CPV Division description, (string) (located in cpv collection as 'cpv_division_description')
    value_2 = average 'DT-DISPATCH' - 'DT-AWARD', (float)
    value_3 = average 'AWARD_VALUE_EURO' - 'VALUE_EURO' (float)
    """

    pipeline = [
        year_filter(bot_year, top_year, country_list),
        {'$group': {
            '_id': {'CPV_Division': '$_id.CPV_Division', 'CPV_Description': '$CPV_Description'},
            'Count_Contracts_with_Difference_Time_Total': {'$sum': '$Count_Contracts_with_Difference_Time'},
            'Sum_Difference_Time_Total': {'$sum': '$Total_Difference_Time'},
            'Count_Contracts_with_Difference_Euro_Total': {'$sum': '$Count_Contracts_with_Difference_Euro'},
            'Sum_Difference_Euro_Total': {'$sum': '$Total_Difference_Euro'}
        }},
        {'$match': {  # guaranteeing no division by zero
            'Count_Contracts_with_Difference_Time_Total': {'$ne': 0},
            'Count_Contracts_with_Difference_Euro_Total': {'$ne': 0}
        }},
        {'$project': {
            '_id': 0,
            'cpv': '$_id.CPV_Description',
            'time_difference': {
                '$divide': ['$Sum_Difference_Time_Total', '$Count_Contracts_with_Difference_Time_Total']},
            'value_difference': {
                '$divide': ['$Sum_Difference_Euro_Total', '$Count_Contracts_with_Difference_Euro_Total']}
        }},
        {'$sort': {
            'time_difference': -1
        }},
        {'$limit': 5}
    ]

    list_documents = list(db.cpv_divisions_all_data.aggregate(pipeline))

    if not list_documents:
        list_documents = [{'cpv': 0, 'time_difference': 0, 'value_difference': 0}]

    return list_documents


def ex10_country_box(bot_year=2008, top_year=2020, country_list=countries):
    """
    We want five numbers, described below
    Result filterable by floor year, roof year and country_list

    Expected Output:
    (avg_country_euro_avg, avg_country_count, avg_country_offer_avg, avg_country_euro_avg_y_eu, avg_country_euro_avg_n_eu)

    Where:
    avg_country_euro_avg = average value of each countries ('ISO_COUNTRY_CODE') contracts average 'VALUE_EURO', (int)
    avg_country_count = average value of each countries ('ISO_COUNTRY_CODE') contract count, (int)
    avg_country_offer_avg = average value of each countries ('ISO_COUNTRY_CODE') contracts average NUMBER_OFFERS', (int)
    avg_country_euro_avg_y_eu = average value of each countries ('ISO_COUNTRY_CODE') contracts average VALUE_EURO' with 'B_EU_FUNDS', (int)
    avg_country_euro_avg_n_eu = average value of each countries ('ISO_COUNTRY_CODE') contracts average 'VALUE_EURO' with out 'B_EU_FUNDS' (int)
    """

    # 10A
    pipeline = [
        year_filter(bot_year, top_year, country_list),
        { '$match': {
            'Count_Contracts_with_Value_Euro': {'$exists': True},
        } },
        { '$group': {
            '_id': '$_id.ISO_COUNTRY_CODE',
            'Sum_Country_Spending': {'$sum': '$Sum_Value_Euro'},
            'Count_contracts_Country_Spending': {'$sum': '$Count_Contracts_with_Value_Euro'}
        } },
        { '$project': {
            'Avg_Country_Spending': {'$divide': ['$Sum_Country_Spending', '$Count_contracts_Country_Spending']}
        }},
        { '$group': {
            '_id': False,
            'Avg_Spending_Total': {'$avg': '$Avg_Country_Spending'}
        } }, 
        { '$project': {
            '_id': 0,
            'Avg_Spending_Total': 1
        } }
    ]

    avg_country_euro_avg = list(db.countries_all_data.aggregate(pipeline))[0].get('Avg_Spending_Total')

    # 10B
    pipeline = [
        year_filter(bot_year, top_year, country_list),       
        { '$group': {
            '_id': '$_id.ISO_COUNTRY_CODE',
            'Count_contracts_Country': {'$sum': '$Count_Contracts_Total'}
        } },
        { '$group': {
            '_id': False,
            'Avg_Count_Contracts_Total': {'$avg': '$Count_contracts_Country'}
        } }, 
        { '$project': {
            '_id': 0,
            'Avg_Count_Contracts_Total': 1
        } }
    ]

    avg_country_count = list(db.countries_all_data.aggregate(pipeline))[0].get('Avg_Count_Contracts_Total')

    # 10C
    pipeline = [
        year_filter(bot_year, top_year, country_list),    
        { '$match': {
            'Count_Contracts_with_Nr_Offers': {'$exists': True},
        } },
        { '$group': {
            '_id': '$_id.ISO_COUNTRY_CODE',
            'Sum_Contry_Offers': {'$sum': '$Sum_Nr_Offers'},
            'Count_contracts_Contry_Offers': {'$sum': '$Count_Contracts_with_Nr_Offers'}
        } },
        { '$project': {
            'Avg_Country_Offers': {'$divide': ['$Sum_Contry_Offers', '$Count_contracts_Contry_Offers']}
        }},
        { '$group': {
            '_id': False,
            'Avg_NR_Offers_Total': {'$avg': '$Avg_Country_Offers'}
        } }, 
        { '$project': {
            '_id': 0,
            'Avg_NR_Offers_Total': 1
        } }
    ]

    avg_country_offer_avg = list(db.countries_all_data.aggregate(pipeline))[0].get('Avg_NR_Offers_Total')

    # 10D
    pipeline = [
        year_filter(bot_year, top_year, country_list),
        {'$match': {
            'Count_Contracts_B_EU_Y': {'$exists': True},
        }},
        {'$group': {
            '_id': '$_id.ISO_COUNTRY_CODE',
            'Sum_Country_Funds': {'$sum': '$Sum_Value_Euro_B_EU_Y'},
            'Count_Contracts_Country_Funds': {'$sum': '$Count_Contracts_B_EU_Y'}
        }},
        {'$project': {
            'Avg_Country_Spending_Funds': {'$divide': ['$Sum_Country_Funds', '$Count_Contracts_Country_Funds']}
        }},
        {'$group': {
            '_id': False,
            'Avg_Spending_Funds_Total': {'$avg': '$Avg_Country_Spending_Funds'}
        }},
        {'$project': {
            '_id': 0,
            'Avg_Spending_Funds_Total': 1
        }}
    ]
    avg_country_euro_avg_y_eu = list(db.countries_all_data.aggregate(pipeline))[0].get('Avg_Spending_Funds_Total')

    # 10E
    pipeline = [
        year_filter(bot_year, top_year, country_list),
        {'$match': {
            'Count_Contracts_B_EU_N': {'$exists': True},
        }},
        {'$group': {
            '_id': '$_id.ISO_COUNTRY_CODE',
            'Sum_Country_No_Funds': {'$sum': '$Sum_Value_Euro_B_EU_N'},
            'Count_contracts_Country_No_Funds': {'$sum': '$Count_Contracts_B_EU_N'}
        }},
        {'$project': {
            'Avg_Country_Spending_No_Funds': {'$divide': ['$Sum_Country_No_Funds', '$Count_contracts_Country_No_Funds']}
        }},
        {'$group': {
            '_id': False,
            'Avg_Spending_No_Funds_Total': {'$avg': '$Avg_Country_Spending_No_Funds'}
        }},
        {'$project': {
            '_id': 0,
            'Avg_Spending_No_Funds_Total': 1
        }}
    ]
    avg_country_euro_avg_n_eu = list(db.countries_all_data.aggregate(pipeline))[0].get('Avg_Spending_No_Funds_Total')

    return avg_country_euro_avg, avg_country_count, avg_country_offer_avg, avg_country_euro_avg_y_eu, avg_country_euro_avg_n_eu


def ex11_country_treemap(bot_year=2008, top_year=2020, country_list=countries):
    """
    Returns the count of contracts per country ('ISO_COUNTRY_CODE')
    Result filterable by floor year, roof year and country_list

    Expected Output (list of documents):
    [{country: value_1, count: value_2}, ....]

    Where:
    value_1 = Country ('ISO_COUNTRY_CODE') name, (string) (located in iso_codes collection')
    value_2 = contract count of each country, (int)
    """

    pipeline = [
        year_filter(bot_year, top_year, country_list),
        {'$group': {
            '_id': {'ISO_COUNTRY_CODE': '$_id.ISO_COUNTRY_CODE', 'Country_Name': '$Country_Name'},
            'Count_contracts_Country': {'$sum': '$Count_Contracts_Total'}
        }},
        {'$project': {
            '_id': 0,
            'country': '$_id.Country_Name',
            'count': '$Count_contracts_Country'
        }}
    ]

    list_documents = list(db.countries_all_data.aggregate(pipeline))

    if not list_documents:
        list_documents = [{'country': 0, 'count': 0}]

    return list_documents


def ex12_country_bar_1(bot_year=2008, top_year=2020, country_list=countries):
    """
    Returns the average 'VALUE_EURO' for each country, return the highest 5 countries

    Result filterable by floor year, roof year and country_list

    Expected Output (list of 5 sorted documents):
    [{country: value_1, avg: value_2}, ....]

    Where:
    value_1 = Country ('ISO_COUNTRY_CODE') name, (string) (located in iso_codes collection as 'name')
    value_2 = average 'VALUE_EURO' of each country ('ISO_COUNTRY_CODE') name, (float)
    """

    pipeline = [
        year_filter(bot_year, top_year, country_list),
        { '$match': {
            'Count_Contracts_with_Value_Euro': {'$exists': True},
        } },
        {'$group': {
            '_id': {'ISO_COUNTRY_CODE': '$_id.ISO_COUNTRY_CODE', 'Country_Name': '$Country_Name'},
            'Sum_Country_Spending': {'$sum': '$Sum_Value_Euro'},
            'Count_contracts_Country_Spending': {'$sum': '$Count_Contracts_with_Value_Euro'}
        }},
        {'$project': {
            '_id': 0,
            'country': '$_id.Country_Name',
            'avg': {'$divide': ['$Sum_Country_Spending', '$Count_contracts_Country_Spending']}
        }},
        {'$sort': {
            'avg': -1
        }},
        {'$limit': 5}
    ]

    list_documents = list(db.countries_all_data.aggregate(pipeline))

    if not list_documents:
        list_documents = [{'country': 0, 'avg': 0}]

    return list_documents


def ex13_country_bar_2(bot_year=2008, top_year=2020, country_list=countries):
    """
    Group by country and get the average 'VALUE_EURO' for each group, return the lowest, average wise, 5 documents

    Result filterable by floor year, roof year and country_list

    Expected Output (list of 5 sorted documents):
    [{country: value_1, avg: value_2}, ....]

    Where:
    value_1 = Country ('ISO_COUNTRY_CODE') name, (string) (located in cpv collection as 'cpv_division_description')
    value_2 = average 'VALUE_EURO' of each country ('ISO_COUNTRY_CODE') name, (float)
    """

    pipeline = [
        year_filter(bot_year, top_year, country_list),
        { '$match': {
            'Count_Contracts_with_Value_Euro': {'$exists': True},
        } },       
        {'$group': {
            '_id': {'ISO_COUNTRY_CODE': '$_id.ISO_COUNTRY_CODE', 'Country_Name': '$Country_Name'},
            'Sum_Country_Spending': {'$sum': '$Sum_Value_Euro'},
            'Count_contracts_Country_Spending': {'$sum': '$Count_Contracts_with_Value_Euro'}
        }},
        {'$project': {
            '_id': 0,
            'country': '$_id.Country_Name',
            'avg': {'$divide': ['$Sum_Country_Spending', '$Count_contracts_Country_Spending']}
        }},
        {'$sort': {
            'avg': 1
        }},
        {'$limit': 5}
    ]

    list_documents = list(db.countries_all_data.aggregate(pipeline))

    if not list_documents:
        list_documents = [{'country': 0, 'avg': 0}]

    return list_documents


def ex14_country_map(bot_year=2008, top_year=2020, country_list=countries):
    """
    For each country get the sum of the respective contracts 'VALUE_EURO' with 'B_EU_FUNDS'

    Result filterable by floor year, roof year and country_list

    Expected Output (list of documents):
    [{sum: value_1, country: value_2}, ....]

    Where:
    value_1 = sum 'VALUE_EURO' of country ('ISO_COUNTRY_CODE') name, (float)
    value_2 = country in ISO-3 format (string) (located in iso_codes collection)
    """

    pipeline = [
        year_filter(bot_year, top_year, country_list),
        {'$match': {
            'Sum_Value_Euro_B_EU_Y': {'$exists': True},
        }},
        {'$group': {
            '_id': {'ISO_COUNTRY_CODE': '$_id.ISO_COUNTRY_CODE', 'ISO3': '$ISO3'},
            'Sum_Country_Funds': {'$sum': '$Sum_Value_Euro_B_EU_Y'}
        }},
        {'$project': {
            '_id': 0,
            'country': '$_id.ISO3',
            'sum': '$Sum_Country_Funds'
        }}
    ]

    list_documents = list(db.countries_all_data.aggregate(pipeline))

    if not list_documents:
        list_documents = [{'country': 0, 'sum': 0}]

    return list_documents


def ex15_business_box(bot_year=2008, top_year=2020, country_list=countries):
    """
    We want five numbers, described below

    Result filterable by floor year, roof year and country_list

    Expected Output:
    (avg_business_euro_avg, avg_business_count, avg_business_offer_avg, avg_business_euro_avg_y_eu, avg_business_euro_avg_n_eu)

    Where:
    avg_business_euro_avg = average value of each company ('CAE_NAME')  contracts average 'VALUE_EURO', (int)
    avg_business_count = average value of each company ('CAE_NAME') contract count, (int)
    avg_business_offer_avg = average value of each company ('CAE_NAME') contracts average NUMBER_OFFERS', (int)
    avg_business_euro_avg_y_eu = average value of each company ('CAE_NAME') contracts average VALUE_EURO' with 'B_EU_FUNDS', (int)
    avg_business_euro_avg_n_eu = average value of each company ('CAE_NAME') contracts average 'VALUE_EURO' with out 'B_EU_FUNDS' (int)
    """
    # 15A
    pipeline = [
        year_filter(bot_year, top_year, country_list),
        # some companies don't have contracts with value euro, which lead to a
        # Count_contracts_Company_Spending = 0 and an impossible division
        { '$match': {
            'Count_Contracts_with_Value_Euro': {'$exists': True}
        }},
        { '$group': {
            '_id': '$_id.CAE_NAME',
            'Sum_Company_Spending': {'$sum': '$Sum_Value_Euro'},
            'Count_contracts_Company_Spending': {'$sum': '$Count_Contracts_with_Value_Euro'}
        }},
        { '$project': {
            'Avg_Company_Spending': {'$divide': ['$Sum_Company_Spending', '$Count_contracts_Company_Spending']}
        }},
        { '$group': {
            '_id': False,
            'Avg_Spending_Total': {'$avg': '$Avg_Company_Spending'}
        }},
        { '$project': {
            '_id': 0,
            'Avg_Spending_Total': 1
        }}
    ]
    avg_business_euro_avg = list(db.companies_all_data.aggregate(pipeline))[0].get('Avg_Spending_Total')
    
    # 15B
    pipeline = [
        year_filter(bot_year, top_year, country_list),
        { '$group': {
            '_id': '$_id.CAE_NAME',
            'Count_contracts_Company': {'$sum': '$Count_Contracts_Total'}
        }},
        { '$group': {
            '_id': False,
            'Avg_Count_Contracts_Total': {'$avg': '$Count_contracts_Company'}
        }},
        { '$project': {
            '_id': 0,
            'Avg_Count_Contracts_Total': 1
        }}
    ]
    avg_business_count = list(db.companies_all_data.aggregate(pipeline))[0].get('Avg_Count_Contracts_Total')
    
    # 15C
    pipeline = [
        year_filter(bot_year, top_year, country_list),
        # some companies don't have contracts with the attribute number of offers, which lead to a
        # Count_contracts_Company_Offers = 0 and an impossible division
        { '$match': {
            'Count_Contracts_with_Nr_Offers': {'$exists': True}
        }},
        { '$group': {
            '_id': '$_id.CAE_NAME',
            'Sum_Company_Offers': {'$sum': '$Sum_Nr_Offers'},
            'Count_contracts_Company_Offers': {'$sum': '$Count_Contracts_with_Nr_Offers'}
        }},
        { '$project': {
            'Avg_Company_Offers': {'$divide': ['$Sum_Company_Offers', '$Count_contracts_Company_Offers']}
        }},
        { '$group': {
            '_id': False,
            'Avg_NR_Offers_Total': {'$avg': '$Avg_Company_Offers'}
        }},
        { '$project': {
            '_id': 0,
            'Avg_NR_Offers_Total': 1
        }}
    ]
    avg_business_offer_avg = list(db.companies_all_data.aggregate(pipeline))[0].get('Avg_NR_Offers_Total')

    # 15D
    pipeline = [
        year_filter(bot_year, top_year, country_list),
        {'$match': {
            'Count_Contracts_B_EU_Y': {'$exists': True},
        }},
        {'$group': {
            '_id': '$_id.CAE_NAME',
            'Sum_Company_Funds': {'$sum': '$Sum_Value_Euro_B_EU_Y'},
            'Count_Contracts_Company_Funds': {'$sum': '$Count_Contracts_B_EU_Y'}
        }},
        {'$project': {
            'Avg_Company_Spending_Funds': {'$divide': ['$Sum_Company_Funds', '$Count_Contracts_Company_Funds']}
        }},
        {'$group': {
            '_id': False,
            'Avg_Spending_Funds_Total': {'$avg': '$Avg_Company_Spending_Funds'}
        }},
        {'$project': {
            '_id': 0,
            'Avg_Spending_Funds_Total': 1
        }}
    ]
    avg_business_euro_avg_y_eu = list(db.companies_all_data.aggregate(pipeline))[0].get('Avg_Spending_Funds_Total')
    
    # 15E
    pipeline = [
        year_filter(bot_year, top_year, country_list),
        {'$match': {
            'Count_Contracts_B_EU_N': {'$exists': True},
        }},
        {'$group': {
            '_id': '$_id.CAE_NAME',
            'Sum_Company_No_Funds': {'$sum': '$Sum_Value_Euro_B_EU_N'},
            'Count_contracts_Company_No_Funds': {'$sum': '$Count_Contracts_B_EU_N'}
        }},
        {'$project': {
            'Avg_Company_Spending_No_Funds': {'$divide': ['$Sum_Company_No_Funds', '$Count_contracts_Company_No_Funds']}
        }},
        {'$group': {
            '_id': False,
            'Avg_Spending_No_Funds_Total': {'$avg': '$Avg_Company_Spending_No_Funds'}
        }},
        {'$project': {
            '_id': 0,
            'Avg_Spending_No_Funds_Total': 1
        }}
    ]
    avg_business_euro_avg_n_eu = list(db.companies_all_data.aggregate(pipeline))[0].get('Avg_Spending_No_Funds_Total')

    return avg_business_euro_avg, avg_business_count, avg_business_offer_avg, avg_business_euro_avg_y_eu, avg_business_euro_avg_n_eu


def ex16_business_bar_1(bot_year=2008, top_year=2020, country_list=countries):
    """
    Returns the average 'VALUE_EURO' for company ('CAE_NAME') return the highest 5 companies
    Result filterable by floor year, roof year and country_list

    Expected Output (list of 5 sorted documents):
    [{company: value_1, avg: value_2}, ....]

    Where:
    value_1 = company ('CAE_NAME') name, (string)
    value_2 = average 'VALUE_EURO' of each company ('CAE_NAME'), (float)
    """
    pipeline = [
        year_filter(bot_year, top_year, country_list),
        # some companies don't have contracts with the attribute value euro, which lead to a
        # Count_Contracts_with_Value_Euro = 0 and an impossible division
        { '$match': {
            'Count_Contracts_with_Value_Euro': {'$exists': True}
        }},
        { '$group': {
            '_id': '$_id.CAE_NAME',
            'Sum_Company_Spending': {'$sum': '$Sum_Value_Euro'},
            'Count_contracts_Company_Spending': {'$sum': '$Count_Contracts_with_Value_Euro'}
        }},
        { '$project': {
            '_id': 0,
            'company': '$_id',
            'avg': {'$divide': ['$Sum_Company_Spending', '$Count_contracts_Company_Spending']}
        }},
        { '$sort': {
            'avg': -1
        }},
        { '$limit': 5 }
    ]

    list_documents = list(db.companies_all_data.aggregate(pipeline))

    if not list_documents:
        list_documents = [{'company': 0, 'avg': 0}]

    return list_documents


def ex17_business_bar_2(bot_year=2008, top_year=2020, country_list=countries):
    """
    Returns the average 'VALUE_EURO' for company ('CAE_NAME') return the lowest 5 companies


    Result filterable by floor year, roof year and country_list

    Expected Output (list of 5 sorted documents):
    [{company: value_1, avg: value_2}, ....]

    Where:
    value_1 = company ('CAE_NAME') name, (string)
    value_2 = average 'VALUE_EURO' of each company ('CAE_NAME'), (float)
    """

    pipeline = [
        year_filter(bot_year, top_year, country_list),
        # some companies don't have contracts with the attribute value euro, which lead to a
        # Count_Contracts_with_Value_Euro = 0 and an impossible division
        { '$match': {
            'Count_Contracts_with_Value_Euro': {'$exists': True}
        }},
        { '$group': {
            '_id': '$_id.CAE_NAME',
            'Sum_Company_Spending': {'$sum': '$Sum_Value_Euro'},
            'Count_contracts_Company_Spending': {'$sum': '$Count_Contracts_with_Value_Euro'}
        }},
        { '$project': {
            '_id': 0,
            'company': '$_id',
            'avg': {'$divide': ['$Sum_Company_Spending', '$Count_contracts_Company_Spending']}
        }},
        { '$sort': {
            'avg': 1
        }},
        { '$limit': 5 }
    ]

    list_documents = list(db.companies_all_data.aggregate(pipeline))

    if not list_documents:
        list_documents = [{'company': 0, 'avg': 0}]

    return list_documents


def ex18_business_treemap(bot_year=2008, top_year=2020, country_list=countries):
    """
    We want the count of contracts for each company 'CAE_NAME', for the highest 15
    Result filterable by floor year, roof year and country_list

    Expected Output (list of documents):
    [{company: value_1, count: value_2}, ....]

    Where:
    value_1 = company ('CAE_NAME'), (string)
    value_2 = contract count of each company ('CAE_NAME'), (int)
    """

    pipeline = [
        year_filter(bot_year, top_year, country_list),
        { '$group': {
            '_id': '$_id.CAE_NAME',
            'Count_contracts_Company': {'$sum': '$Count_Contracts_Total'}
        }},
        { '$project': {
            '_id': 0,
            'company': '$_id',
            'count': '$Count_contracts_Company'
        }},
        { '$sort': {
            'count': -1
        }},
        { '$limit': 15 }
    ]

    list_documents = list(db.companies_all_data.aggregate(pipeline))

    if not list_documents:
        list_documents = [{'company': 0, 'count': 0}]

    return list_documents

def ex19_business_map(bot_year=2008, top_year=2020, country_list=countries):
    """
    For each country get the highest company ('CAE_NAME') in terms of 'VALUE_EURO' sum contract spending

    Result filterable by floor year, roof year and country_list

    Expected Output (list of documents):
    [{company: value_1, sum: value_2, country: value_3, address: value_4}, ....]

    Where:
    value_1 = 'top' company of that particular country ('CAE_NAME'), (string)
    value_2 = sum 'VALUE_EURO' of country and company ('CAE_NAME'), (float)
    value_3 = country in ISO-3 format (string) (located in iso_codes collection)
    value_4 = company ('CAE_NAME') address, single string merging 'CAE_ADDRESS' and 'CAE_TOWN' separated by ' ' (space)
    """

    pipeline = [ 
        year_filter(bot_year, top_year, country_list),
        {'$group': {
            '_id': {
                'ISO_CODE': '$Alpha3',
                'CAE_NAME': '$_id.CAE_NAME',
                'ADDR_TOWN': '$_id.ADDR_TOWN'
            },
            'Sum_Company_Spending': {'$sum': '$Sum_Value_Euro'},
        }},
        {'$project': {
            '_id': 0,
            'company': '$_id.CAE_NAME',
            'sum': '$Sum_Company_Spending',
            'country': '$_id.ISO_CODE',
            'address': '$_id.ADDR_TOWN'
        }},
        {'$sort': {
            'country': -1,
            'sum': -1
        }},
        {'$group': {
            '_id': "$country",
            'winner': {
                '$push': {
                    'company': "$company",
                    'address': '$address',
                    'sum': "$sum",
                }
            }
        }},
        {'$project': {
            'winner': {
                '$slice': ["$winner", 1]
            }
        }},
        {'$project': {
            '_id': 0,
            'company': {'$arrayElemAt': ['$winner.company', 0]},
            'sum': {'$arrayElemAt': ['$winner.sum', 0]},
            'country': '$_id',
            'address': {'$arrayElemAt': ['$winner.address', 0]}
        }}
    ]
   
    list_documents = list(db.companies_all_data.aggregate(pipeline, allowDiskUse=True))

    if not list_documents:
        list_documents = [{'company': 0, 'sum': 0, 'country': 0, 'address': 0}]

    return list_documents


def ex20_business_connection(bot_year=2008, top_year=2020, country_list=countries):
    """
    We want the top 5 most frequent co-occurring companies ('CAE_NAME' and 'WIN_NAME')

    Result filterable by floor year, roof year and country_list

    Expected Output (list of documents):
    [{companies: value_1, count: value_2}, ....]

    Where:
    value_1 = company ('CAE_NAME') string merged with company ('WIN_NAME') separated by the string ' with ', (string)
    value_2 = co-occurring number of contracts (int)
    """
    # As we consider co-occurences of A with B and B with A the same occurrence, 
    # the order of the entities names in value_1 will be alphabetical

    pipeline = [
        year_filter(bot_year, top_year, country_list),
        { '$group': {
            '_id': '$_id.CAE_WIN',
            'Co-occurrences': {'$sum': '$Count'}
        }},
        { '$project': {
            '_id': 0,
            'companies': '$_id',
            'count': '$Co-occurrences'
        }},
        { '$sort': {'count': -1}},
        { '$limit': 5}
    ]

    list_documents = list(db.companies_occurrences.aggregate(pipeline, allowDiskUse=True))

    if not list_documents:
        list_documents = [{'companies': 0, 'count': 0}]

    return list_documents

def insert_operation(document):
    '''
        Insert operation.
        In case pre computed tables were generated for the queries they should be recomputed with the new data.

        When a new document is inserted, we update all the fields according to the ids in the collections that feed the
        queries for the dashboard. If the ids does not match an existing one, instead of updating fields, we insert a
        new document in each of those collections.
    '''
    inserted_ids = eu.insert_many(document).inserted_ids

    '''
    Create fields CPV_Corrected, CPV_Division and ADDR_TOWN in the original collection.
    - In CPV_Corrected all values have a size of 8 digits and are of type string.
    - In CPV_Division we have the 2 first digits of CPV_Corrected.
    - ADDR_TOWN is a concatenation of company's Address and Town.
    '''
    eu.update_many(
        {'CPV': {'$exists': True}, '_id': {'$in': inserted_ids}},
        [
            {"$set": {"CPV_Corrected": {'$cond': [{'$gte': [ "$CPV", 10000000 ] }, # condition
                                                  {'$toString': "$CPV"},  # true case
                                                  {"$concat": [ "0", {'$toString': "$CPV" }]} # false case
                                                 ]
                                       },
                      "ADDR_TOWN": {'$toLower': {
                          '$concat': [{'$toString': '$CAE_ADDRESS'}, ' ', {'$toString': '$CAE_TOWN'}]
                                    }}
                     }
            }
        ],
        upsert = False
    )

    eu.update_many(
        {'CPV': {'$exists': True}, '_id': {'$in': inserted_ids}},
        [
            {"$set": {"CPV_Division": {'$substr': ['$CPV_Corrected', 0, 2]}
                      }
             }
        ],
        upsert=False
    )

    new_docs = list(eu.find({"_id": {'$in': inserted_ids}}))
    for doc in new_docs:  # iterate over documents to update/insert everything organizing it by collection
        # common fields
        year = doc.get('YEAR', None)
        country = doc.get('ISO_COUNTRY_CODE', None)
        value_euro = doc.get('VALUE_EURO', None)
        nr_offers = doc.get('NUMBER_OFFERS', None)
        funds = doc.get('B_EU_FUNDS', None)

        # cpv_div_all_data collection
        cpv_div = doc.get('CPV_Division', None)
        award_value_euro = doc.get('AWARD_VALUE_EURO', None)
        dt_award = doc.get('DT_AWARD', None)
        dt_award = datetime.strptime(dt_award, '%d-%b-%y')
        dt_dispatch = doc.get('DT_DISPATCH', None)
        dt_dispatch = datetime.strptime(dt_dispatch, '%d-%b-%y')

        if dt_award and dt_dispatch:
            time_diff = (dt_dispatch - dt_award).total_seconds() * 1000
        else:
            time_diff = None

        if award_value_euro and value_euro:
            value_diff = award_value_euro - value_euro
        else:
            value_diff = None

        # companies_all_data collection
        cae_name = str(doc.get('CAE_NAME', None))
        addr_town = doc.get('ADDR_TOWN', None)

        # companies_occurrences collection
        win_name = str(doc.get('WIN_NAME', None))

        if cae_name and win_name:
            if cae_name > win_name:
                cae_win = win_name + ' with ' + cae_name
            else:
                cae_win = cae_name + ' with ' + win_name
        else:
            cae_win = None

        # CPV_DIV_ALL_DATA collection
        update_info = db.cpv_divisions_all_data.update_one(
            { '_id.YEAR': {'$eq': year},
              '_id.ISO_COUNTRY_CODE': {'$eq': country},
              '_id.CPV_Division': {'$eq': cpv_div},
            },
            [{'$set': {
                'Count_Contracts_with_Value_Euro': {'$cond': [{'$or': [{'$eq': [value_euro, None]}, {'$gte': [value_euro, 100000000]}]},
                                                              '$Count_Contracts_with_Value_Euro',
                                                              {'$sum': ['$Count_Contracts_with_Value_Euro', 1]}]
                                                    },
                'Sum_Value_Euro': {'$cond': [{'$or': [{'$eq': [value_euro, None]}, {'$gte': [value_euro, 100000000]}]},
                                             '$Sum_Value_Euro',
                                             {'$sum': ['$Sum_Value_Euro', value_euro]}]
                                   },
                'Count_Contracts_B_EU_Y': {'$cond': [{'$or': [{'$eq': [value_euro, None]}, {'$ne': [funds, 'Y']}, {'$gte': [value_euro, 100000000]}]},
                                                     '$Count_Contracts_B_EU_Y',
                                                     {'$sum': ['$Count_Contracts_B_EU_Y', 1]}]
                                           },
                'Sum_Value_Euro_B_EU_Y': {'$cond': [{'$or': [{'$eq': [value_euro, None]}, {'$ne': [funds, 'Y']}, {'$gte': [value_euro, 100000000]}]},
                                                    '$Sum_Value_Euro_B_EU_Y',
                                                    {'$sum': ['$Sum_Value_Euro_B_EU_Y', value_euro]}]
                                          },
                'Count_Contracts_B_EU_N': {'$cond': [{'$or': [{'$eq': [value_euro, None]}, {'$ne': [funds, 'N']}, {'$gte': [value_euro, 100000000]}]},
                                                     '$Count_Contracts_B_EU_N',
                                                     {'$sum': ['$Count_Contracts_B_EU_N', 1]}]
                                           },
                'Sum_Value_Euro_B_EU_N': {'$cond': [{'$or': [{'$eq': [value_euro, None]}, {'$ne': [funds, 'N']}, {'$gte': [value_euro, 100000000]}]},
                                                    '$Sum_Value_Euro_B_EU_N',
                                                    {'$sum': ['$Sum_Value_Euro_B_EU_N', value_euro]}]
                                          },
                'Count_Contracts_with_Nr_Offers': {'$cond': [{'$eq': [nr_offers, None]},
                                                             '$Count_Contracts_with_Nr_Offers',
                                                             {'$sum': ['$Count_Contracts_with_Nr_Offers', 1]}]
                                                   },
                'Sum_Nr_Offers': {'$cond': [{'$eq': [nr_offers, None]},
                                            '$Sum_Nr_Offers',
                                            {'$sum': ['$Sum_Nr_Offers', nr_offers]}]
                                  },
                'Count_Contracts_Total': {'$sum': ['$Count_Contracts_Total', 1]},
                'Count_Contracts_with_Difference_Euro': {'$cond': [{'$or': [{'$eq': [value_diff, None]}, {'$gte': [value_euro, 100000000]}]},
                                                                   '$Count_Contracts_with_Difference_Euro',
                                                                   {'$sum': ['$Count_Contracts_with_Difference_Euro', 1]}]
                                                         },
                'Total_Difference_Euro': {'$cond': [{'$or': [{'$eq': [value_diff, None]}, {'$gte': [value_euro, 100000000]}]},
                                                    '$Total_Difference_Euro',
                                                    {'$sum': ['$Total_Difference_Euro', value_diff]}]
                                          },
                'Count_Contracts_with_Difference_Time': {'$cond': [{'$eq': [time_diff, None]},
                                                                   '$Count_Contracts_with_Difference_Time',
                                                                   {'$sum': ['$Count_Contracts_with_Difference_Time', 1]}]
                                                         },
                'Total_Difference_Time': {'$cond': [{'$eq': [time_diff, None]},
                                                    '$Total_Difference_Time',
                                                    {'$sum': ['$Total_Difference_Time', time_diff]}]
                                          },
            }}],
            upsert = True
        )
    
        if update_info.upserted_id:
            # get cpv description
            pipeline = [
                { '$match': {
                    '_id': {'$eq': update_info.upserted_id}
                }},
                { '$lookup': {
                    'from': 'cpv',
                    'localField': '_id.CPV_Division',   
                    'foreignField': 'cpv_division',  
                    'as': 'cpv_division_description'
                }},
                { '$project': {
                    '_id': 1,
                    'CPV_Description': {'$arrayElemAt': ['$cpv_division_description.cpv_division_description', 0]},
                }}
            ]
            cpv_desc = list(db.cpv_divisions_all_data.aggregate(pipeline, allowDiskUse=True))[0].get('CPV_Description')

            # get country alpha3 code
            pipeline = [
                { '$match': {
                    '_id': {'$eq': update_info.upserted_id}
                }},
                { '$lookup': {
                    'from': 'iso_codes',
                    'localField': '_id.ISO_COUNTRY_CODE',   
                    'foreignField': 'alpha-2',  
                    'as': 'iso_codes'
                }},
                { '$project': {
                    '_id': 1,
                    'Alpha3': {'$arrayElemAt': ['$iso_codes.alpha-3', 0]},
                }}
            ]
            alpha3 = list(db.cpv_divisions_all_data.aggregate(pipeline, allowDiskUse=True))[0].get('Alpha3')

            db.cpv_divisions_all_data.update_one(
                {'_id': {'$eq': update_info.upserted_id}},
                [
                    {"$set": {"CPV_Description": cpv_desc,
                              "Alpha3": alpha3
                              }
                     }
                ]
            )
        else:
            alpha3 = None

        # COMPANIES_ALL_DATA collection
        update_info = db.companies_all_data.update_one(
            { '_id.YEAR': {'$eq': year},
              '_id.ISO_COUNTRY_CODE': {'$eq': country},
              '_id.CAE_NAME': {'$eq': cae_name},
              '_id.ADDR_TOWN': {'$eq': addr_town},
            },
            [{'$set': {
                'Count_Contracts_with_Value_Euro': {'$cond': [{'$or': [{'$eq': [value_euro, None]}, {'$gte': [value_euro, 100000000]}]},
                                                              '$Count_Contracts_with_Value_Euro',
                                                              {'$sum': ['$Count_Contracts_with_Value_Euro', 1]}]
                                                    },
                'Sum_Value_Euro': {'$cond': [{'$or': [{'$eq': [value_euro, None]}, {'$gte': [value_euro, 100000000]}]},
                                             '$Sum_Value_Euro',
                                             {'$sum': ['$Sum_Value_Euro', value_euro]}]
                                   },
                'Count_Contracts_B_EU_Y': {'$cond': [{'$or': [{'$eq': [value_euro, None]}, {'$ne': [funds, 'Y']}, {'$gte': [value_euro, 100000000]}]},
                                                     '$Count_Contracts_B_EU_Y',
                                                     {'$sum': ['$Count_Contracts_B_EU_Y', 1]}]
                                           },
                'Sum_Value_Euro_B_EU_Y': {'$cond': [{'$or': [{'$eq': [value_euro, None]}, {'$ne': [funds, 'Y']}, {'$gte': [value_euro, 100000000]}]},
                                                    '$Sum_Value_Euro_B_EU_Y',
                                                    {'$sum': ['$Sum_Value_Euro_B_EU_Y', value_euro]}]
                                          },
                'Count_Contracts_B_EU_N': {'$cond': [{'$or': [{'$eq': [value_euro, None]}, {'$ne': [funds, 'N']}, {'$gte': [value_euro, 100000000]}]},
                                                     '$Count_Contracts_B_EU_N',
                                                     {'$sum': ['$Count_Contracts_B_EU_N', 1]}]
                                           },
                'Sum_Value_Euro_B_EU_N': {'$cond': [{'$or': [{'$eq': [value_euro, None]}, {'$ne': [funds, 'N']}, {'$gte': [value_euro, 100000000]}]},
                                                    '$Sum_Value_Euro_B_EU_N',
                                                    {'$sum': ['$Sum_Value_Euro_B_EU_N', value_euro]}]
                                          },
                'Count_Contracts_with_Nr_Offers': {'$cond': [{'$eq': [nr_offers, None]},
                                                             '$Count_Contracts_with_Nr_Offers',
                                                             {'$sum': ['$Count_Contracts_with_Nr_Offers', 1]}]
                                                   },
                'Sum_Nr_Offers': {'$cond': [{'$eq': [nr_offers, None]},
                                            '$Sum_Nr_Offers',
                                            {'$sum': ['$Sum_Nr_Offers', nr_offers]}]
                                  },
                'Count_Contracts_Total': {'$sum': ['$Count_Contracts_Total', 1]},
            }}],
            upsert = True
        )
        
        if update_info.upserted_id:
            if not alpha3:
                # get country alpha3 code
                pipeline = [
                    { '$match': {
                        '_id.YEAR': {'$eq': year},
                        '_id.ISO_COUNTRY_CODE': {'$eq': country},
                        '_id.CPV_Division': {'$eq': cpv_div},
                    }},
                    { '$lookup': {
                        'from': 'iso_codes',
                        'localField': '_id.ISO_COUNTRY_CODE',   
                        'foreignField': 'alpha-2',  
                        'as': 'iso_codes'
                    }},
                    { '$project': {
                        '_id': 1,
                        'Alpha3': {'$arrayElemAt': ['$iso_codes.alpha-3', 0]},
                    }}
                ]

                alpha3 = list(db.companies_all_data.aggregate(pipeline, allowDiskUse=True))[0].get('Alpha3')

            db.companies_all_data.update_one(
                {'_id': {'$eq': update_info.upserted_id}},
                [
                    {"$set": {"Alpha3": alpha3
                              }
                     }
                ]
            )


        # COUNTRIES_ALL_DATA collection
        update_info = db.countries_all_data.update_one(
            { '_id.YEAR': {'$eq': year},
              '_id.ISO_COUNTRY_CODE': {'$eq': country},
            },
            [{'$set': {
                'Count_Contracts_with_Value_Euro': {'$cond': [{'$or': [{'$eq': [value_euro, None]}, {'$gte': [value_euro, 100000000]}]},
                                                              '$Count_Contracts_with_Value_Euro',
                                                              {'$sum': ['$Count_Contracts_with_Value_Euro', 1]}]
                                                    },
                'Sum_Value_Euro': {'$cond': [{'$or': [{'$eq': [value_euro, None]}, {'$gte': [value_euro, 100000000]}]},
                                             '$Sum_Value_Euro',
                                             {'$sum': ['$Sum_Value_Euro', value_euro]}]
                                   },
                'Count_Contracts_B_EU_Y': {'$cond': [{'$or': [{'$eq': [value_euro, None]}, {'$ne': [funds, 'Y']}, {'$gte': [value_euro, 100000000]}]},
                                                     '$Count_Contracts_B_EU_Y',
                                                     {'$sum': ['$Count_Contracts_B_EU_Y', 1]}]
                                           },
                'Sum_Value_Euro_B_EU_Y': {'$cond': [{'$or': [{'$eq': [value_euro, None]}, {'$ne': [funds, 'Y']}, {'$gte': [value_euro, 100000000]}]},
                                                    '$Sum_Value_Euro_B_EU_Y',
                                                    {'$sum': ['$Sum_Value_Euro_B_EU_Y', value_euro]}]
                                          },
                'Count_Contracts_B_EU_N': {'$cond': [{'$or': [{'$eq': [value_euro, None]}, {'$ne': [funds, 'N']}, {'$gte': [value_euro, 100000000]}]},
                                                     '$Count_Contracts_B_EU_N',
                                                     {'$sum': ['$Count_Contracts_B_EU_N', 1]}]
                                           },
                'Sum_Value_Euro_B_EU_N': {'$cond': [{'$or': [{'$eq': [value_euro, None]}, {'$ne': [funds, 'N']}, {'$gte': [value_euro, 100000000]}]},
                                                    '$Sum_Value_Euro_B_EU_N',
                                                    {'$sum': ['$Sum_Value_Euro_B_EU_N', value_euro]}]
                                          },
                'Count_Contracts_with_Nr_Offers': {'$cond': [{'$eq': [nr_offers, None]},
                                                             '$Count_Contracts_with_Nr_Offers',
                                                             {'$sum': ['$Count_Contracts_with_Nr_Offers', 1]}]
                                                   },
                'Sum_Nr_Offers': {'$cond': [{'$eq': [nr_offers, None]},
                                            '$Sum_Nr_Offers',
                                            {'$sum': ['$Sum_Nr_Offers', nr_offers]}]
                                  },
                'Count_Contracts_Total': {'$sum': ['$Count_Contracts_Total', 1]},
            }}],
            upsert = True
        )
        
        if update_info.upserted_id:
            # get country name and alpha3
            pipeline = [
                { '$match': {
                    '_id.YEAR': {'$eq': year},
                    '_id.ISO_COUNTRY_CODE': {'$eq': country},
                }},
                { '$lookup': {
                    'from': 'iso_codes',
                    'localField': '_id.ISO_COUNTRY_CODE',   
                    'foreignField': 'alpha-2',  
                    'as': 'iso_codes'
                }},
                { '$project': {
                    '_id': 1,
                    'Country_Name': {'$arrayElemAt': ['$iso_codes.name', 0]},
                    'ISO3': {'$arrayElemAt': ['$iso_codes.alpha-3', 0]},
                }}
            ]

            result = list(db.countries_all_data.aggregate(pipeline, allowDiskUse=True))[0]
            alpha3 = result.get('ISO3')
            country_name = result.get('Country_Name')

            db.countries_all_data.update_one(
                {'_id': {'$eq': update_info.upserted_id}},
                [
                    {"$set": {"Country_Name": country_name,
                              "ISO3": alpha3
                              }
                     }
                ]
            )


        # CONTRACTS_VALUE_EURO collection
        if year and country and cpv_div and value_euro and value_euro < 100000000:
            db.contracts_value_euro.insert(
                {
                    'YEAR': year,
                    'ISO_COUNTRY_CODE': country,
                    'VALUE_EURO': value_euro,
                    'CPV_Division': cpv_div
                }
            )
        
        # COMPANIES_OCCURRENCES
        if cae_win:
            db.companies_occurrences.update_one(
                { '_id.YEAR': {'$eq': year},
                  '_id.ISO_COUNTRY_CODE': {'$eq': country},
                  '_id.CAE_WIN': {'$eq': cae_win}
                },
                [{'$set': {
                    'Count': { '$sum': ['$Count', 1]},
                }}],
                upsert = True
            )

    return inserted_ids


query_list = [
    ex1_cpv_box, ex2_cpv_treemap, ex3_cpv_bar_1, ex4_cpv_bar_2,
    ex5_cpv_bar_3, ex6_cpv_bar_4, ex7_cpv_map, ex8_cpv_hist ,ex9_cpv_bar_diff,
    ex10_country_box, ex11_country_treemap, ex12_country_bar_1,
    ex13_country_bar_2, ex14_country_map, ex15_business_box,
    ex16_business_bar_1, ex17_business_bar_2, ex18_business_treemap,
    ex19_business_map, ex20_business_connection
]
