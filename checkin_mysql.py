#!/usr/bin/env python3
from datetime import datetime
from datetime import timedelta
from dateutil.parser import parse
from docopt import docopt
from math import trunc
from pytz import utc
from southwest import Reservation, openflights
from threading import Thread
import sys
import time
import flights_db

CHECKIN_EARLY_SECONDS = 5

def schedule_checkin(flight_time, reservation, prikey):
    checkin_time = flight_time - timedelta(days=1)
    current_time = datetime.utcnow().replace(tzinfo=utc)

    # check to see if we need to sleep until 24 hours before flight
    if checkin_time > current_time:
        # calculate duration to sleep
        delta = (checkin_time - current_time).total_seconds() - CHECKIN_EARLY_SECONDS
        # pretty print our wait time
        m, s = divmod(delta, 60)
        h, m = divmod(m, 60)
        print(("Too early to check in.  Waiting {} hours, {} minutes, {} seconds".format(trunc(h), trunc(m), s)))
        time.sleep(delta)
    data = reservation.checkin()
    for flight in data['flights']:
        for doc in flight['passengers']:
            print(("{} got {}{}!".format(doc['name'], doc['boardingGroup'], doc['boardingPosition'])))
            boarding_num = "%s%s" % (doc['boardingGroup'],doc['boardingPosition'])

            # open database to store boarding number
            db = flights_db.connect()
            cursor = db.cursor(dictionary=True)

            #checked in so don't try next time
            query = "UPDATE flightinfo SET boardingnum=%s WHERE conf=%s AND prikey=%s"
            cursor.execute(query,(boarding_num, doc['confirmationNumber'], prikey))
            db.commit()
            db.close()

def set_takeoff(reservation_number, first_name, last_name, notify=[]):
    r = Reservation(reservation_number, first_name, last_name, notify)
    body = r.lookup_existing_reservation()

    # connect to db to store date
    db = flights_db.connect()
    cursor = db.cursor(dictionary=True)
    i=0

    # find all eligible legs for checkin
    for leg in body['bounds']:
        # calculate departure for this leg
        print("calc departure in leg")
        airport = "{}, {}".format(leg['departureAirport']['name'], leg['departureAirport']['state'])
        takeoff = "{} {}".format(leg['departureDate'], leg['departureTime'])
        for item in leg['flights']:
            flightnum = item['number']
        airport_tz = openflights.timezone_for_airport(leg['departureAirport']['code'])
          
        # need to convert this to computer time so we start checkin at the right time
        cpu_tz = openflights.timezone_for_airport('DEN')
        temp = airport_tz.localize(datetime.strptime(takeoff, '%Y-%m-%d %H:%M'))
        date = temp.astimezone(cpu_tz)

        if i is 0:
            query = "UPDATE flightinfo SET takeoff=%s, flightnum=%s WHERE conf=%s"
            cursor.execute(query,(date,flightnum,reservation_number))
            db.commit()
        else:
            query = "INSERT INTO flightinfo (takeoff, flightnum, conf, first, last) VALUES (%s, %s, %s, %s, %s)"
            cursor.execute(query,(date,flightnum,reservation_number, first_name, last_name))
            db.commit()
        i+=1 

    db.close()
    return ()

def auto_checkin(threads, reservation_number, first_name, last_name, prikey, notify=[]):
    r = Reservation(reservation_number, first_name, last_name, notify)
    body = r.lookup_existing_reservation()

    # Get our local current time
    now = datetime.utcnow().replace(tzinfo=utc)
    tomorrow = now + timedelta(days=1)

    # find all eligible legs for checkin
    for leg in body['bounds']:
        print("auto check in leg")
        # calculate departure for this leg
        airport = "{}, {}".format(leg['departureAirport']['name'], leg['departureAirport']['state'])
        takeoff = "{} {}".format(leg['departureDate'], leg['departureTime'])
        airport_tz = openflights.timezone_for_airport(leg['departureAirport']['code'])
        date = airport_tz.localize(datetime.strptime(takeoff, '%Y-%m-%d %H:%M'))
        print(date)
        print(now)
        if date > now:
            # found a flight for checkin!
            print(("Flight information found, departing {} at {}".format(airport, date.strftime('%b %d %I:%M%p'))))
            # Checkin with a thread
            t = Thread(target=schedule_checkin, args=(date, r, prikey))
            t.daemon = True
            t.start()
            threads.append(t)
            # Need to go to the next conf so send back threads to manage
            return threads

if __name__ == '__main__':

    print("======================")
    print("Starting Checkin Mysql")
    print((str(datetime.now())))
    db = flights_db.connect()
    cursor = db.cursor(dictionary=True)

    # capture takeoff times if not set in mysql
    query = "SELECT * FROM flightinfo WHERE takeoff IS NULL and conf IS NOT NULL"

    cursor.execute(query)

    records = cursor.fetchall()

    for record in records:
        print(("Getting Takeoff time for {}".format(record['conf'])))
        set_takeoff(record['conf'], record['first'], record['last'])

    # get those that are less than two hours from checkin (run cron every two hours)
    query = "SELECT * FROM flightinfo WHERE ((takeoff - INTERVAL 26 HOUR) < NOW()) AND boardingnum IS NULL"

    cursor.execute(query)

    records = cursor.fetchall()
    db.close()
    threads = []

    for record in records:
        print(("Checkin time for {}".format(record['conf'])))
        reservation_number = record['conf']
        first_name = record['first']
        last_name = record['last']
        email = record['email']
        mobile = record['mobile']
        prikey = record['prikey']

        # build out notifications
        notifications = []
        if email is not None:
            print("adding email")
            notifications.append({'mediaType': 'EMAIL', 'emailAddress': email})
        if mobile is not None:
            print("adding mobile")
            notifications.append({'mediaType': 'SMS', 'phoneNumber': mobile})

        threads = auto_checkin(threads,reservation_number, first_name, last_name, prikey, notifications)
    try:
        # cleanup threads while handling Ctrl+C
        while True:
            if len(threads) == 0:
                break
            for t in threads:
                t.join(5)
                if not t.isAlive():
                    threads.remove(t)
                    break
    except KeyboardInterrupt:
        print("Ctrl+C detected, canceling checkin")
        sys.exit()

    print("Exiting Checkin Mysql")
    print("======================")
