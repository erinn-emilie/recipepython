from flask import Flask, jsonify, request
from flask_cors import CORS 
from bs4 import BeautifulSoup
import json
import requests

app = Flask(__name__)
CORS(app)


def parse_allrecipes(soup):
    json_script_tag = soup.find('script', type='application/ld+json')
    json_string = json_script_tag.string
    json_data = json.loads(json_string)
    json_dict = json_data[0]


    author = json_dict["author"][0]["name"]

    recipe_name = json_dict["headline"]
    recipe_name = recipe_name.replace("&#39;", "'")

    cuisine_type = json_dict["recipeCuisine"]
    recipe_category = json_dict["recipeCategory"]
    ingredients = json_dict["recipeIngredient"]
    cook_time = json_dict["cookTime"]
    rating = json_dict["aggregateRating"]["ratingValue"]
    review_count = json_dict["aggregateRating"]["ratingCount"]
    recipe_yield = json_dict["recipeYield"]

    stepsList = json_dict["recipeInstructions"]
    instructions = []

    for step in stepsList:
        instructions.append(step["text"])

    return_dictionary = {
        "author": author,
        "name": recipe_name,
        "cuisine": cuisine_type,
        "category": recipe_category,
        "ingredients": ingredients,
        "cook_time": cook_time,
        "rating": rating,
        "reviews": review_count,
        "yield": recipe_yield,
        "instructions": instructions
    }

    return return_dictionary


def parse_other(soup, urlType):
    
    json_script_tag = soup.find('script', type='application/ld+json')

    json_string = json_script_tag.string

    json_data = json.loads(json_string)

    print(json_data)

    json_dict = json_data["@graph"]


    for dict in json_dict:
        if dict["@type"] == "Recipe":

            if urlType == "modernhoney":
                if "@id" in dict["author"]:
                    author = dict["author"]["@id"]
                else:
                    author = dict["author"]["name"]
                rating = dict["aggregateRating"]["ratingValue"]
                review_count = dict["aggregateRating"]["ratingCount"]
                recipe_yield = dict["recipeYield"]
            else:
                author = dict["author"]["name"]
                rating = dict["aggregateRating"]["ratingValue"]
                review_count = dict["aggregateRating"]["reviewCount"]
                recipe_yield = dict["recipeYield"][1]


            recipe_name = dict["name"]
            cuisine_type = dict["recipeCuisine"]
            recipe_category = dict["recipeCategory"]
            ingredients = dict["recipeIngredient"]
            cook_time = dict["cookTime"]

            stepsList = dict["recipeInstructions"]
            instructions = []

            for step in stepsList:
                instructions.append(step["text"])

    
    return_dictionary = {
        "author": author,
        "name": recipe_name,
        "cuisine": cuisine_type,
        "category": recipe_category,
        "ingredients": ingredients,
        "cook_time": cook_time,
        "rating": rating,
        "reviews": review_count,
        "yield": recipe_yield,
        "instructions": instructions
    }

    return return_dictionary
    

@app.route('/run-script', methods=['POST'])
def run_script():
    url = request.json["url"]
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'}
    page = requests.get(url, headers=headers)
    soup = BeautifulSoup(page.text, 'html.parser')

    if "allrecipes" in url:
        return_dictionary = parse_allrecipes(soup)
    elif "modernhoney" in url:
        return_dictionary = parse_other(soup, "modernhoney")
    else:
        return_dictionary = parse_other(soup, "pinchofyum")


    return return_dictionary

if __name__ == '__main__':
    app.run(port=5000)