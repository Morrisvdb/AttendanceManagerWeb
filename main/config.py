class Config:
    BABEL_DEFAULT_LOCALE = 'en'
    BABEL_SUPPORTED_LOCALES = ['en', 'nl']

class Development(Config):
    DEBUG = True # Enable the debugger
    
class Production(Config):
    DEBUG = False 
    TESTING = False
