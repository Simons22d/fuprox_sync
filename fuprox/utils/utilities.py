from fuprox.models import Customer,CustomerSchema
from fuprox import bcrypt
import secrets
from flask import jsonify

user_schema = CustomerSchema()
users_exist = CustomerSchema(many=True)


# check if the user exists
def user_exists(email,password):
    data = Customer.query.filter_by(email=email).first()
    print(data)
    # checking for the password
    if data:
        if bcrypt.check_password_hash(data.password,password):
            token = secrets.token_hex(48)
            result = {
                "user_data"  : user_schema.dump(data),
                "token" : token
            }
    else :
        result = {
            "user": None,
            "msg": "Bad Username/Password combination"
        }
    return jsonify(result)
