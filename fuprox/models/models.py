from fuprox import db, ma
from datetime import datetime
import random
from fuprox.utils.utilities import ticket_unique


class ServiceOffered(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.ForeignKey("branch.id"), nullable=False)
    name = db.Column(db.String(length=250), unique=True)
    teller = db.Column(db.String(100), nullable=True)
    date_added = db.Column(db.DateTime, default=datetime.now)
    code = db.Column(db.String(length=10), nullable=False)
    icon = db.Column(db.String(length=20))
    is_synced = db.Column(db.Boolean, default=False)
    unique_id = db.Column(db.String(255), default=ticket_unique, unique=True)

    def __init__(self, name, branch_id, teller, code, icon):
        self.name = name
        self.branch_id = branch_id
        self.teller = teller
        self.code = code
        self.icon = icon


class ServiceOfferedSchema(ma.Schema):
    class Meta:
        fields = ("id", "branch_id", "name", "teller", "date_added", "code", "icon", "unique_id")


class BookingTimes(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, nullable=False, unique=True)
    date_added = db.Column(db.DateTime, default=datetime.now())
    service = db.Column(db.ForeignKey("service_offered.unique_id"), nullable=False)
    start = db.Column(db.DateTime, default=datetime.now)
    end = db.Column(db.DateTime, default=None)
    is_synced = db.Column(db.Boolean, default=False)

    def __init__(self, booking_id, service):
        self.booking_id = booking_id
        self.service = service


class BookingTimesSchema(ma.Schema):
    class Meta:
        fields = ("id", "booking_id", "start", "end", "service", "date_added")


# creating a booking ID
class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    service_name = db.Column(db.String(length=250), nullable=True)
    start = db.Column(db.String(length=200))
    branch_id = db.Column(db.Integer)
    ticket = db.Column(db.String(length=6), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.now, unique=True)
    active = db.Column(db.Boolean, default=False, nullable=False)
    nxt = db.Column(db.Integer, nullable=False, default=1001)
    serviced = db.Column(db.Boolean, nullable=False, default=False)
    teller = db.Column(db.String(200), nullable=False, default=000000)
    kind = db.Column(db.Integer, nullable=False)
    user = db.Column(db.Integer)
    is_instant = db.Column(db.Boolean, default=False)
    forwarded = db.Column(db.Boolean, default=False)
    is_synced = db.Column(db.Boolean, default=False)
    unique_id = db.Column(db.String(255), default=ticket_unique, unique=True)

    def __init__(self, service_name, start, branch_id, ticket, active, nxt, serviced, teller, kind, user,
                 instant, fowarded):
        self.service_name = service_name
        self.start = start
        self.branch_id = branch_id
        self.ticket = ticket
        self.active = active
        self.nxt = nxt
        self.serviced = serviced
        self.teller = teller
        self.kind = kind
        self.user = user
        self.is_instant = instant
        self.forwarded = fowarded
        self.nxt = 1001


class BookingSchema(ma.Schema):
    class Meta:
        fields = ("id", "service_name", "start", "branch_id", "ticket", "active", "nxt", "serviced", "teller", \
                 "kind", "user", "is_instant", "forwarded", "is_synced", "unique_id")


# user DB model
class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(48), unique=True, nullable=False)
    phoneNumber = db.Column(db.String(12), unique=True, nullable=False)
    image_file = db.Column(db.String(200), nullable=False, default="default.jpg")
    password = db.Column(db.String(200), nullable=False)

    def __repr__(self):
        return f"User (' {self.id} '{self.email}' )"

    def __init__(self, email, phone, password):
        self.email = email
        self.phoneNumber = phone
        self.password = password


class CustomerSchema(ma.Schema):
    class Meta:
        fields = ("id", "email", "phoneNumber", "image_file", "password")


# creating a company class
class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(length=50), unique=True)
    service = db.Column(db.String(length=250))

    def __init__(self, name, service):
        self.name = name
        self.service = service

    def __repr__(self):
        return f"Company {self.name} -> {self.service}"


class CompanySchema(ma.Schema):
    class Meta:
        fields = ("id", "name", "service")


# creating a branch class
class Branch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(length=250), unique=True)
    company = db.Column(db.String(length=100), db.ForeignKey("company.name"), nullable=False)
    longitude = db.Column(db.String(length=50))
    latitude = db.Column(db.String(length=50))
    opens = db.Column(db.String(length=50))
    closes = db.Column(db.String(length=50))
    service = db.Column(db.String(length=100), db.ForeignKey("service.name"))
    description = db.Column(db.String(length=50))
    key_ = db.Column(db.Text)
    valid_till = db.Column(db.DateTime)

    def __init__(self, name, company, longitude, latitude, opens, closes, service, description, key_):
        self.name = name
        self.company = company
        self.longitude = longitude
        self.latitude = latitude
        self.opens = opens
        self.closes = closes
        self.service = service
        self.description = description
        self.key_ = key_


# creating branch Schema
class BranchSchema(ma.Schema):
    class Meta:
        fields = (
            'id', 'name', 'company', 'address', 'longitude', 'latitude', 'opens', 'closes', 'service', 'description',
            "key_", "valid_till")


