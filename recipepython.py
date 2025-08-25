from re import S
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS 
from bs4 import BeautifulSoup
import json
import requests
from sqlalchemy import Integer, String, DATE
from sqlalchemy.orm import Mapped, mapped_column
from datetime import date, datetime
import bcrypt
import re


#CONNECTION STRING: Server=localhost\SQLEXPRESS;Database=master;Trusted_Connection=True;


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mssql+pyodbc:///?odbc_connect=DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost\\SQLEXPRESS;DATABASE=RecipeDB;Trusted_Connection=yes;'
CORS(app)

database = SQLAlchemy(app)


signupCodes = {
    "NOMESSAGE": 0,
    "PASSNOMATCH": 1,
    "INVALPASS": 2,
    "TAKENUSER": 3,
    "INVALEMAIL": 4,
    "TAKENEMAIL": 5,
    "SUCCESS": 6
}


loginCodes = {
    "NOMESSAGE": 0,
    "INVALINFO": 1,
    "SUCCESS": 2
}

class Users(database.Model):
    userID: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str]
    email: Mapped[str]
    password: Mapped[str]
    firstname: Mapped[str]
    lastname: Mapped[str]
    lastname: Mapped[str]
    dateofacccreation: Mapped[date] = mapped_column(DATE, default=date.today)
    savedrecipes: Mapped[str]

def parse_allrecipes(soup):
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

    date_published = json_dict["datePublished"]
    site_name = json_dict["publisher"]["name"]

    nutrition = json_dict["nutrition"]



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
        "instructions": instructions,
        "date": date_published,
        "site_name": site_name,
        "nutrition": nutrition
    }

    return return_dictionary


def parse_other(soup, urlType):
    
    json_script_tag = soup.find('script', type='application/ld+json')

    json_string = json_script_tag.string

    json_data = json.loads(json_string)

    print(json_data)

    json_dict = json_data["@graph"]


    for dict in json_dict:
        if dict["@type"] == "Organization" or dict["@type"] == "WebSite":
            site_name = dict["name"]
        if dict["@type"] == "Recipe":
            if urlType == "modernhoney":
                if "@id" in dict["author"]:
                    author = dict["author"]["@id"]
                else:
                    author = dict["author"]["name"]
                review_count = dict["aggregateRating"]["ratingCount"]
                recipe_yield = dict["recipeYield"]
            else:
                author = dict["author"]["name"]
                review_count = dict["aggregateRating"]["reviewCount"]
                recipe_yield = dict["recipeYield"][1]

            rating = dict["aggregateRating"]["ratingValue"]
            recipe_name = dict["name"]
            cuisine_type = dict["recipeCuisine"]
            recipe_category = dict["recipeCategory"]
            ingredients = dict["recipeIngredient"]
            cook_time = dict["cookTime"]

            date_published = dict["datePublished"]
            nutrition = dict["nutrition"]



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
        "instructions": instructions,
        "date": date_published,
        "site_name": site_name,
        "nutrition": nutrition

    }

    return return_dictionary
    

@app.route('/parse-recipe', methods=['POST'])
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

    return_dictionary["name"] = return_dictionary["name"].replace("&#39;", "'")

    return return_dictionary


@app.route('/login', methods=['POST'])
def login_script():
    username = request.json["username"]
    password = request.json["password"].encode('utf-8') 

    


    user = database.session.scalars(database.select(Users).filter_by(username=username)).one_or_none()
    message = loginCodes["NOMESSAGE"]

    if user is None:
        message = loginCodes["INVALINFO"]

    else:
        hashbrown = user.password.encode('utf-8')
        if bcrypt.checkpw(password, hashbrown):
            message = loginCodes["SUCCESS"]
        else:
            message = loginCodes["INVALINFO"]


    return {"message": message}

@app.route('/signup', methods=['POST'])
def database_script():
    username = request.json["username"]
    password = request.json["password"].encode('utf-8') 
    retyped = request.json["retyped"].encode('utf-8') 
    email = request.json["email"]

    message = signupCodes["NOMESSAGE"]

    if password != retyped:
        message = signupCodes["PASSNOMATCH"]
    else:
        valid = re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email)
        if not valid:
            message = signupCodes["INVALEMAIL"]
        else:
            usernameCheck = database.session.execute(database.select(Users).filter_by(username=username)).one_or_none()
            if not usernameCheck is None:
                message = signupCodes["TAKENUSER"]
            else:
                emailCheck = database.session.execute(database.select(Users).filter_by(email=email)).one_or_none()
                if not emailCheck is None:
                    message = signupCodes["TAKENEMAIL"]
                else:
                    if len(password) < 8:
                        message = signupCodes["INVALPASS"]
                    else:
                        salt = bcrypt.gensalt()
                        hashbrown = bcrypt.hashpw(password, salt)
                        user = Users(
                            username=username,
                            email=email,
                            password=hashbrown
                        )
                        database.session.add(user)
                        database.session.commit()
                        message = signupCodes["SUCCESS"]

    return {"message": message}


if __name__ == '__main__':
    app.run(port=5000)