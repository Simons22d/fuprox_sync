from logging import exception
import eventlet.wsgi
from flask import request, jsonify, send_from_directory
from fuprox import db, app
from fuprox.models.models import (Branch, BranchSchema, Service, ServiceSchema, Company, CompanySchema, Help,
                                  HelpSchema, ServiceOffered, ServiceOfferedSchema, Booking, BookingSchema,
                                  TellerSchema, Teller, Payments, PaymentSchema, Mpesa, MpesaSchema, Recovery,
                                  RecoverySchema, ImageCompanySchema, ImageCompany, AccountStatus, AccountStatusSchema,
                                  Customer, CustomerSchema)
from fuprox.utils.payments import authenticate, stk_push
import secrets

# from fuprox.utilities import user_exists
from fuprox import bcrypt
from sqlalchemy import desc
import logging
import sqlalchemy
import socketio
import requests
import time
from datetime import datetime, timedelta
import json
import re
import smtplib, ssl
import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fuprox.utils.email import body, password_changed, code_body
import random, requests
from pathlib import Path
import os
import subprocess

link = "http://localhost:4000"
link_icon = "159.65.144.235"
# online socket link
# socket_link = "http://159.65.144.235:5000/"

#  offline socket link
socket_link = "http://localhost:5000/"
# standard Python
sio = socketio.Client()

# from fuprox.utilities import user_exists

# adding some product schemas
user_schema = CustomerSchema()
users_schema = CustomerSchema(many=True)

company_icon = ImageCompanySchema()
companies_icon = ImageCompanySchema(many=True)

service_ = ServiceSchema()
service_s = ServiceSchema(many=True)

# branch schema
branch_schema = BranchSchema()
branches_schema = BranchSchema(many=True)

# service offered schema
service_offered_schema = ServiceOfferedSchema()
services_offered_schema = ServiceOfferedSchema(many=True)

# service schema
service_schema = ServiceSchema()
services_schema = ServiceSchema(many=True)

booking_schema = BookingSchema()
bookings_schema = BookingSchema(many=True)

# getting companiy schema
company_schema = CompanySchema()
companies_schema = CompanySchema(many=True)

# help
help_schema = HelpSchema()
helps_schema = HelpSchema(many=True)

# service Offered
service_offer_schema = ServiceOfferedSchema()
service_offers_schema = ServiceOfferedSchema(many=True)

# teller schema
teller_schema = TellerSchema()
tellers_schema = TellerSchema(many=True)

# payment  schema
payment_schema = PaymentSchema()
payments_schema = PaymentSchema(many=True)

# mpesa_schema
mpesa_schema = MpesaSchema()
mpesas_schema = MpesaSchema(many=True)

# recovery_schema
recovery_schema = RecoverySchema()
recoverys_schema = RecoverySchema(many=True)

# account schema
account_schema = AccountStatusSchema()
accounts_schema = AccountStatusSchema(many=True)


def get_icon_by_company(company_name):
    company = Company.query.filter_by(name=company_name).first()
    if company:
        lookup = ImageCompany.query.filter_by(company=company.id).first()
    else:
        lookup = dict()
    return lookup


def get_icon_by_id(id):
    company = Company.query.get(id)
    lookup = ImageCompany.query.filter_by(company=company.id).first()
    return lookup


def add_user_account(user):
    try:
        lookup = AccountStatus(user)
        db.session.add(lookup)
        db.session.commit()
        # get user data
        lookup = AccountStatus.query.filter_by(user=user).first()
        return account_schema.dump(lookup)
    except sqlalchemy.exc.IntegrityError:
        lookup = AccountStatus.query.filter_by(user=user).first()
        return account_schema.dump(lookup)


def activate_account(usr):
    user = Customer.query.filter_by(email=usr).first()
    if user:
        lookup = AccountStatus.query.filter_by(user=user.id).first()
        if lookup:
            l = AccountStatus.query.filter_by(user=user.id).first()
            l.active = True
            db.session.commit()
            return account_schema.dump(lookup)
        else:
            return None
    else:
        return None


def user_is_active(usr):
    user = Customer.query.filter_by(email=usr).first()
    if user:
        lookup = AccountStatus.query.filter_by(user=user.id).first()
        if lookup:
            if bool(lookup.active):
                return True
            else:
                return False
        else:
            return False
    else:
        return False


# :::::::::::::::: Routes for graphs for the fuprox_no_queu_backend ::::
@app.route("/graph/data/doughnut", methods=["POST"])
def graph_data():
    # get all booking sorting by
    serviced_lookup = Booking.query.with_entities(Booking.date_added).filter_by(serviced=True).all()
    serviced_data = bookings_schema.dump(serviced_lookup)

    unserviced_lookup = Booking.query.with_entities(Booking.date_added).filter_by(serviced=False).all()
    unserviced_data = bookings_schema.dump(unserviced_lookup)
    print(unserviced_data)

    final = {
        "serviced": len(serviced_data),
        "unserviced": len(unserviced_data)
    }
    return final


