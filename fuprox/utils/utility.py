from fuprox.models import Customer, CustomerSchema
from flask import jsonify
user_schema = CustomerSchema()


# check if the user exists
def user_exists(email):
    data = Customer.query.filter_by(email=email).first()
    result = user_schema.dump(data)
    return jsonify(result)


def generate_ticket_number(code,branch,service):
    # check the branch_id
    # check the service_branch
    pass


def get_inst_id():
    pass



def create_service(name,teller,expires,date_expires,active,code):
    # get_inst_id
    # get (name,teller(s),expires,date_expires,active,code)
    # get added to (equity_unicity_service_INST_ID)
    pass
# on app connect _ verify with backend
# get inst_id {localstorage}


def make_booking():
    # get service
    # get last_ticket
    # get_code
    # online:bool background
    # make booking : offline(branch_id,service_id)
    # make booking : online([user_id],start,branch_id,service_id)
    '''
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.String(length=100))
    user_id = db.Column(db.Integer)
    start = db.Column(db.String(length=200))
    ticket = db.Column(db.String(length=6),nullable=False)
    branch = db.Column(db.Integer)
    institution = db.Column(db.Integer)
    :return:
    '''
    pass


'''

main backend : branch table will have an INST_ID column


equity_unicity_service_INST_ID
id : Int
service_name : String 
teller : Array
date_added : Datetime
expires : Boolean
date_expires : Datetime
active : Boolean


equity_unicity_bookings_INST_IT 

'''
