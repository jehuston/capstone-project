import json
import requests
import pickle
from pymongo import MongoClient

def get_recipe_info(recipe_id, api_key):
    '''
    INPUT: recipe ID number (int), API key (string)
    OUTPUT: result object

    Returns results from Food2Fork api call.
    '''
    ## Gets the recipe info and stores in dict.
    payload  = {'key' : api_key, #creds['api-key'],
                       'rId': recipe_id
                     }
    result = requests.get('http://food2fork.com/api/get', params = payload)
    return result


def extract_info(json_obj):
    '''
    INPUT: result object (JSON)
    OUTPUT: recipe entry (dict)

    Extracts relevant info (ingredients, publisher, URLS) from api response and
    prepares for storing.
    '''
    recipe_dict = {}
    recipe_dict['rec_id'] = json_obj.json()['recipe']['recipe_id']
    recipe_dict['ingredients'] = json_obj.json()['recipe']['ingredients']
    recipe_dict['publisher'] = json_obj.json()['recipe']['publisher']
    recipe_dict['source_url'] = json_obj.json()['recipe']['source_url']
    recipe_dict['image_url'] = json_obj.json()['recipe']['image_url']
    recipe_dict['title'] = json_obj.json()['recipe']['title']

    #print recipe_dict
    return recipe_dict

def write_to_json(filepath, dict_obj):
    '''
    INPUT: file, recipe dict object
    OUTPUT: None

    Writes recipe data to a JSON file. This function used before database was initialized.

    '''
    with open(filepath, "a") as json_file:
#         for line in dict_obj:
        json_file.write("{}\n".format(json.dumps(dict_obj)))

def write_to_database(recipe_dict, db):
    '''
    INPUT: recipe dict object, database connection
    OUTPUT: None

    Write recipe data dictionary object to mongoDB database.
    '''
    db.recipes.insert_one(recipe_dict)


def run_pipeline(id_list, api_key, db):
    '''
    INPUT: recipe IDs (list), API key (string), database connection
    OUTPUT: None

    Queries Food2Fork API, extracts recipe info from response, and stores in
    mongoDB.

    '''
    for i, rid in enumerate(id_list):
        cursor = db.restaurants.find_one({'rec_id': rid}) ## check if already in db
        if not cursor:
            result = get_recipe_info(rid, api_key)
            r_dict = extract_info(result)
            write_to_database(r_dict, db)
        if i % 200 == 0:
            print "Just finished number ", i
    print "Finished!"



if __name__ == '__main__':
    client = MongoClient()
    db = client['project']

    ## open file with saved recipe IDs
    with open('recipe_ids.txt') as infile: # next round saved as txt file
        id_list = [line.strip() for line in infile]


    # open api credentials
    with open('credentials/f2f_config.json') as cred: #AWS path
    # with open('../credentials/f2f_config.json') as cred: #local path
        creds = json.load(cred)
    api_key = creds['api-key']

    ids = id_list[:2000] # 6/10
    run_pipeline(ids, api_key, db)