@app.route('/graph/data/timeline', methods=["POST"])
def timeline():
    now = datetime.now()
    offset = timedelta.days(-15)
    # the offset for new date
    limit_date = (now + offset)
    date_lookup = Booking.query("date_added") \
        .filter(Booking.date_added.between(limit_date, now)).all()
    #  sort data using pandas
    date_data = bookings_schema.dump(date_lookup)
    return date_data




'''
reset ticket counter
'''


@app.route("/reset/ticket/counter", methods=["POST"])
def reset_ticket():
    lookup = Booking.query.all()
    for booking in lookup:
        booking.nxt = 4004
        db.session.commit()
    #  here we are going to filter all tickets with the status [nxt == 4004]
    reset_data = get_all_bookings_no_branch()
    if reset_data:
        # there was some data reset
        final = loop_data_check_reset_tickets(reset_data)
    else:
        # No data to reset
        final = list()
    return jsonify(final)


def get_all_bookings_no_branch():
    data = Booking.query.filter_by(nxt=1001).all()
    return bookings_schema.dump(data)


def loop_data_check_reset_tickets(data):
    ticket_reset = list()
    for item in data:
        if item.nxt == 4004:
            ticket_reset.append(item)
    return ticket_reset


def save_code(user, code):
    lookup = Recovery(user, code)
    db.session.add(lookup)
    db.session.commit()
    return recovery_schema.dump(lookup)


def random_four():
    rand = random.getrandbits(30)
    numbers = str(rand)
    final = [numbers[i:i + 4] for i in range(0, len(numbers), 4)]
    final = f"{final[0]}-{final[1]}"
    return final


def email_exists(email):
    lookup = Customer.query.filter_by(email=email).first()
    return user_schema.dump(lookup)


def send_email(_to, subject, body):
    _from = "admin@fuprox.com"
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = _from
    message["To"] = _to

    # Turn these into plain/html MIMEText objects
    part = MIMEText(body, "html")
    # Add HTML/plain-text parts to MIMEMultipart message
    message.attach(part)
    # Create secure connection with server and send email
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("mail.fuprox.com", 465, context=context) as server:
        server.login(_from, "Japanitoes")
        if server.sendmail(_from, _to, message.as_string()):
            return True
        else:
            return False


def validate_email(email):
    regex = re.compile(r'^(([^<>()\[\]\\.,;:\s@"]+(\.[^<>()\[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,'
                       r'3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$')
    return re.match(regex, email)


@app.route("/user/logout")
def user_logout():
    # remove the user token from the database
    token = request.json["token"]
    # remove token from db
    pass


@app.route("/branch/get")
def get_all_branches():
    branches = Branch.query.all()
    # loop over the
    res = branches_schema.dump(branches)
    lst = list()
    # here we are going to make a teller request to the socket
    # sio.emit("teller",{"branch_id":res})
    for item in res:
        final = bool()

        if branch_is_medical(item["id"]):
            final = True
        else:
            final = False

        item["is_medical"] = final
        icon = get_icon_by_company(item["company"])
        if icon:
            item["icon"] = f"http://{link_icon}:4000/icon/{icon.image}"
        else:
            item["icon"] = f"http://{link_icon}:4000/icon/default.png"
        lst.append(item)

    return jsonify({"branches": lst})


@app.route('/icon/<string:icon>', methods=["GET"])
def get_icon(icon):
    home = str(Path.home())
    icon_path = os.path.join(home, "fuprox_api", "icons")
    return send_from_directory("icons", filename=icon)


@app.route("/branch/get/single", methods=["GET", "POST"])
def get_user_branches():
    branch_id = request.json["branch_id"]
    branch_data = branch_get_single(branch_id)
    if branch_data:
        # if branch_data["status"] :
        #     branch_data.update({"icon": f"http://{link_icon}:4000/icon/default.png"})
        # else :
        print("here")
        print(branch_data)
        data = get_icon_by_company(branch_data["company"])
        try:
            branch_data.update({"icon": f"http://{link_icon}:4000/icon/{data['image']}"})
        except KeyError:
            branch_data.update({"icon": f"http://{link_icon}:4000/icon/default.png"})

    else:
        branch_data
    return jsonify(branch_data)


def branch_get_single(branch_id):
    # make a database selection
    data = Branch.query.filter_by(id=branch_id).first()
    res = branch_schema.dump(data)
    if res:
        final = bool()
        company_ = ""
        # get company_data
        if data:
            company = get_company_by_branch(res["company"])
            if company:
                company_ = company["id"]
        if res:
            if branch_is_medical(res["id"]):
                final = True
            else:
                final = False
        res["is_medical"] = final
        res["company"] = company_
    else:
        res = {}
    return res


def get_company_by_branch(branch_name):
    lookup = Company.query.filter_by(name=branch_name).first()
    company_data = company_schema.dump(lookup)
    return company_data


@app.route("/services/get/all", methods=["POST"])
def service_offered():
    branch_id = request.json["branch_id"]
    lookup = ServiceOffered.query.filter_by(branch_id=branch_id).all()
    final = service_offers_schema.dump(lookup)
    return jsonify(final)


