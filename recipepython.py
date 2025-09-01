from ast import parse
from re import S
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS 
from bs4 import BeautifulSoup
import json
import requests
from sqlalchemy import Integer, String, DATE, Numeric, cast
from sqlalchemy.orm import Mapped, mapped_column
from datetime import date, datetime
import bcrypt
import re
import urllib
import random
from datetime import datetime as dt






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

saveRecipeCodes = {
    "FAILURE": 0,
    "SUCCESS": 1
}

badParseCodes = {
    "INVALURL": 0
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

class Recipes(database.Model):
    recipeID: Mapped[int] = mapped_column(primary_key=True)
    author: Mapped[str]
    name: Mapped[str]
    cuisine: Mapped[str]
    category: Mapped[str]
    ingredients: Mapped[str]
    cook_time: Mapped[str]
    rating: Mapped[float]
    reviews: Mapped[int]
    yield_col: Mapped[str] = mapped_column('yield', database.String(50))     
    instructions: Mapped[str]
    date: Mapped[date] = mapped_column(DATE)
    site_name: Mapped[str]
    nutrition: Mapped[str]
    url: Mapped[str]
    weighted_rating: Mapped[float]

class Recipebookpages(database.Model):
    recipepageID: Mapped[int] = mapped_column(primary_key=True)
    fk_userID: Mapped[int]
    fk_recipeID: Mapped[int]


def check_key(dictionary, key):
    if key in dictionary:
        return dictionary[key]
    return ""

def check_keys(dictionary, key1, key2):
    if key1 in dictionary:
        if key2 in dictionary[key1]:
            return dictionary[key1][key2]
    return ""

def find_right_key(dictionary, keyList):
    for key in keyList:
        if key in dictionary:
            return dictionary[key]
    return ""

def find_right_dict_and_key(dictionary, primKey, keyList):
    if primKey in dictionary:
        return find_right_key(dictionary[primKey], keyList)
    else:
        return ""


def make_str_from_list(list_obj, seperator):
    return_str = ""
    print(list_obj)
    for idx, item in enumerate(list_obj):
        if idx == 0:
            return_str = str(item)
        else:
            return_str = return_str + seperator + str(item)

    return return_str

def make_list_from_str(str, seperator):
    split = str.split(seperator)
    return_list = []
    for bit in split:
        bit = bit.strip()
        if bit != "":
            return_list.append(bit)
    return return_list



def parse_allrecipes(json_data):
    json_dict = json_data[0]

    stepsList = check_key(json_dict,"recipeInstructions")
    ingredients = check_key(json_dict,"recipeIngredient")


    if stepsList != "" and ingredients != "":
        instructions = []

        for step in stepsList:
            text = step["text"].strip()
            text = text.replace("&#39;", "'").replace("&amp;", "&").replace("&nbsp;", "")
            instructions.append(text)

        cuisine = check_key(json_dict,"recipeCuisine")
        cuisineStr = make_str_from_list(cuisine, "-")

        category = check_key(json_dict,"recipeCategory")
        categoryStr = make_str_from_list(category, "-")

        recipe_yield = check_key(json_dict,"recipeYield")
        yield_field = ""
        if isinstance(recipe_yield, list):
            if len(recipe_yield) == 1:
                yield_field = recipe_yield[0]
            else:
                yield_field = recipe_yield[1]
        else:
            yield_field = recipe_yield

        cooktime = check_key(json_dict,"cookTime")
        cooktime = cooktime.replace("PT", "")

        return_dictionary = {
            "author": json_dict["author"][0]["name"],
            "name": check_key(json_dict,"headline").replace("&#39;", "'").replace("&amp;", "&"),
            "cuisine": cuisineStr,
            "category": categoryStr,
            "ingredients": ingredients,
            "cook_time": cooktime,
            "rating": check_keys(json_dict,"aggregateRating", "ratingValue"),
            "reviews": check_keys(json_dict,"aggregateRating","ratingCount"),
            "yield": yield_field,
            "instructions": instructions,
            "date": check_key(json_dict,"datePublished"),
            "site_name": check_keys(json_dict,"publisher","name"),
            "nutrition": check_key(json_dict,"nutrition"),
            "weighted_rating": "0",
            "userliked": "false",
        }
    else:
        return_dictionary = {"message": "FAILURE"}

    return return_dictionary


def parse_other(json_data):

    json_dict = json_data["@graph"]
    return_dictionary = {}
    site_name = ""

    for dic in json_dict:
        if dic["@type"] == "Organization" or dic["@type"] == "WebSite":
            site_name = check_key(dic,"name")

        if dic["@type"] == "Recipe":

            recipe_yield = check_key(dic,"recipeYield")
            if isinstance(recipe_yield,list):
                recipe_yield = recipe_yield[0]

            ingredients = check_key(dic,"recipeIngredient")
            stepsList = check_key(dic,"recipeInstructions")

            if ingredients != "" and stepsList != "":
                stepsList = dic["recipeInstructions"]

                itemListElement = check_key(stepsList[0], "itemListElement")
                if itemListElement != "":
                    stepsList = itemListElement

                instructions = []
                for step in stepsList:
                    if isinstance(step, dict) and check_key(step, "text") != "":
                        text = step["text"].strip()
                        text = text.replace("&#39;", "'").replace("&amp;", "&").replace("&nbsp;", "").replace("&#8217;", "'")
                        instructions.append(text)

                cuisineStr = ""
                cuisine = check_key(dic,"recipeCuisine")
                if isinstance(cuisine, list):
                    cuisineStr = make_str_from_list(cuisine, "-")
                else:
                    cuisineStr = cuisine

                categoryStr = ""
                category = check_key(dic,"recipeCategory")
                if isinstance(category, list):
                    categoryStr = make_str_from_list(category, "-")
                else:
                    categoryStr = category

                cook_time = check_key(dic,"cookTime").replace("PT", "")
                                            
                return_dictionary = {
                    "author": check_key(dic["author"], "name"),
                    "name": check_key(dic,"name").replace("&#39;", "'").replace("&amp;", "&").replace("&#8217;", "'"),
                    "cuisine": cuisineStr,
                    "category": categoryStr,
                    "ingredients": ingredients,
                    "cook_time": cook_time,
                    "rating": find_right_dict_and_key(dic,"aggregateRating", ["ratingValue"]),
                    "reviews": find_right_dict_and_key(dic, "aggregateRating",["ratingCount","reviewCount"]),
                    "yield": recipe_yield,
                    "instructions": instructions,
                    "date": check_key(dic,"datePublished"),
                    "site_name": site_name,
                    "nutrition": check_key(dic,"nutrition"),
                    "weighted_rating": "0",
                    "userliked": "false",
                }
            else:
                return_dictionary = {"message": "FAILURE"}

    return return_dictionary



def parse_from_database(recipe_obj):
    # All the data from the database. ingredientsStr and instructionsStr needs to be put into an array of stringss, nutritionStr needs to be put in a dictionary
    ingredientsStr = recipe_obj.ingredients
    instructionsStr = recipe_obj.instructions
    nutritionStr = recipe_obj.nutrition

    instructionArr = make_list_from_str(instructionsStr, "---")
    ingredientArr = make_list_from_str(ingredientsStr, "---")


    nutritionDict = {}
    nutritionSplit = nutritionStr.split("---")
    for nutrition in nutritionSplit:
        nutrition = nutrition.strip()
        if nutrition != "":
            nutritionBites = nutrition.split(":")
            nutritionDict[nutritionBites[0]] = nutritionBites[1]

    date = recipe_obj.date
    dateStr = date.strftime("%B %d, %Y")


    return_dictionary = {
        "author": recipe_obj.author,
        "name": recipe_obj.name,
        "cuisine": recipe_obj.cuisine,
        "category": recipe_obj.category,
        "ingredients": ingredientArr,
        "cook_time": recipe_obj.cook_time,
        "rating": recipe_obj.rating,
        "reviews": recipe_obj.reviews,
        "yield": recipe_obj.yield_col,
        "instructions": instructionArr,
        "date": dateStr,
        "site_name": recipe_obj.site_name,
        "nutrition": nutrition,
        "url": recipe_obj.url,
        "userliked": "false",
        "weighted_rating": recipe_obj.weighted_rating
    }

    return return_dictionary



def save_to_database(data_dict, url):

    ingredients = data_dict["ingredients"]
    ingredientStr = make_str_from_list(ingredients, "---")


    instructions = data_dict["instructions"]
    instructionStr = make_str_from_list(instructions, "---")

    nutrition = data_dict["nutrition"]
    nutritionStr = ""
    if isinstance(nutrition, dict):
        for key, value in nutrition.items():
            nutritionStr = nutritionStr + "---" + str(key) +":" + str(value)
     

    newrecipe = Recipes(
        author = data_dict["author"],
        name = data_dict["name"],
        cuisine = data_dict["cuisine"],
        category = data_dict["category"],
        ingredients = ingredientStr,
        cook_time = data_dict["cook_time"],
        rating = cast(data_dict["rating"], Numeric),
        reviews = cast(data_dict["reviews"],Numeric),
        yield_col = data_dict["yield"],
        instructions = instructionStr,
        date = data_dict["date"],
        site_name = data_dict["site_name"],
        nutrition = nutritionStr,
        url = url,
        weighted_rating = cast(data_dict["weighted_rating"], Numeric)
    )
    database.session.add(newrecipe)
    database.session.commit()


@app.route('/parse-recipe', methods=['POST'])
def run_script():
    url = request.json["url"]
    username = request.json["username"]
    recipe = database.session.scalars(database.select(Recipes).filter_by(url=url)).one_or_none()
    return_dictionary = {}
    
    #First, check if recipe is already in the database
    if not recipe is None:
        # If it is we parse it from the database
        return_dictionary = parse_from_database(recipe)
        recipeID = recipe.recipeID
        # Then we check to see if the user is logged in
        if username != "N/A":
            user = database.session.scalars(database.select(Users).filter_by(username=username)).one_or_none()
            page = database.session.scalars(database.select(Recipebookpages).filter_by(fk_userID=user.userID, fk_recipeID=recipeID)).one_or_none()
            if not page is None:
                return_dictionary["userliked"] = "true"

        return return_dictionary

    else: 
        # If it isn't we parse it from the website
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'}
            page = requests.get(url, headers=headers)
            page.raise_for_status()  

            soup = BeautifulSoup(page.text, 'html.parser')

            json_script_tag = soup.find('script', type='application/ld+json')
            json_string = json_script_tag.string
            json_data = json.loads(json_string)

            if "allrecipes" in url:
                return_dictionary = parse_allrecipes(json_data)
            else:
                return_dictionary = parse_other(json_data)

            message = check_key(return_dictionary, "message")
            if message == "":
                return_dictionary["name"] = return_dictionary["name"].replace("&#39;", "'")

                if (return_dictionary["rating"] != "" and not return_dictionary["rating"] is None ) and (return_dictionary["reviews"] != "" and not return_dictionary["reviews"] is None ):
                    rating = round(float(return_dictionary["rating"]), 2)
                    reviews = round(float(return_dictionary["reviews"]), 2)
                    return_dictionary["weighted_rating"] = str(round(rating*reviews, 2))

                save_to_database(return_dictionary, url)
        
            return return_dictionary

        except requests.exceptions.MissingSchema as e:
            return {"message": badParseCodes["INVALURL"]}
        except requests.exceptions.HTTPError as e:
            return {"message": badParseCodes["INVALURL"]}





@app.route('/login', methods=['POST'])
def login_script():
    username = request.json["username"]
    password = request.json["password"].encode('utf-8') 

    user = database.session.scalars(database.select(Users).filter_by(username=username)).one_or_none()
    message = loginCodes["NOMESSAGE"]
    userid = -1

    if user is None:
        message = loginCodes["INVALINFO"]

    else:
        hashbrown = user.password.encode('utf-8')
        if bcrypt.checkpw(password, hashbrown):
            message = loginCodes["SUCCESS"]
            userid = user.userID
        else:
            message = loginCodes["INVALINFO"]

    return {"message": message, "userid": userid}




@app.route('/signup', methods=['POST'])
def signup_script():
    username = request.json["username"]
    password = request.json["password"].encode('utf-8') 
    retyped = request.json["retyped"].encode('utf-8') 
    email = request.json["email"]

    message = signupCodes["NOMESSAGE"]
    userid = -1

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
                        dbuser = database.session.scalars(database.select(Users).filter_by(username=username, password=hashbrown)).one_or_none()
                        userid = dbuser.userID
                        message = signupCodes["SUCCESS"]

    return {"message": message, "userid": userid}



@app.route('/save-recipe', methods=['POST'])
def save_recipe():
    username = request.json["username"]
    userid = request.json["userid"]

    url = request.json["url"]
    recipename = request.json["name"]

    message = saveRecipeCodes["FAILURE"]

    # user and recipe are the database objects that represent the relevent user and recipe
    user = database.session.scalars(database.select(Users).filter_by(userID=userid, username=username)).one_or_none()
    recipe = database.session.scalars(database.select(Recipes).filter_by(url=url, name=recipename)).one_or_none()

    if not recipe is None and user is not None:

        page = Recipebookpages(
            fk_userID = user.userID,
            fk_recipeID = recipe.recipeID,
        )
        database.session.add(page)
        database.session.commit()    
        message = saveRecipeCodes["SUCCESS"]
    else:
        message = saveRecipeCodes["FAILURE"]

    # Then we return the message
    return {"message": message}

        

@app.route('/fetch-data', methods=['POST'])
def fetch_data():
    name = request.json["name"]
    author = request.json["author"]
    site_name = request.json["site_name"]
    cuisine = request.json["cuisine"]
    category = request.json["category"]

    username = request.json["username"]
    savedRecipesOnly = request.json["savedRecipesOnly"]
    offset = request.json["offset"]

    return_list = []

    if username != "":
            user = database.session.scalars(database.select(Users).filter_by(username=username)).one_or_none()
            pages = database.session.scalars(database.select(Recipebookpages).filter_by(fk_userID=user.userID)).all()

            if savedRecipesOnly == "true":
                for page in pages: 
                    recipeID = page.fk_recipeID
                    recipe = database.session.scalars(database.select(Recipes).filter_by(recipeID = recipeID)).one_or_none()
                    if (name in recipe.name) and (author in recipe.author) and (site_name in recipe.site_name) and (cuisine in recipe.cuisine) and (category in recipe.category):
                        dic = parse_from_database(recipe)
                        dic["userliked"] = "true"
                        return_list.append(dic)
            else:
                all_saved_ids = []
                for page in pages:
                    all_saved_ids.append(page.fk_recipeID)
                all_recipes = database.session.scalars(database.select(Recipes).order_by(Recipes.weighted_rating.desc()).filter(Recipes.name.icontains(name), Recipes.author.icontains(author), Recipes.site_name.icontains(site_name), Recipes.cuisine.icontains(cuisine), Recipes.category.icontains(category)).offset(offset).limit(30)).all()
                for recipe in all_recipes:
                    dic = parse_from_database(recipe)
                    if recipe.recipeID in all_saved_ids:
                        dic["userliked"] = "true"
                    return_list.append(dic)
    else:
        all_recipes = database.session.scalars(database.select(Recipes).order_by(Recipes.weighted_rating.desc()).filter(Recipes.name.icontains(name), Recipes.author.icontains(author), Recipes.site_name.icontains(site_name), Recipes.cuisine.icontains(cuisine), Recipes.category.icontains(category)).offset(offset).limit(30)).all()
        for recipe in all_recipes:
            return_list.append(parse_from_database(recipe))

    return return_list






              


if __name__ == '__main__':
    app.run(port=5000)