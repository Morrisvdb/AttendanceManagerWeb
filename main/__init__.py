from flask import Flask, request
from flask_babel import Babel
from flask_babel_js import BabelJS
from dotenv import load_dotenv, find_dotenv, set_key
from main.config import Development, Production
import os, random, string, requests


API_URL = os.environ.get("API_URL") if "API_URL" in os.environ else 'http://localhost:5001'


def get_locale():
    AuthKey = request.cookies.get("Authorization")
    headers = {"Authorization": AuthKey}
    r = requests.get(API_URL+"/user", headers=headers)
    
    if r.status_code == 200:
        user = r.json()['user']
        locale = user['locale']
        if locale in app.config['BABEL_SUPPORTED_LOCALES']:
            return locale
            
    
    lang = request.cookies.get('locale')
    if lang in app.config['BABEL_SUPPORTED_LOCALES']:
        return lang
    return request.accept_languages.best_match(app.config['BABEL_SUPPORTED_LOCALES'])

def create_app():
    dotenv_file = find_dotenv()
    if not os.path.exists(dotenv_file): # Create a `.env` file if it's not found
        open(".env", 'a').close()
    dotenv_file = find_dotenv()
    load_dotenv(dotenv_path=dotenv_file)
    
    if "FLASK_SECRET_KEY" not in os.environ: # Set the flask secret key to a random 32 character string if it's not found
        os.environ["FLASK_SECRET_KEY"] = ''.join(random.choices(string.ascii_letters + string.digits + string.punctuation, k=32))
        set_key(dotenv_file, "FLASK_SECRET_KEY", os.environ["FLASK_SECRET_KEY"])
        
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ['FLASK_SECRET_KEY']
    app.config.from_object(Development) # Sets the current mode between Development and Production

    babel = Babel(app, locale_selector=get_locale)
    babel_js = BabelJS(app)

    return app


app = create_app()