@app.route("/ahead/of/you", methods=["POST"])
def ahead_of_you():
    service_name = request.json["service_name"]
    branch_id = request.json["branch_id"]

    branch = Branch.query.get(int(branch_id))

    lookup = Booking.query.filter_by(service_name=service_name).filter_by(nxt=1001).filter_by(
        branch_id=branch_id).filter_by(serviced=False).filter_by(forwarded=False).all()

    forwarded = Booking.query.filter_by(branch_id=branch.id).filter_by(
        forwarded=True).filter_by(service_name=service_name).filter_by(serviced=False).all()

    final = len(lookup) + len(forwarded)

    return jsonify({"infront": final})


@app.route("/ahead/of/you/id", methods=["POST"])
def ahead_of_you_id_():
    branch_id = request.json["booking_id"]
    return jsonify(ahead_of_you_id(branch_id))


"""Not to delete"""


@app.route("/sycn/online/booking", methods=["POST"])
def sync_bookings():
    service_name = request.json["service_name"]
    start = request.json["start"]
    branch_id = request.json["branch_id"]
    is_instant = request.json["is_instant"]
    user = request.json["user"]
    ticket = request.json["ticket"]
    key_ = request.json["key_"]
    unique_id = request.json["unique_id"]
    is_synced = True if int(user) == 0 else False
    serviced = request.json['serviced']
    forwarded = request.json["forwarded"]
    unique_teller = request.json["unique_teller"]

    if not booking_exists_by_unique_id(unique_id):
        final = dict()
        try:
            try:
                final = create_booking_online_(service_name, start, branch_id, is_instant, user, kind=ticket,
                                               key=key_, unique_id=unique_id, is_synced=is_synced, serviced=serviced,
                                               forwarded=forwarded, unique_teller=forwarded)
            except ValueError as err:
                log(err)
        except sqlalchemy.exc.IntegrityError:
            log("Error! Could not create booking.")
    else:
        log("Booking Does exist.")
        final = {"msg": "booking exists"}
        ack_successful_entity("BOOKING", {"unique_id": unique_id})
    return final


"""No to delete"""


@app.route("/sycn/offline/services", methods=["POST"])
def sync_services():
    name = request.json["name"]
    teller = request.json["teller"]
    branch_id = request.json["branch_id"]
    code = request.json["code"]
    icon_id = request.json["icon"]
    key = request.json["key"]
    unique_id = request.json["unique_id"]
    service = dict()
    try:
        key_data = get_online_by_key(key)
        if key_data:
            service = create_service(name, teller, key_data["id"], code, icon_id, unique_id)
        else:
            service = dict()
    except sqlalchemy.exc.IntegrityError:
        print("Error! Could not create service.")
    return service_schema.jsonify(service)


"""Not T0 Delete"""


@app.route('/sycn/offline/teller', methods=["POST"])
def sycn_teller():
    service = request.json["service"]
    branch = request.json["branch"]
    number_ = request.json["number"]
    unique_id = request.json["unique_id"]
    branch_unique_id = request.json["branch_unique_id"]
    teller_ = dict()
    try:
        teller_ = add_teller(number_, branch, service, unique_id, branch_unique_id)
    except sqlalchemy.exc.IntegrityError as e:
        print(e)
        print("Error! Teller could not be added Could not add the record.")
    return teller_


@app.route("/update/ticket", methods=["POST"])
def update_tickets_():
    # get branch by key
    key = request.json["key_"]
    service_name = request.json["service_name"]
    ticket = request.json["ticket"]
    branch_data = get_online_by_key(key)
    final = dict()
    if branch_data:
        # online booking
        booking_lookup = Booking.query.filter_by(service_name=service_name).filter_by(branch_id=branch_data["id"]). \
            filter_by(ticket=ticket).first()
        booking_data = booking_schema.dump(booking_lookup)
        if booking_data:
            # make this booking active
            booking_lookup.serviced = True
            db.session.commit()
            final = booking_schema.dump(booking_lookup)
        # if data is not saved save
        # ______!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        # TODO: add sync if does not exist
    return final


@app.route("/payments/user/status", methods=["POST"])
def payment_user_status():
    data = request.json["phone"]
    lookup = Payments(data)
    # we are going to work with new mpsay payments
    db.session.add(lookup)
    db.session.commit()
    return payment_schema.jsonify(lookup)


'''
reset ticket count
'''


@app.route("/ticket/reset", methods=["POST"])
def reset():
    code = {"code": random.getrandbits(100)}
    sio.emit("reset_tickets", code)
    return jsonify(code)


@app.route("/init/sync/online", methods=["POST"])
def init_sync():
    branch = request.json["key"]
    sio.emit("init_sync", {"key": branch})
    return dict()


# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# functions >>>>>>>>>>>>>>>>>>>>>>>>
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>


def get_online_by_key(key):
    lookup = Branch.query.filter_by(key_=key).first()
    lookup_data = branch_schema.dump(lookup)
    return lookup_data


def services_exist(services, branch_id):
    holder = services.split(",")
    for item in holder:
        if not service_exists(item, branch_id):
            return False
    return True


