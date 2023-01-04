#!/usr/bin/env python3

import sys
import datetime
import requests
import json
import random
import pdb
import logging
from urllib import parse



"""
Return a list of date strings in the format YYYY-MM-DD
"""
def daterange(date1, date2):
    assert type(date1) == datetime.date, 'Dates must be datetime.date objects'
    assert type(date2) == datetime.date, 'Dates must be datetime.date objects'

    dates = []
    for n in range(int((date2 - date1).days)+1):
        dt = date1 + datetime.timedelta(n)
        dates.append(dt.strftime('%Y-%m-%d'))
    return dates


"""
Using the food elements for morning, midday, evening, or anytime,
display the food name and portion (if available) as a Markdown
bulleted item.
"""
def printfood(foods):
    assert type(foods) == list, 'foods must be a list'

    for food in foods:
        assert type(food) == dict, 'food in list must be a dict'
        try:
            foodname = food['name']
        except KeyError:
            # No tracked food, continue through list
            continue

        try:
            foodportion = food['portionName']
            foodsize = food['portionSize']
            suffix = f', {foodsize} {foodportion}'
        except KeyError:
            # Quick add foods lack a portion size and portion name
            suffix = ''
        print(f'* {foodname}{suffix}')


"""
Validate JWT. Return False if not valid.
"""
def checkjwt(jwt):
    assert type(jwt) == str, 'JWT must be type str'

    if jwt[0:3] != 'eyJ' and jwt[0:10] != 'Bearer eyJ':
        return False
    # With the Bearer prefix, the JWT I'm seeing is 1095 characters. Check for length
    # at least 1000 to give us a sanity check of JWT
    if len(jwt) < 1000:
        return False

    return True


"""
Login to the WW website and return the JWT.

The WW login process requires 2 steps:

    1. Send username and password in JSON POST to
       auth.weightwatchers.com/login-apis/v1/authenticate.  In the server
       response, obtain the tokenId in the body response JSON blob.
    2. Send tokenId value as `wwAuth2` cookie in GET request to
       https://auth.weightwatchers.com/openam/oauth2/authorize with several URL
       parameters including a client-side selected nonce.  Server will return a
       HTTP/302 Found response with a Location header. The id_token parameter in
       the Location header is the JWT used for subsequent API access.

This function calls these step steps as login1() and login2().

TODO: When the server response isn't what we expect, we sys.exit(-1), but
ideally this should raise an exception instead.

Returns JWT or None.
"""
def login(username, password):
    assert type(username) == str, 'Username must be a string'
    assert type(password) == str, 'Password must be a string'

    tokenid = login1(username, password)
    if tokenid == None:
        return None

    return login2(tokenid)



"""
Login with username and password to retrieve the tokenId value.

Return tokenid or None
"""
def login1(username, password):
    assert type(username) == str, 'Username must be a string'
    assert type(password) == str, 'Password must be a string'

    tokenid = None

    authrequest = {
            'username'        : username,
            'password'        : password,
            'rememberMe'      : False,
            'usernameEncoded' : False,
            'retry'           : False
    }

    authheader = {
            'Content-Type' : 'application/json'
    }

    url = 'https://auth.weightwatchers.com/login-apis/v1/authenticate'
    response = requests.post(url, headers=authheader, json=authrequest)
    if (response.status_code != 200):
        sys.stderr.write(f'ERROR: Invalid response from login step 1 endpoint ({response.status_code}). ')
        sys.stderr.write('Make sure you have the correct username and password.\n')
        sys.exit(-1)

    try:
        responsedata = json.loads(response.content)
        tokenid = responsedata['data']['tokenId']
    except ValueError:
        sys.stderr.write('ERROR: Missing tokenId in response data (API changed?)\n')
        sys.exit(-1)

    return tokenid


"""
Complete step 2 of login with tokenid as wwAuth2 cookie.

Return id_token/JWT.
"""
def login2(tokenid):
    assert type(tokenid) == str, 'tokenid must be a string'

    nonce = hex(random.getrandbits(128))[2:]
    url = f'https://auth.weightwatchers.com/openam/oauth2/authorize?response_type=id_token&client_id=webCMX&redirect_uri=https%3A%2F%2Fcmx.weightwatchers.com%2Fauth&nonce={nonce}'
    cookies = {
        'wwAuth2': f'{tokenid}'
    }

    response = requests.get(url, cookies=cookies, allow_redirects=False)
    if (response.status_code != 302):
        sys.stderr.write('ERROR: Unexpected response status code (API changed?)\n')
        exit(-1)

    # The redirect location has the JWT
    redirecturl = response.headers['Location']
    responsedata = dict(parse.parse_qsl(parse.urlsplit(redirecturl).fragment))
    return responsedata['id_token']


if __name__ == '__main__':
    if (len(sys.argv) != 4):
        sys.stderr.write(f'Usage: {sys.argv[0]} startdate enddate JWT\n')
        sys.stderr.write('\nDates must be in the format YYYY-MM-DD.\n')
        sys.exit(1)

    startdate = datetime.date(*map(int, sys.argv[1].split('-')))
    enddate = datetime.date(*map(int, sys.argv[2].split('-')))

    # Allow JWT to include 'Bearer ' prefix
    if (sys.argv[3][0:7] == 'Bearer '):
        jwt = sys.argv[3][7:]
    else:
        jwt = sys.argv[3]

    if (checkjwt(jwt) == False):
        sys.stderr.write('ERROR: Invalid JWT. Get a valid JWT from your logged-in Firefox session.\n')
        sys.exit(-1)

    authheader = {'Authorization': f'Bearer {jwt}'}

    print(f'# Weight Watchers Tracked Food Report\n\n> {sys.argv[1]} - {sys.argv[2]}\n')

    for date in daterange(startdate, enddate):
        # WW API endpoint with date at the end in the format YYYY-MM-DD
        endpointurl = 'https://cmx.weightwatchers.com/api/v3/cmx/operations/composed/members/~/my-day'
        url = f'{endpointurl}/{date}'
        response = requests.get(url, headers=authheader)
        if (response.status_code != 200):
            sys.stderr.write(f'ERROR: Invalid response from weightwatchers.com API ({response.status_code}). ')
            sys.stderr.write('Make sure you have a valid JWT from a logged-in browser session.\n')
            exit(-1)

        trackedday = json.loads(response.content)
        print(f'\n\n## {date}')

        try:
            print('\n### Breakfast')
            morning = trackedday['today']['trackedFoods']['morning']
            printfood(morning)
        except KeyError:
            pass

        try:
            print('\n### Lunch')
            midday = trackedday['today']['trackedFoods']['midday']
            printfood(midday)
        except KeyError:
            pass

        try:
            print('\n### Dinner')
            evening = trackedday['today']['trackedFoods']['evening']
            printfood(evening)
        except KeyError:
            pass

        try:
            print('\n### Snacks')
            anytime = trackedday['today']['trackedFoods']['anytime']
            printfood(anytime)
        except KeyError:
            pass

        print('')




