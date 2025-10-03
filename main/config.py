class Development:
    DEBUG = True # Enable the debugger
    SQLALCHEMY_DATABASE_URI = "sqlite:///testing_database.db"
    
class Production:
    DEBUG = False 
    TESTING = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///database.db"