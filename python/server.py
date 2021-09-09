import requests

from json import dumps

import decouple
import time

from oauthlib.common import urldecode
from oauthlib.oauth2 import WebApplicationClient
from requests_oauthlib import OAuth2Session

from flask import Flask, request, redirect, session, jsonify
from flask_mongoengine import MongoEngine

# To prevent errors while running on localhost over HTTP rather than HTTPS
import os

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

app = Flask(__name__)
# Host and IP for the local server, running on http://host:port
HOST = decouple.config("HOST")
PORT = decouple.config("PORT")


#mongo database configuration settings
app.config['MONGODB_SETTINGS'] = {
    'db': 'hackers',
    'host': 'localhost',
    'port': 27017
}
db = MongoEngine()
db.init_app(app)

# database tables = models
class Customer(db.Document):
    customer_number = db.StringField()
    connection_id = db.StringField()
    name = db.StringField()
    email = db.StringField()

class Courses(db.Document):
    course_number = db.StringField()
    course_name = db.StringField()
    course_description = db.StringField()

class TrackCourses(db.Document):
    customer_number = db.StringField()
    course_number = db.StringField()

class TrackConsumption(db.Document):
    total_consumption = db.StringField()   
     


# 1000010 | 1
# 1000010 | 2
# 1000010 | 3
# 1000011 | 1
# 1000012 | 1


# YOUR CLIENT CREDENTIALS CONFIG
CLIENT_ID = decouple.config("CLIENT_ID")
CLIENT_SECRET = decouple.config("CLIENT_SECRET")


REDIRECT_URI = f"http://{HOST}:{PORT}/callback"
AUTH_URL = decouple.config("AUTH_URL")
TOKEN_URL = decouple.config("TOKEN_URL")
API_URL = decouple.config("API_URL")

# Your scopes, list of strings
scope = decouple.config("SCOPES", cast=lambda v: [s.strip() for s in v.split(',')])

# An unguessable random string. It is used to protect against CSRF attacks.
state = "super-secret-state"

# API endpoints
SESSION_ENDPOINT = f"{API_URL}/session/"
CONSUMPTION_SUMMARY_ENDPOINT = f"{API_URL}/consumption/summary/"+"{}/{}/"
CONSUMPTION_AVERAGES_ENDPOINT = f"{API_URL}/consumption/averages/"+"{}/{}/?start_date={}&end_date={}&group_by={}"


@app.route("/")
def authorization():
    """User Authorization.
    Redirect the user/resource owner to our OAuth provider
    While supplying key OAuth parameters.
    """
    # Here we're using `WebApplicationClient` to utilize authorization code grant
    client = WebApplicationClient(client_id=CLIENT_ID)
    request_uri = client.prepare_request_uri(
        AUTH_URL, redirect_uri=REDIRECT_URI, scope=scope, state=state
    )
    # State is used to prevent CSRF, we'll keep it to reuse it later.
    session["oauth_state"] = state
    return redirect(request_uri)


@app.route("/callback", methods=["GET"])
def callback():
    """Retrieving an access token.
    After you've redirected from our provider to your callback URL,
    you'll have access to the auth code in the redirect URL, which
    we'll be using to get an access token.
    """

    client = WebApplicationClient(client_id=CLIENT_ID)
    # Parse the response URI after the callback, with the same state we initially sent
    client.parse_request_uri_response(
        request.url, state=session["oauth_state"])
    # Now we've access to the auth code
    code = client.code

    # Prepare request body to get the access token
    body = client.prepare_request_body(
        code=code,
        redirect_uri=REDIRECT_URI,
        include_client_id=False,
        scope=scope,
    )

    # Basic HTTP auth by providing your client credentials
    auth = requests.auth.HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET)

    # Making a post request to the TOKEN_URL endpoint
    r = requests.post(TOKEN_URL, data=dict(urldecode(body)), auth=auth)

    # Parse the response to get the token and store it in session
    token = client.parse_request_body_response(r.text, scope=scope)
    session["access_token"] = token

    return redirect("/home")


@app.route("/home", methods=["GET"])
def home():
    # Redirect user to auth endpoint if access token is missing
    if session.get("access_token", None) is None:
        return redirect("/")
    return """
    <h1>Access token obtained!</h1>
    <ul>
        <li><a href="/sample_api_calls">Sample API calls</a></li>
    </ul>
    """

@app.route("/hackers", methods=["GET"])
def hackers():
    # Redirect user to auth endpoint if access token is missing
    if session.get("access_token", None) is None:
        return redirect("/")

    # Make a request to the API
    oauth_session = OAuth2Session(token=session["access_token"])
    try:
        response = oauth_session.get(SESSION_ENDPOINT)
    except:
        return redirect("/")


    # Prepare data for summary end point
    # Get customer data
    customer = response.json()["data"]["customer"][0]
    customer_number = customer["customer_number"]
    connection_id = customer["connection"]["connection_id"]
    name = customer["first_name"] + " " + customer["last_name"]
    email = customer["email"]

    print(customer_number,name,email)

    customer = Customer(
                customer_number=str(customer_number),
                connection_id=str(connection_id),
                name=name,
                email=email,
            ).save()

    db_customer = Customer.objects(customer_number=str(customer_number)).first()

    if not db_customer:
        return jsonify({'error': 'data not found'})
    else:
        db_customer_data = db_customer

    print(db_customer_data)
    db_customer_name = db_customer_data["name"]

    

    time.sleep(1)

    api_response = oauth_session.get(CONSUMPTION_AVERAGES_ENDPOINT.format(customer_number, connection_id, '2020-01-01', '2020-01-31', 'day'))

    start_date = api_response.json()["data"]["range"]["start_date"] 

    consumption = api_response.json()["total consumption"]

    
    #print(dumps(api_response.json(), indent=3))
    #print(start_date)

    return """
        <html>
            <head>
                
            </head>
            <body>
                <div>{out_start_date}</div>
                <div>{customer_name}</div>
            </body>
        </html>
    """.format(
        out_start_date=start_date,
        customer_name=db_customer_name,
        total_consumption = consumption




    )
    

@app.route("/sample_api_calls", methods=["GET"])
def sample_api_calls():
    # Redirect user to auth endpoint if access token is missing
    if session.get("access_token", None) is None:
        return redirect("/")

    # /session/ call
    # Create an OAuth2Session with the access token we've previously obtained
    oauth_session = OAuth2Session(token=session["access_token"])
    # GET request to sessions end point
    response = oauth_session.get(SESSION_ENDPOINT)

    # Prepare data for summary end point
    # Get customer data
    customer = response.json()["data"]["customer"][0]
    # Get customer number
    customer_number = customer["customer_number"]
    # Get get customer's connection ID
    connection_id = customer["connection"]["connection_id"]

    time.sleep(1)
    # /consumption/summary/customer_number/connection_id/ call
    summary_response = oauth_session.get(
        CONSUMPTION_SUMMARY_ENDPOINT.format(customer_number, connection_id)
    )

    print(dumps(summary_response.json(), indent=3))

    return """
        <h1>/session/ response</h1>
        <div>%s</div>
        <h1>/consumption/summary/ response</h1>
        <div>%s</div>
    """ % (
        dumps(response.json(), indent=3),
        dumps(summary_response.json(), indent=3),
    )


if __name__ == "__main__":
    app.secret_key = "super secret key"
    app.config["SESSION_TYPE"] = "filesystem"
    app.debug = True
    app.run(host=HOST, port=PORT)