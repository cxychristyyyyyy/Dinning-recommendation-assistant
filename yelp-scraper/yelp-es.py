
import requests
import json
from requests_aws4auth import AWS4Auth
from collections import defaultdict


#access the aws
region = "us-east-1"
service = "es"
auth = AWS4Auth(accessID,accessKey,region,service)


def getCuisinces():
    """This function get the cuisinces from the Yelp"""
    offset = 0
    results = defaultdict(list)
    header = {"Authorization": "Bearer {}".format(key)}
    url = "https://api.yelp.com/v3/businesses/search"
    resultDB = []

    # the cuisines that we decide to store
    Cuisine = ["italian","chinese","thai","american","japanese"]
    for cuisine in Cuisine:
        while (offset<=950):
            parameters = "?location=NYC&term={}&limit=50&offset={}".format(cuisine,str(offset))
            newURL = url+parameters
            r = requests.get(newURL,headers = header)
            response = json.loads(r.text)
            results[cuisine] = results[cuisine] + response["businesses"]
            resultDB = resultDB + response["businesses"]
            offset += 50
        offset=0
        print(len(results[cuisine]))

    writeToJson(results)
    return results, resultDB


def writeToJson(results):
    """
    This function store the results into a json file
    :param results:
    :return:
    """
    Cuisine = ["italian", "chinese", "thai", "american", "japanese"]
    id = 0

    #write the data into the json with the format es needed
    f = open("data.json","a")
    for cuisine in Cuisine:
        for rest in results[cuisine]:
            header = {"index": {"_index": "restaurants", "_id": id}}
            dic = {}
            dic["Cuisine"] = cuisine
            dic["RestaurantID"] = rest["id"]
            f.write(json.dumps(header))
            f.write("\r\n")
            f.write(json.dumps(dic))
            f.write("\r\n")
            id += 1
    f.close()








result,resultDB = getCuisinces()