def add_teller(teller_number, branch_id, service_name, unique_id, branch_unique_id):
    # here we are going to ad teller details
    # two words service name
    if not teller_exists_unique(unique_id):
        if len(service_name.split(",")) > 1:
            # get teller by unique
            if get_teller(unique_id):
                final = {"msg": "Teller number exists"}, 500
                # log(f"teller exists - {unique_id}")
            else:
                lookup = Teller(teller_number, branch_id, service_name, branch_unique_id)
                lookup.unique_id = unique_id
                try:
                    db.session.add(lookup)
                    db.session.commit()
                    print("added")
                    ack_successful_entity("TELLER", teller_schema.dump(lookup))
                    log(f"teller synced + {unique_id}")
                except sqlalchemy.exc.IntegrityError:
                    ack_failed_entity("TELLER", {"unique_id": unique_id})
                    # log(f"teller exists - {unique_id}")
                    ack_successful_entity("TELLER", {"data": {"unique_id": unique_id}})

                final = teller_schema.dump(lookup)
        else:
            # get teller by unique
            if get_teller(unique_id):
                final = {"msg": "Teller number exists"}, 500
                log(f"teller exists - {unique_id}")
                ack_successful_entity("TELLER", {"unique_id": unique_id})
            else:
                lookup = Teller(teller_number, branch_id, service_name, branch_unique_id)
                lookup.unique_id = unique_id

                db.session.add(lookup)
                db.session.commit()
                final = teller_schema.dump(lookup)
                log(f"teller synced + {unique_id}")

    else:
        lookup = teller_exists_unique(unique_id)
        ack_successful_entity("TELLER", {"unique_id": unique_id})
        log("We should make teller synced")
        lookup.is_synced = True
        db.session.commit()
        final = dict()
    return final


"""
::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:::::sync offline booking | service >> online data for offline updating:::
::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
"""


def teller_exists_unique(unique_id):
    return Teller.query.filter_by(unique_id=unique_id).first()


def get_branch_by_key(key):
    lookup = Branch.query.filter_by(key_=key).first()
    return branch_schema.dump(lookup)


# new sync implementation
# get all data online to offline
def get_sync_all_data(key):
    # get all booking
    bookings_to_sync = get_all_unsyced_bookings()
    # return the data
    final = {"bookings": bookings_to_sync, "key": key}
    return final


def get_all_unsyced_bookings(branch_key):
    branch = get_branch_by_key(branch_key)
    online = Booking.query.filter_by(nxt=1001).filter_by(active=False).filter_by(branch_id=branch["id"]).filter_by(
        serviced=False).filter_by(is_synced=False).all()
    online_bookings = bookings_schema.dump(online)
    return online_bookings


@app.route("/bookings/to/sycn", methods=["POST"])
def test__():
    key = request.json["key"]
    data = sync_service(key)
    final = list()
    for record in data:
        final.append(record["unique_id"])
    return jsonify(data)


def sync_service(key):
    branch_data = get_branch_by_key(key)
    final = dict()
    if branch_data:
        # branch_data font the company
        final = get_all_unsyced_bookings(key)
    # emit event
    return final


# getting branch data
def sync_company_data():
    company_lookup = Company.query.all()
    company_data = companies_schema.dump(company_lookup)
    return company_data


def sycn_branch_data(key):
    # get all the branch`
    branch = get_branch_by_key(key)
    # get the company for the branch
    final = list()
    if branch:
        company = Company.query.filter_by(name=branch["company"]).first()
        company_data = company_schema.dump(company)
        if company_data:
            branches_lookup = Branch.query.filter_by(company=company_data["name"]).all()
            branches_data = branches_schema.dump(branches_lookup)
            final = branches_data
    # get all the branches for that company
    return final


# sycing off line services
def create_service(name, teller, branch_id, code, icon_id, unique_id=""):
    if branch_exist(branch_id):
        final = None
        if service_exists_by_unique_id(unique_id):
            final = {"msg": "Error service name already exists"}
            log(f"service exists - {unique_id}")
            ack_successful_entity("SERVICE", {"unique_id": unique_id})
        else:
            if get_service_code(code, branch_id):
                final = {"msg": "Error Code already exists"}
                log(f"service exists [code] - {unique_id} - {code}")
                ack_successful_entity("SERVICE", {"unique_id": unique_id})

            else:
                service = ServiceOffered(name, branch_id, teller, code, int(icon_id))
                service.unique_id = unique_id
                service.is_synced = True
                try:
                    db.session.add(service)
                    db.session.commit()
                    ack_successful_entity("SERVICE", service_schema.dump(service))
                    log(f"service synced + {unique_id}")
                except sqlalchemy.exc.IntegrityError as e:
                    ack_failed_entity("SERVICE", {"unique_id": unique_id})
                    log(f"service exists - {unique_id}")
                final = service_schema.dump(service)
    else:
        final = {"msg": "Service/Branch issue"}
    return final


