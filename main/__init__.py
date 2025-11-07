from flask import Flask
from dotenv import load_dotenv, find_dotenv, set_key
from main.config import Development, Production
import os, random, string

API_URL = "http://localhost:5001"


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
    app.config.from_object(Development) # Sets the current mode between Development and Production
    # app.config['SECRET_KEY'] = os.environ["FLASK_SECRET_KEY"]
    # db.init_app(app)

    return app


app = create_app()