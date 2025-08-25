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
                nutrition = {}

            else:
                author = dict["author"]["name"]
                review_count = dict["aggregateRating"]["reviewCount"]
                recipe_yield = dict["recipeYield"][1]
                nutrition = dict["nutrition"]

            rating = dict["aggregateRating"]["ratingValue"]
            recipe_name = dict["name"]
            cuisine_type = dict["recipeCuisine"]
            recipe_category = dict["recipeCategory"]
            ingredients = dict["recipeIngredient"]
            cook_time = dict["cookTime"]

            date_published = dict["datePublished"]



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

    # If the recipe already exists in the database
    if not recipe is None:
        # recipeid is set to the unique id of the recipe
        recipeid = recipe.recipeID

        # If the user already has saved recipes
        if not savedrecipes is None:
            # We split up the recipe ids' in the string and iterate through them, where curID is the current id from the string that we are on
            slices = savedrecipes.split("--")
            for bite in slices:
                bite = bite.trim()
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
    # If the recipe is None, that means it is not in the database and we need to add it.
    else:
        # cuisine and category are initalized
        cuisine = request.json["cuisine"]
        cuisineStr = cuisine[0]
        category = request.json["category"]
        categoryStr = category[0]

        # ingredients, instructions, and nutrition are formatted into strings to be stored
        ingredients = request.json["ingredients"]
        ingredientStr = ""
        for ingredient in ingredients:
           ingredientStr = ingredientStr + "---" + str(ingredient)

        instructions = request.json["instructions"]
        instructionStr = ""
        for instruction in instructions:
            instructionStr = instructionStr + "---" + str(instruction)

        nutrition = request.json["nutrition"]
        nutritionStr = ""
        for key, value in nutrition.items():
            nutritionStr = nutritionStr + "---" + str(key) +":" + str(value)

        # Then the new recipe object is made, and the object is added to the database and committed
        newrecipe = Recipes(
            author = request.json["author"],
            name = request.json["name"],
            cuisine = cuisineStr,
            category = categoryStr,
            ingredients = ingredientStr,
            cook_time = request.json["cook_time"],
            rating = request.json["rating"],
            reviews = request.json["reviews"],
            yield_col = request.json["yield"],
            instructions = instructionStr,
            date = request.json["date"],
            site_name = request.json["site_name"],
            nutrition = nutritionStr,
            url = request.json["url"]
        )
        database.session.add(newrecipe)
        database.session.commit()

        # newdbrecipe is then retrieved back from the database so we can access its unique recipe id
        newdbrecipe = database.session.scalars(database.select(Recipes).filter_by(url=url, name=recipename)).one_or_none()
        newrecipeid = newdbrecipe.recipeID

        # If the user already has saved recipes, we append the newrecipeid to the current savedrecipes string and store it in final recipes. If not
        # we add it as the only thing in the finalsaverecipes string
        if not savedrecipes is None:
            finalsaverecipes = savedrecipes + "---" + str(newrecipeid)
        else:
            finalsaverecipes = str(newrecipeid)

        # The message is success
        message = saveRecipeCodes["SUCCESS"]

    # If we have a message of succes we can go ahead and change the users' savedrecipes string to our finalsaverecipes and commit that to the database
    if message == saveRecipeCodes["SUCCESS"]:
        user.savedrecipes = finalsaverecipes
        database.session.commit()

    # Then we return the message
    return {"message": message}

        

        





              


if __name__ == '__main__':
    app.run(port=5000)