def update_sync_all_data(data):
    bookings = data["bookings"]
    key = data["key"]
    if branch_exists_key(key):
        # we can sync
        for booking in bookings:
            # check if booking exists
            if not booking_exists_unique(booking):
                # booking does not exists
                # add booking to the db
                # flag the booking as synced now
                id = booking["id"]
                service_name = booking["service_name"]
                start = booking["start"]
                branch_id = booking["branch_id"]
                ticket = booking["ticket"]  # replaces kind
                active = booking["active"]
                nxt = booking["nxt"]
                serviced = booking["serviced"]
                teller = booking["teller"]
                kind = booking["kind"]
                user = booking["user"]
                is_instant = booking["is_instant"]
                forwarded = booking["forwarded"]
                is_synced = booking["is_synced"]
                unique_id = booking["unique_id"]
                # adding data to the database
                create_booking(service_name, start, branch_id, bool(is_instant), user, unique_id, is_synced)
            else:
                # booking exists
                flag_booking_as_synced(booking)
                ack_successful_entity("BOOKING", booking)
    else:
        print("branch data is not for this branch")
    return dict()


def booking_exists_unique(data):
    final = Booking.query.filter_by(unique_id=data["unique_id"]).first()
    return final


# def flag_booking_as_synced(data):
#     booking = booking_exists_unique(data)
#     booking.is_synced = True
#     return booking


def branch_exists_key(key):
    lookup = Branch.query.filter_by(key_=key).first()
    return lookup


# check if the user exists
def user_exists(email, password):
    data = Customer.query.filter_by(email=email).first()
    print("user_data", data)
    # checking for the password
    if data:
        if bcrypt.check_password_hash(data.password, password):
            token = secrets.token_hex(48)
            result = {"user_data": user_schema.dump(data), "token": token}
        else:
            result = {
                "user_data": {
                    "email": None,
                    "msg": "Bad Username/Password combination"
                }
            }
    else:
        result = {
            "user_data": {
                "email": None,
                "msg": "Bad Username/Password combination"
            }
        }
    return result


def is_user(user_id):
    lookup = Customer.query.get(user_id)
    user_data = user_schema.dump(lookup)
    return user_data


def get_teller(unique_id):
    lookup = Teller.query.filter_by(unique_id=unique_id).first()
    data = teller_schema.dump(lookup)
    return data


def ticket_queue(service_name, branch_id):
    lookup = Booking.query.filter_by(service_name=service_name).filter_by(nxt=1001).filter_by(
        branch_id=branch_id).order_by(
        desc(Booking.date_added)).first()
    booking_data = booking_schema.dump(lookup)
    return booking_data


def create_booking(service_name, start, branch_id, is_instant, user_id):
    if service_exists(service_name, branch_id):
        if is_user(user_id):
            final = ""
            # get the service
            data = service_exists(service_name, branch_id)
            name = data["name"]
            if ticket_queue(service_name, branch_id):
                # get last ticket is active next == True
                # get the last booking
                book = get_last_ticket(service_name, branch_id)
                # if is active we can creat a next
                is_active = book["active"]
                is_serviced = book["serviced"]
                # last booking next so this booking should just be a normal booking
                last_ticket_number = book["ticket"]
                next_ticket = int(last_ticket_number) + 1
                final = make_booking(name, start, branch_id, next_ticket, instant=is_instant, user=user_id)
            else:
                # we are making the first booking for this category
                # we are going to make this ticket  active
                next_ticket = 1
                final = make_booking(name, start, branch_id, next_ticket, active=True, instant=is_instant, user=user_id)
        else:
            print("user_does not exist")
            final = None
            logging.info("user does not exist")
    else:
        print("service does not exist")
        final = None
        logging.info("service does not exists")
    return final


def create_booking_online(service_name, start, branch_id, ticket, is_instant=False, user_id="", is_active=False):
    data = service_exists(service_name, branch_id)
    final = make_booking(service_name, start, branch_id, ticket, False, is_active, instant=is_instant, user=user_id)
    return final


def update_branch_offline(key):
    lookup = Branch.query.filter_by(key_=key).first()
    lookup_data = branch_schema.dump(lookup)
    return lookup_data