class Help(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    topic = db.Column(db.String(length=100), nullable=False)
    title = db.Column(db.String(length=250), nullable=False)
    solution = db.Column(db.Text, nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.now, nullable=False)
    is_synced = db.Column(db.Boolean, default=False)

    def __init__(self, topic, title, solution):
        self.topic = topic
        self.title = title
        self.solution = solution


class HelpSchema(ma.Schema):
    class Meta:
        fields = ("id", "topic", "title", "solution", "date_added")


class Teller(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.now)
    branch = db.Column(db.Integer)
    service = db.Column(db.String(200))
    unique_id = db.Column(db.String(255), default=ticket_unique, unique=True)
    is_synced = db.Column(db.Boolean, default=False)

    def __init__(self, number, branch, service):
        self.number = number
        self.branch = branch
        self.service = service


class TellerSchema(ma.Schema):
    class Meta:
        fields = ("id", "number", "date_added", "branch", "service", "is_synced", "unique_id")


"""
>>>> MPESA PAYMENTS >>
"""


class Mpesa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=True)
    receipt_number = db.Column(db.String(255), nullable=True)
    transaction_date = db.Column(db.String(255), nullable=True)
    phone_number = db.Column(db.String(255), nullable=True)
    checkout_request_id = db.Column(db.String(255), nullable=True)
    merchant_request_id = db.Column(db.String(255), nullable=True)
    result_code = db.Column(db.Integer, nullable=False)
    result_desc = db.Column(db.Text, nullable=True)
    date_added = db.Column(db.DateTime(), default=datetime.now)
    local_transactional_key = db.Column(db.String(255), nullable=False)
    is_synced = db.Column(db.Boolean, default=False)

    def __init__(self, MerchantRequestID, CheckoutRequestID, ResultCode, ResultDesc):
        self.merchant_request_id = MerchantRequestID
        self.checkout_request_id = CheckoutRequestID
        self.result_code = ResultCode
        self.result_desc = ResultDesc


class MpesaSchema(ma.Schema):
    class Meta:
        fields = ("id", "amount", "receipt_number", "transaction_data", "phone_number", "checkout_request_id",
                  "merchant_request_id", "result_code", "result_desc", "date_added", "local_transactional_key")


class Payments(db.Model):
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    body = db.Column(db.Text, nullable=False)
    token = db.Column(db.String(length=255))
    is_synced = db.Column(db.Boolean, default=False)

    def __init__(self, body, token):
        self.body = body
        self.token = token


class PaymentSchema(ma.Schema):
    class Meta:
        fields = ("id", "body", "token")


class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(length=50), unique=True)
    service = db.Column(db.String(length=250))
    is_medical = db.Column(db.Boolean, default=False)
    is_synced = db.Column(db.Boolean, default=False)

    def __init__(self, name, service, is_medical):
        self.name = name
        self.service = service
        self.is_medical = is_medical


class ServiceSchema(ma.Schema):
    class Meta:
        fields = ("id", "name", "service", "is_medical")


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(12), unique=True, nullable=False)
    email = db.Column(db.String(48), unique=True, nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default="default.jpg")
    password = db.Column(db.String(60), nullable=False)
    is_synced = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"User (' {self.id} ',' {self.username} ', '{self.email}', '{self.image_file}' )"

    def __init__(self, username, email, password):
        self.username = username
        self.email = email
        self.password = password


class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(length=250), unique=True)
    active = db.Column(db.Integer, default=0)
    type = db.Column(db.Integer, default=0)
    is_synced = db.Column(db.Boolean, default=False)

    def __init__(self, name, type):
        self.name = name
        self.type = type


class VideoSchema(ma.Schema):
    class Meta:
        fields = ("id", "name", "active", "type")


class Recovery(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.ForeignKey("customer.id"), nullable=False)
    code = db.Column(db.String(length=50), nullable=False)
    used = db.Column(db.Boolean, nullable=False, default=False)
    is_synced = db.Column(db.Boolean, default=False)

    def __init__(self, user, code):
        self.user = user
        self.code = code


class RecoverySchema(ma.Schema):
    class Meta:
        fields = ("id", "user", "code")


class ImageCompany(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company = db.Column(db.ForeignKey("company.id"), nullable=False)
    image = db.Column(db.String(length=250), nullable=False)
    is_synced = db.Column(db.Boolean, default=False)

    def __init__(self, company, image):
        self.company = company
        self.image = image


class ImageCompanySchema(ma.Schema):
    class Meta:
        fields = ("id", "company", "image")


class Utils:

    @staticmethod
    def random_numbers():
        return random.getrandbits(24)


class AccountStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.ForeignKey("customer.id"), nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=False)
    code = db.Column(db.String(10), nullable=False, default=Utils.random_numbers)
    is_synced = db.Column(db.Boolean, default=False)

    def __init__(self, user):
        self.user = user


class AccountStatusSchema(ma.Schema):
    class Meta:
        fields = ("id", "user", "active", "code")
