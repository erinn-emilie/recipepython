####
from ast import parse
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
    "NOMESSAGE": 0,
    "INVALUSER": 1,
    "DOUBLESAVE": 2,
    "SUCCESS": 3
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
    savedingredients: Mapped[str]

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



def parse_allrecipes(json_data):
    json_dict = json_data[0]

    stepsList = json_dict["recipeInstructions"]
    instructions = []

    for step in stepsList:
        instructions.append(step["text"])


    if "aggregateRating" in json_dict:
        rating = json_dict["aggregateRating"]["ratingValue"]
        reviews = json_dict["aggregateRating"]["ratingCount"]
    else:
        rating = "Not available"
        reviews = "Not available"

    return_dictionary = {
        "author": json_dict["author"][0]["name"],
        "name": json_dict["headline"],
        "cuisine": json_dict["recipeCuisine"],
        "category": json_dict["recipeCategory"],
        "ingredients": json_dict["recipeIngredient"],
        "cook_time": json_dict["cookTime"],
        "rating": rating,
        "reviews": reviews,
        "yield": json_dict["recipeYield"],
        "instructions": instructions,
        "date": json_dict["datePublished"],
        "site_name": json_dict["publisher"]["name"],
        "nutrition": json_dict["nutrition"],
        "userliked": "false"
    }

    return return_dictionary


def parse_other(json_data, urlType):

    json_dict = json_data["@graph"]


    for dic in json_dict:
        if dic["@type"] == "Organization" or dic["@type"] == "WebSite":
            site_name = dic["name"]

        if dic["@type"] == "Recipe":

            if "@id" in dic["author"]:
                author = dic["author"]["@id"]
            elif "name" in dic["author"]:
                author = dic["author"]["name"]
            else:
                author = "Not available"


            if "aggregateRating" in dic:
                rating = dic["aggregateRating"]["ratingValue"]
                if "ratingCount" in dic["aggregateRating"]:
                    review_count =  dic["aggregateRating"]["ratingCount"]
                elif "reviewCount" in dic["aggregateRating"]:
                    review_count = dic["aggregateRating"]["reviewCount"]
                else:
                    review_count = "Not available"
            else:
                rating = "Not available"
                review_count = "Not available"


            if "nutrition" in dic:
                nutrition = dic["nutrition"]
            else:
                nutrition = {}



            if urlType == "modernhoney":
                recipe_yield = dic["recipeYield"]

            else:
                recipe_yield = dic["recipeYield"][1]

            recipe_name = dic["name"]
            cuisine_type = dic["recipeCuisine"]
            recipe_category = dic["recipeCategory"]
            ingredients = dic["recipeIngredient"]
            cook_time = dic["cookTime"]
            date_published = dic["datePublished"]



            stepsList = dic["recipeInstructions"]
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
        "nutrition": nutrition,
        "userliked": "false"
    }

    return return_dictionary



def parse_from_database(recipe_obj):
    # All the data from the database. ingredientsStr and instructionsStr needs to be put into an array of stringss, nutritionStr needs to be put in a dictionary
    ingredientsStr = recipe_obj.ingredients
    instructionsStr = recipe_obj.instructions
    nutritionStr = recipe_obj.nutrition

    instructionArr = []

    instructionSplit = instructionsStr.split("---")
    for instruction in instructionSplit:
        instruction = instruction.strip()
        if instruction != "":
            instructionArr.append(instruction)

    ingredientArr = []
    ingredientSplit = ingredientsStr.split("---")
    for ingredient in ingredientSplit:
        ingredient = ingredient.strip()
        if ingredient != "":
            ingredientArr.append(ingredient)

    nutritionDict = {}
    nutritionSplit = nutritionStr.split("---")
    for nutrition in nutritionSplit:
        nutrition = nutrition.strip()
        if nutrition != "":
            nutritionBites = nutrition.split(":")
            nutritionDict[nutritionBites[0]] = nutritionBites[1]

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
        "date": recipe_obj.date,
        "site_name": recipe_obj.site_name,
        "nutrition": nutrition,
        "userliked": "false"
    }

    return return_dictionary



