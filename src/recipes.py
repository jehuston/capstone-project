import json
import requests
import pickle
from pymongo import MongoClient

def get_recipe_info(recipe_id, api_key):
    ## Gets the recipe info and stores in dict.
    payload  = {'key' : api_key, #creds['api-key'],
                       'rId': recipe_id
                     }
    result = requests.get('http://food2fork.com/api/get', params = payload)
    return result


def extract_info(json_obj):
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
    with open(filepath, "a") as json_file:
#         for line in dict_obj:
        json_file.write("{}\n".format(json.dumps(dict_obj)))

def write_to_database(dict_obj, db):
    db.recipes.insert_one(dict_obj)


def run_pipeline(id_list, api_key, db):
    for i, id_ in enumerate(id_list):
        result = get_recipe_info(id_, api_key)
        r_dict = extract_info(result)
        write_to_database(r_dict, db)
        if i % 200 == 0:
            print "Just finished number ", i
    print "Finished!"



if __name__ == '__main__':
    client = MongoClient()
    db = client['project']

    ## open pickle file with saved recipe IDs
    with open('recipe_ids_pt2.pkl') as infile:
        id_list = pickle.load(infile)
    ## open api credentials
    with open('credentials/f2f_config.json') as cred:
        creds = json.load(cred)

    api_key = creds['api-key']
    ids = id_list[1373:3873] ## update limits for what you want to call that day

    run_pipeline(ids, api_key, db)