def create_booking_online_(service_name, start, branch_id_, is_instant=False, user=0, kind=0, key="", unique_id="",
                           is_synced="", serviced=False, forwarded=False, unique_teller=0):
    data_ = update_branch_offline(key)
    branch_id = data_["id"] if data_ else 1
    if branch_is_medical(branch_id):
        if service_exists(service_name, branch_id):
            # get the service
            data = service_exists(service_name, branch_id)
            name = data["name"]
            if ticket_queue(service_name, branch_id):
                book = ticket_queue(service_name, branch_id)
                last_ticket_number = book["ticket"]
                next_ticket = int(last_ticket_number) + 1
                log("before make booking call")
                final = make_booking(name, start, branch_id, next_ticket, instant=False, user=user, kind=kind,
                                     unique_id=unique_id, is_synced=is_synced, serviced=serviced, forwarded=forwarded,
                                     unique_teller=unique_teller)
            else:
                # we are making the first booking for this category
                # we are going to make this ticket  active
                next_ticket = 1
                final = make_booking(name, start, branch_id, next_ticket, active=False, instant=False, user=user,
                                     kind=kind, unique_id=unique_id, is_synced=is_synced, serviced=serviced,
                                     forwarded=forwarded, unique_teller=unique_teller)
        else:
            raise ValueError("Service Does Not Exist. Please Add Service First.")
            final = True
    else:
        if service_exists(service_name, branch_id):
            # get the service
            data = service_exists(service_name, branch_id)
            name = data["name"]
            if ticket_queue(service_name, branch_id):
                book = ticket_queue(service_name, branch_id)
                last_ticket_number = book["ticket"]
                next_ticket = int(last_ticket_number) + 1
                log(f"before make booking call-> booking status {serviced}")
                final = make_booking(name, start, branch_id, next_ticket, instant=is_instant, user=user, kind=kind,
                                     unique_id=unique_id, is_synced=is_synced, serviced=serviced, forwarded=forwarded,
                                     unique_teller=unique_teller)
            else:
                # we are making the first booking for this category
                # we are going to make this ticket  active
                next_ticket = 1
                log(f"before make booking call-> booking status {serviced}")
                final = make_booking(name, start, branch_id, next_ticket, active=False, instant=is_instant, user=user,
                                     kind=kind, unique_id=unique_id, is_synced=is_synced, serviced=serviced,
                                     forwarded=forwarded, unique_teller=unique_teller)
        else:
            raise ValueError("Service Does Not Exist. Please Add Service First.")
            final = True

    # print("the final output of the fuction >>>>", final)
    time.sleep(5)
    return final


# requests.exceptions.ConnectionError: HTTPConnectionPool

def make_booking(service_name, start="", branch_id=1, ticket=1, active=False, upcoming=False, serviced=False,
                 teller=000, kind="1", user=0000, instant=False, unique_id="", is_synced="", forwarded=False,
                 unique_teller=0):
    final = list()
    branch_data = branch_exist(branch_id)
    if branch_is_medical(branch_id):
        log("This is a medical branch")
        lookup = Booking(service_name, start, branch_id, ticket, active, upcoming, serviced, teller, kind, user, False,
                         forwarded)
        if unique_id:
            lookup.unique_id = unique_id
        if is_synced:
            lookup.is_synced = True
        if serviced:
            lookup.serviced = True
        if forwarded:
            lookup.forwarded = True
        if unique_teller:
            lookup.unique_teller = unique_teller

        db.session.add(lookup)
        db.session.commit()
        final = booking_schema.dump(lookup)
        if final:
            ack_successful_entity("BOOKING", final)
            log(f"service synced + {unique_id}")
        else:
            ack_failed_entity("BOOKING", {"unique_id": unique_id})
            log(f"Error Booking + {unique_id}")
        final.update({"key": branch_data["key_"]})

    else:
        lookup = Booking(service_name, start, branch_id, ticket, active, upcoming, serviced, teller, kind, user,
                         instant, fowarded=False)
        if unique_id:
            lookup.unique_id = unique_id

        if is_synced:
            lookup.is_synced = True

        if serviced:
            lookup.serviced = True
        log(f"some details ....> {serviced, unique_id, is_synced}")
        db.session.add(lookup)
        db.session.commit()
        final = booking_schema.dump(lookup)
        if final:
            ack_successful_entity("BOOKING", final)
            log(f"service synced + {unique_id}")
        else:
            ack_failed_entity("BOOKING", {"unique_id": unique_id})
            log(f"Error Booking + {unique_id}")

        final.update({"key": branch_data["key_"]})
    return final


def ack_successful_entity(name, data):
    sio.emit("ack_successful_enitity", {"category": name, "data": data})
    return data


def ack_failed_entity(name, data):
    sio.emit("ack_failed_enitity", {"category": name, "data": data})
    return data


def service_exists(name, branch_id):
    lookup = ServiceOffered.query.filter_by(name=name).filter_by(branch_id=branch_id).first()
    data = service_offered_schema.dump(lookup)
    return data


def service_exists_by_unique_id(unique_id):
    lookup = ServiceOffered.query.filter_by(unique_id=unique_id).first()
    data = service_offered_schema.dump(lookup)
    return data


def get_last_ticket(service_name, branch_id):
    """ Also check last online ticket """
    # here we are going to get the last ticket offline then make anew one base on that's
    # emit("last_ticket",{"branch_id":branch_id,"service_name": service_name})

    lookup = Booking.query.filter_by(service_name=service_name).filter_by(nxt=1001).order_by(
        desc(Booking.date_added)).first()
    booking_data = booking_schema.dump(lookup)
    return booking_data


def branch_exist(branch_id):
    lookup = Branch.query.get(branch_id)
    branch_data = branch_schema.dump(lookup)
    return branch_data


# assume we are making a booking
def generate_ticket(booking_id):
    # get_ticket code
    booking = get_booking(booking_id)
    if booking:
        branch = branch_exist(booking['branch_id'])
        service = service_exists(booking["service_name"], booking["branch_id"])
        if branch and service:
            code = service["code"] + booking["ticket"]
            branch_name = branch["name"]
            company = branch["company"]
            service_name = service["name"]
            date_added = booking["start"]
            booking_id = booking["id"]
            final = {"booking_id": booking_id, "code": code, "branch": branch_name, "company": company,
                     "service": service_name, "date": date_added}
        else:
            final = {"msg": "Details not Found"}
    else:
        final = {"msg": "Booking not Found"}
    return final