def save_to_database(data_dict, url):

    ingredients = data_dict["ingredients"]
    ingredientStr = ""
    for ingredient in ingredients:
        ingredientStr = ingredientStr + "---" + str(ingredient)

    instructions = data_dict["instructions"]
    instructionStr = ""
    for instruction in instructions:
        instructionStr = instructionStr + "---" + str(instruction)

    nutrition = data_dict["nutrition"]
    nutritionStr = ""
    for key, value in nutrition.items():
        nutritionStr = nutritionStr + "---" + str(key) +":" + str(value)

    newrecipe = Recipes(
        author = data_dict["author"],
        name = data_dict["name"],
        cuisine = data_dict["cuisine"],
        category = data_dict["category"],
        ingredients = ingredientStr,
        cook_time = data_dict["cook_time"],
        rating = data_dict["rating"],
        reviews = data_dict["reviews"],
        yield_col = data_dict["yield"],
        instructions = instructionStr,
        date = data_dict["date"],
        site_name = data_dict["site_name"],
        nutrition = nutritionStr,
        url = url
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
            savedrecipes = user.savedrecipes
            savedSplit = savedrecipes.split("---")
            for saved in savedSplit:
                saved = saved.strip()
                if saved != "":
                    savedInt = int(saved)
                    if savedInt == recipeID:
                        return_dictionary["userLiked"] = "true"
    else: 
        # If it isn't we parse it from the website
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'}
        page = requests.get(url, headers=headers)
        soup = BeautifulSoup(page.text, 'html.parser')

        json_script_tag = soup.find('script', type='application/ld+json')
        json_string = json_script_tag.string
        json_data = json.loads(json_string)

        if "allrecipes" in url:
            return_dictionary = parse_allrecipes(json_data)
        elif "modernhoney" in url:
            return_dictionary = parse_other(json_data, "modernhoney")
        else:
            return_dictionary = parse_other(json_data, "pinchofyum")

        return_dictionary["name"] = return_dictionary["name"].replace("&#39;", "'")

        save_to_database(return_dictionary, url)

    return return_dictionary



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
    # The usernamed and userid of the user that will have a recipe added to it
    username = request.json["username"]
    userid = request.json["userid"]
    # The url and naem of the recipe that will be added to the database and/or user
    url = request.json["url"]
    recipename = request.json["name"]

    # Initalizing some helper variables, message will be returned to client, initially there is no message
    # doublesave indicated that the user has already saved this recipe, initially it is false
    # finalsaverecipes is a placeholder for the string that will eventually hold all the recipe id's that the user has saved
    message = saveRecipeCodes["NOMESSAGE"]
    doublesave = False
    finalsaverecipes = ""

    # user and recipe are the database objects that represent the relevent user and recipe
    user = database.session.scalars(database.select(Users).filter_by(userID=userid, username=username)).one_or_none()
    recipe = database.session.scalars(database.select(Recipes).filter_by(url=url, name=recipename)).one_or_none()

    # savedrecipes is the string that holds the users' current saved recipes string
    savedrecipes = user.savedrecipes

    # recipeid is set to the unique id of the recipe
    recipeid = recipe.recipeID

    # If the user already has saved recipes
    if not savedrecipes is None:
        # We split up the recipe ids' in the string and iterate through them, where curID is the current id from the string that we are on
        slices = savedrecipes.split("--")
        for bite in slices:
            bite = bite.strip()
            curID = int(bite)
            # If curID is equal to the recipeid we are looking for, that means the user has already saved this recipe. The message is set and doublesave is set to true
            if curID == recipeid:
                message = saveRecipeCodes["DOUBLESAVE"]
                doublesave = True
                break
        # If doublesave isn't true, we append the recipeid to the end of the users' current savedrecipes string and store it in finalsaverecipes. The message is success
        if not doublesave:
            finalsaverecipes = savedrecipes + "--" + str(recipeid)
            message = saveRecipeCodes["SUCCESS"]
    # If savedrecipes is empty, finalsaverecipes becomes just this recipeid, as it is the only recipe the user has saved.
    else:
        finalsaverecipes = str(recipeid)
        message = saveRecipeCodes["SUCCESS"]

    # If we have a message of succes we can go ahead and change the users' savedrecipes string to our finalsaverecipes and commit that to the database
    if message == saveRecipeCodes["SUCCESS"]:
        user.savedrecipes = finalsaverecipes
        database.session.commit()

    # Then we return the message
    return {"message": message}

        

        





              


if __name__ == '__main__':
    app.run(port=5000)