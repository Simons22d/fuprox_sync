from flask import Flask
from flask_marshmallow import Marshmallow
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import (JWTManager)
from flask_cors import CORS
import os
from dotenv import load_dotenv
from flask_migrate import Migrate

load_dotenv()

db_pass = os.getenv("DBPASS")
db_user = os.getenv("DBUSER")


app = Flask(__name__)

# init cors
CORS(app)

# adding JWT to the app
jwt = JWTManager(app)


app.config['SQLALCHEMY_POOL_RECYCLE'] = 10
app.config['SQLALCHEMY_NATIVE_UNICODE'] = 20
app.config['SQLALCHEMY_MAX_OVERFLOW'] = 1000
app.config['SQLALCHEMY_POOL_SIZE'] = 1000
app.config["SQLALCHEMY_POOL_TIMEOUT"] = 5
app.config['MAX_CONTENT_LENGTH'] = 2048 * 1024 * 1024

# basedir  = os.path.abspath(os.path.dirname(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = f"mysql+mysqlconnector://{db_user}:{db_pass}@localhost:3306/fuprox"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


# app bindings
bcrypt = Bcrypt(app)
db = SQLAlchemy(app)
ma = Marshmallow(app)
m = Migrate(app,db)

from fuprox.models.models import *
from fuprox.routes.routes import *



