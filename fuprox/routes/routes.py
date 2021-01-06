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


def get_all_bookings_no_branch():
    data = Booking.query.filter_by(nxt=1001).all()
    return bookings_schema.dump(data)


def loop_data_check_reset_tickets(data):
    ticket_reset = list()
    for item in data:
        if item.nxt == 4004:
            ticket_reset.append(item)
    return ticket_reset


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
                                               forwarded=forwarded, unique_teller=unique_teller)
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
                           is_synced=False, serviced=False, forwarded=False, unique_teller=0):
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
            log("booking Exists")

            if bool(status):
                if not booking_is_serviced(unique_id):
                    booking.serviced = True
                    db.session.commit()
            if bool(forwarded):
                booking.forwarded = True
                booking.unique_teller = unique_teller
                db.session.commit()
        else:
            log("booking Exists")
            # request offline data for sync
            sio.emit("booking_update", unique_id)
    return dict()


def update_booking_by_unique_id_single(booking):
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
            log("we are hit")
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
    update_booking_by_unique_id_single(data)
    # requests.post(f"{link}/sycn/online/booking", json=data)


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
