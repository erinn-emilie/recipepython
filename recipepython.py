from flask import Flask, jsonify, request
from flask_cors import CORS 
from bs4 import BeautifulSoup
import json
import requests

app = Flask(__name__)
CORS(app)

@app.route('/run-script', methods=['POST'])
def run_script():

    url = request.json["url"]
    page = requests.get(url)
    soup = BeautifulSoup(page.text, 'html.parser')


    json_script_tag = soup.find('script', type='application/ld+json')
    json_string = json_script_tag.string
    json_data = json.loads(json_string)
    json_dict = json_data[0]


    author = json_dict["author"][0]["name"]
    recipe_name = json_dict["headline"]
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

if __name__ == '__main__':
    app.run(port=5000)