def get_booking(booking_id):
    lookup = Booking.query.get(booking_id)
    data = booking_schema.dump(lookup)
    return data


def get_user_bookings(user_id):
    lookup = Booking.query.filter_by(user=user_id).all()
    data = bookings_schema.dump(lookup)
    return data


def user_id_exists(user_id):
    lookup = Customer.query.get(user_id)
    data = user_schema.dump(lookup)
    return data


def branch_is_medical(branch_id):
    branch_lookup = Branch.query.get(branch_id)
    branch_data = branch_schema.dump(branch_lookup)
    if branch_data:
        lookup = Service.query.filter_by(name=branch_data["service"]).first()
        service_data = service_.dump(lookup)
        if service_data["is_medical"]:
            service_data = True
        else:
            service_data = False
    else:
        service_data = None
    return service_data


def ahead_of_you_id(id):
    booking_id = request.json["booking_id"]
    lookup = Booking.query.get(booking_id)
    lookup_data = booking_schema.dump(lookup)
    if lookup_data:
        booking_lookup_two = Booking.query.filter_by(service_name=lookup_data["service_name"]). \
            filter_by(branch_id=lookup_data["branch_id"]).filter_by(nxt=1001).filter_by(serviced=False). \
            filter(Booking.date_added > lookup_data["start"]).all()
        final_booking_data = bookings_schema.dump(booking_lookup_two)

        # fowarded
        forwarded = Booking.query.filter_by(branch_id=lookup.branch_id).filter(Booking.unique_teller.isnot(
            0)).filter_by(forwarded=True).filter_by(service_name=lookup_data["service_name"]).filter_by(
            serviced=False).all()

        # forwarded = Booking.query.filter_by(branch_id=lookup.branch_id).filter(Booking.unique_teller.isnot(
        #     0)).filter_by(forwarded=True).filter_by(service_name=lookup.service_name).filter_by(
        #     serviced=False).all()

        final = {"msg": len(final_booking_data) + len(forwarded)}
    else:
        final = {"msg": None}

    return final


def booking_exists(branch, service, tckt):
    lookup = Booking.query.filter_by(branch_id=branch).filter_by(service_name=service).filter_by(ticket=tckt).first()
    data = booking_schema.dump(lookup)
    return data


def booking_exists_by_unique_id(unique_id):
    return Booking.query.filter_by(unique_id=unique_id).first()


@app.route("/booking/test", methods=["POST"])
def bkg_test():
    id = request.json["id"]
    return jsonify(booking_schema.dump(booking_exists_by_unique_id(id)))


def get_service_code(code, branch_id):
    lookup = ServiceOffered.query.filter_by(name=code).filter_by(branch_id=branch_id).first()
    data = service_schema.dump(lookup)
    return data


def log(msg):
    print(f"{datetime.now().strftime('%d:%m:%Y %H:%M:%S')} — {msg}")
    return True


'''here we are going to reset tickets every midnight'''


@sio.event
def connect():
    print('connection established')


@sio.event
def teller(data):
    sio.emit('teller', {'response': 'my response'})


@sio.event
def disconnect():
    print('disconnected from server')


@sio.on('online_data_')
def online_data(data):
    try:
        data = data["booking_data"]
        requests.post(f"{link}/sycn/online/booking", json=data)
        time.sleep(1)
    except requests.exceptions.ConnectionError:
        # we are going to call script to restart this script
        pass


@sio.on('sync_service_')
def sync_service_(data):
    try:
        requests.post(f"{link}/sycn/offline/services", json=data)
        time.sleep(1)
    except requests.exceptions.ConnectionError:
        # we are going to call script to restart this script
        # subprocess.run("systemctl")
        pass


@sio.on("update_ticket_data")
def update_ticket_data(data):
    requests.post(f"{link}/update/ticket", json=data)


def booking_is_serviced(unique_id):
    book = Booking.query.filter_by(unique_id=unique_id).first()
    return book.serviced


def booking_is_forwarded(unique_id):
    book = Booking.query.filter_by(unique_id=unique_id).first()
    return book.forwarded and book.unique_teller


def update_booking_by_unique_id(bookings):
    for booking in bookings:
        unique_id = booking["unique_id"]
        status = booking["serviced"]
        unique_teller = booking["unique_teller"]
        forwarded = booking["forwarded"]

        booking = booking_exists_by_unique_id(unique_id)
        if booking:
            if bool(status):
                if not booking_is_serviced(unique_id):
                    booking.serviced = True
                    db.session.commit()
            if bool(forwarded):
                if unique_teller:
                    if not booking_is_forwarded(unique_id):
                        booking.forwarded = True
                        booking.unique_teller = unique_teller
                        db.session.commit()
        else:
            # request offline data for sync
            sio.emit("booking_update", unique_id)
    return dict()


@sio.on("all_sync_offline_data")
def sync_offline_data(data):
    # get each data category loop each of the list while posting on a timer to the
    # appropriate end point
    if data:
        parsed_data = dict(data)
        if parsed_data:
            if parsed_data["services"]:
                # deal with services offered
                for service in parsed_data["services"]:
                    service.update({"key": parsed_data["key"]})
                    requests.post(f"{link}/sycn/offline/services", json=service)

            if parsed_data["tellers"]:
                for teller_ in parsed_data["tellers"]:
                    teller_.update({"key_": parsed_data["key"]})
                    requests.post(f"{link}/sycn/offline/teller", json=teller_)

            if parsed_data["bookings"]:
                # deal with bookings
                for booking in parsed_data["bookings"]:
                    booking.update({"key_": parsed_data["key"]})
                    requests.post(f"{link}/sycn/online/booking", json=booking)

            if parsed_data["bookings_verify"]:
                update_booking_by_unique_id(parsed_data["bookings_verify"])

            # this key here  will trigger the data for a specific branch to be
            # fetched and pushed down to the backend module.
            data = sync_service(parsed_data["key"])
            final = list()
            key = parsed_data["key"]
            # data.append(key)
            final.append(data)
            final.append(key)
            if parsed_data["key"]:
                sio.emit("all_sync_online", {"data": final})


# booking_resync_data
@sio.on("booking_resync_data")
def booking_resync_data_(data):
    return requests.post(f"{link}/sycn/online/booking", json=data)


# ---------------------------------
# ------ ACKS from offline --------
# ---------------------------------


def ack_teller_fail(data):
    # check if it exists -> if true -> flag as synced if not { inform user of synced }  -> else trigger a sync
    teller = teller_exists_unique(data["data"]["unique_id"])
    if teller:
        if teller["is_synced"]:
            # teller is synced
            log("Teller Already Synced")
        else:
            # teller does not exists
            # trigger async
            sio.emit("add_teller", {"teller_data": data["data"]})


def ack_booking_fail(data):
    booking = booking_exists_unique(data)
    if booking:
        if booking.is_synced:
            # booking is synced
            log("Booking Already Synced")
        else:
            # booking is not synced
            # trigger async
            sio.emit("online_", {"booking_data": data})


def ack_service_fail(data):
    # check if it exists -> if true -> flag as synced if not { inform user of synced }  -> else trigger a sync
    service = service_exists_unique(data["data"]["unique_id"])
    if service:
        if service["is_synced"]:
            log("Service Already Synced")
        else:
            sio.emit("sync_service", data["data"])


def ack_teller_success(data):
    # flag as sycned here based on unique key
    return flag_teller_as_synced(data)


def ack_service_success(data):
    # flag as sycned here based on unique key
    return flag_service_as_synced(data)


def ack_booking_success(data):
    # flag as sycned here based on unique key
    return flag_booking_as_synced(data)


def teller_exists_unique(unique_id):
    return Teller.query.filter_by(unique_id=unique_id).first()


def service_exists_unique(unique_id):
    return ServiceOffered.query.filter_by(unique_id=unique_id).first()


def is_this_branch(key):
    return branch_exists_key(key)


ack_mapper_success = {
    "SERVICE": ack_service_success,
    "TELLER": ack_teller_success,
    "BOOKING": ack_booking_success
}

ack_mapper_fail = {
    "SERVICE": ack_service_fail,
    "TELLER": ack_teller_fail,
    "BOOKING": ack_booking_fail
}


# ack_successful_enitity_online_data
@sio.on("ack_successful_enitity_online_data")
def ack_successful_enitity_online_data_(data):
    log("offline -> online sync [success]")
    # categories = SERVICE TELLER BOOKING
    ack_mapper_success[data["category"]](data["data"])


@sio.on("ack_failed_enitity_online_data")
def ack_failed_enitity_online_data_(data):
    if data:
        log("offline -> online sync [failed]")
        ack_mapper_fail[data["category"]](data["data"])


def flag_booking_as_synced(data):
    booking = booking_exists_unique(data)
    if booking:
        booking.is_synced = True
        db.session.commit()
    return booking


def flag_service_as_synced(data):
    service = booking_exists_unique(data)
    if service:
        service.is_synced = True
        db.session.commit
    return service


def flag_teller_as_synced(data):
    teller = booking_exists_unique(data)
    if teller:
        teller.is_synced = True
    return teller


# ---------------------------------
# ------------END------------------
# ---------------------------------

@sio.on("add_teller_data")
def add_teller_data(data):
    data = data["teller_data"]
    requests.post(f"{link}/sycn/offline/teller", json=data)


# update_teller_data
@sio.on("update_teller_data")
def add_teller_data(data):
    log(data)
    requests.post(f"{link}/sycn/online/booking", json=data)


@sio.on("verify_key_data")
def verify_key(key):
    lookup = Branch.query.filter_by(key_=key).first()
    if lookup:
        sio.emit("key_response", branch_schema.dump(lookup))


@sio.on("reset_ticket_request")
def reset_tickets_listener(data):
    return requests.post(f"{link}/reset/ticket/counter", json=data)


try:
    sio.connect(socket_link)
except socketio.exceptions.ConnectionError:
    print("Error! Could not connect to the socket server.")
