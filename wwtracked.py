#!/usr/bin/env python3

import sys
import datetime
import requests
import json
import csv
import random
# import logging
import getpass
import argparse
from urllib import parse
# import pdb


def daterange(date1, date2):
    """
    Return a list of date strings in the format YYYY-MM-DD
    """
    assert type(date1) == datetime.date, 'Dates must be datetime.date objects'
    assert type(date2) == datetime.date, 'Dates must be datetime.date objects'

    dates = []
    for n in range(int((date2 - date1).days) + 1):
        dt = date1 + datetime.timedelta(n)
        dates.append(dt.strftime('%Y-%m-%d'))
    return dates


def printfood(foods):
    """
    Using the food elements for morning, midday, evening, or anytime,
    display the food name and portion (if available) as a Markdown
    bulleted item.
    """
    assert type(foods) == list, 'foods must be a list'

    for food in foods:
        assert type(food) == dict, 'food in list must be a dict'
        try:
            foodname = food['name']
            if requestnutrition:
                nutritionarr.append(getfoodentrynutrition(food))
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


def getfoodentrynutrition(foodentry):
    """
    Takes the food entry passed to it and calculates the nutrition of the
    food entry by matching the serving type of the entry to the nutritional
    data from WW and multiplying by the entry serving size. Returns dict of data
    """
    assert type(foodentry) == list, 'foodentry must be a list'

    if foodentry['sourceType'] != 'MEMBERFOODQUICK':  # ignore quick add items
        data = {'name': foodentry['name'], 'id': foodentry['_id'], 'entryId': foodentry['entryId'],
                'trackedDate': foodentry['trackedDate'], 'timeOfDay': foodentry['timeOfDay'],
                'sourceType': foodentry['sourceType'], 'portionName': '', 'portionSize': foodentry['portionSize'],
                'calories': 0, 'fat': 0, 'saturatedFat': 0, 'sodium': 0, 'carbs': 0, 'fiber': 0, 'sugar': 0,
                'addedSugar': 0, 'protein': 0}

        # Different types of entries have different API endpoints
        urlprefix = {'WWFOOD': 'https://cmx.weightwatchers.com/api/v3/public/foods/',
                     'MEMBERFOOD': 'https://cmx.weightwatchers.com/api/v3/cmx/members/~/custom-foods/foods/',
                     'WWVENDORFOOD': 'https://cmx.weightwatchers.com/api/v3/public/foods/',
                     'MEMBERRECIPE': 'https://cmx.weightwatchers.com/api/v3/cmx/members/~/custom-foods/recipes/',
                     'WWRECIPE': 'https://cmx.weightwatchers.com/api/v3/public/recipes/'}

        entryurl = f'{urlprefix[foodentry["sourceType"]]}{foodentry["_id"]}?fullDetails=true'

        # Recipes must be handled differently
        if 'RECIPE' in foodentry['sourceType']:
            recipe = True
            data['portionName'] = 'serving(s)'
            foodnutrition = requests.get(entryurl, headers=authheader).json()
        else:
            recipe = False
            data['portionName'] = foodentry['portionName']
            foodnutrition = requests.get(entryurl, headers=authheader).json()['portions']

        size = data['portionSize']  # portion size applies to both recipes and non-recipe entries

        while True and not recipe:
            for nutrition in foodnutrition:
                # match entry serving type (oz, g, cups, etc) to correct nutritional data type from WW API
                if nutrition['name'] == foodentry['portionName']:
                    data['calories'] = round(nutrition['nutrition']['calories'] / nutrition['size'] * size)
                    data['fat'] = round(nutrition['nutrition']['fat'] / nutrition['size'] * size, 1)
                    data['saturatedFat'] = round(nutrition['nutrition']['saturatedFat'] / nutrition['size'] * size, 1)
                    data['sodium'] = round(nutrition['nutrition']['sodium'] / nutrition['size'] * size, 1)
                    data['carbs'] = round(nutrition['nutrition']['carbs'] / nutrition['size'] * size, 1)
                    data['fiber'] = round(nutrition['nutrition']['fiber'] / nutrition['size'] * size, 1)
                    data['sugar'] = round(nutrition['nutrition']['sugar'] / nutrition['size'] * size, 1)
                    data['addedSugar'] = round(nutrition['nutrition']['addedSugar'] / nutrition['size'] * size, 1)
                    data['protein'] = round(nutrition['nutrition']['protein'] / nutrition['size'] * size, 1)
                    break
            break  # in case for some reason there is no match

        if recipe:
            def ingredientnutrition(x): return ingredient['itemDetail']['portions'][0]['nutrition'][x] / \
                                            ingredient['itemDetail']['portions'][0]['size'] * ingredient['quantity'] / \
                                            foodnutrition['servingSize'] * size

            for ingredient in foodnutrition['ingredients']:
                data['calories'] += round(ingredientnutrition('calories'))
                data['fat'] += round(ingredientnutrition('fat'), 1)
                data['saturatedFat'] += round(ingredientnutrition('saturatedFat'), 1)
                data['sodium'] += round(ingredientnutrition('sodium'), 1)
                data['carbs'] += round(ingredientnutrition('carbs'), 1)
                data['fiber'] += round(ingredientnutrition('fiber'), 1)
                data['sugar'] += round(ingredientnutrition('sugar'), 1)
                data['addedSugar'] += round(ingredientnutrition('addedSugar'), 1)
                data['protein'] += round(ingredientnutrition('protein'), 1)

        return data


def writenutritiondata(nutritionarr):
    """
    Takes the array of food nutrition dictionaries and writes to CSV
    """
    assert type(nutritionarr) == list, 'nutritionarr must be a list'

    fields = ['Date', 'When', 'Food', 'Calories', 'Fat', 'Saturated Fat', 'Sodium', 'Carbohydrates', 'Fiber', 'Sugars',
              'Added Sugar', 'Protein']

    if startdate == enddate:
        filename = f'Nutrition Data {startdate}.csv'
    else:
        filename = f'Nutrition Data {startdate} to {enddate}.csv'

    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow(fields)

            for item in nutritionarr:
                name = f'{item["name"]}, {item["portionSize"]} {item["portionName"]}'
                csvwriter.writerow([item['trackedDate'], item['timeOfDay'], name, item['calories'],
                                    item['fat'], item['saturatedFat'], item['sodium'], item['carbs'], item['fiber'],
                                    item['sugar'], item['addedSugar'], item['protein']])

        sys.stderr.write(f'Nutrition data written to "{filename}"\n')
    except PermissionError:
        sys.stderr.write(f'ERROR: Could not save nutrition data, ensure "{filename}" is not already open.\n')


def checkjwt(jwt):
    """
    Validate JWT. Return False if not valid.
    """
    assert type(jwt) == str, 'JWT must be type str'

    if jwt[0:3] != 'eyJ' and jwt[0:10] != 'Bearer eyJ':
        return False
    # With the Bearer prefix, the JWT I'm seeing is 1095 characters. Check for length
    # at least 900 to give us a sanity check of JWT
    if len(jwt) < 900:
        return False

    return True


def login(email, password):
    """
    Login to the WW website and return the JWT using the email address and password.

    The WW login process requires 2 steps:

        1. Send email and password in JSON POST to
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
    assert type(email) == str, 'Email must be a string'
    assert type(password) == str, 'Password must be a string'

    tokenid = login1(email, password)
    if tokenid is None:
        return None

    return login2(tokenid)


def login1(email, password):
    """
    Login with email and password to retrieve the tokenId value.

    Return tokenid or None
    """
    assert type(email) == str, 'Email must be a string'
    assert type(password) == str, 'Password must be a string'

    tokenid = None

    authrequest = {
            'username': email,
            'password': password,
            'rememberMe': False,
            'usernameEncoded': False,
            'retry': False
    }

    authheader = {
            'Content-Type': 'application/json'
    }

    url = 'https://auth.weightwatchers.com/login-apis/v1/authenticate'
    response = requests.post(url, headers=authheader, json=authrequest)
    if (response.status_code != 200):
        sys.stderr.write(f'ERROR: Invalid response from login endpoint ({response.status_code}). ')
        sys.stderr.write('Make sure you have the correct email and password.\n')
        sys.exit(-1)

    try:
        responsedata = json.loads(response.content)
        tokenid = responsedata['data']['tokenId']
    except ValueError:
        sys.stderr.write('ERROR: Missing tokenId in response data (API changed?)\n')
        sys.exit(-1)

    return tokenid


def login2(tokenid):
    """
    Complete step 2 of login with tokenid as wwAuth2 cookie.

    Return id_token/JWT.
    """
    assert type(tokenid) == str, 'tokenid must be a string'

    nonce = hex(random.getrandbits(128))[2:]
    url = (f'https://auth.weightwatchers.com/openam/oauth2/authorize?response_type=id_token&'
           f'client_id=webCMX&redirect_uri=https%3A%2F%2Fcmx.weightwatchers.com%2Fauth&nonce={nonce}')
    cookies = {
        'wwAuth2': f'{tokenid}'
    }

    response = requests.get(url, cookies=cookies, allow_redirects=False)
    if (response.status_code != 302):
        sys.stderr.write('ERROR: Unexpected response status code from authorize endpoint (API changed?)\n')
        exit(-1)

    # The redirect location has the JWT
    redirecturl = response.headers['Location']
    responsedata = dict(parse.parse_qsl(parse.urlsplit(redirecturl).fragment))
    return responsedata['id_token']


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-E', '--email', help='Specify the login email address')
    group.add_argument('-J', '--jwt', help='Specify the JWT')
    parser.add_argument('-s', '--start', required=True, help='Start date as YYYY-MM-DD')
    parser.add_argument('-e', '--end', required=True, help='End date as YYYY-MM-DD')
    parser.add_argument('-n', '--nutrition', action='store_true', help='Produce a CSV report of nutritional data')
    args = parser.parse_args()

    if (args.email is None and args.jwt is None):
        sys.stderr.write('ERROR: Must specify the login email address with -E or a JWT with -J.\n')
        parser.print_help()
        sys.exit(1)

    # Parse the easy stuff first
    startdate = datetime.date(*map(int, args.start.split('-')))
    enddate = datetime.date(*map(int, args.end.split('-')))
    if (startdate > enddate):
        sys.stderr.write('ERROR: Start date cannot follow end date.\n')
        sys.exit(-1)

    # Get password for interactive login, or use JWT
    if (args.email is not None):
        # User specified email; if % is included, split for email and password
        # I stole this convention from the SAMBA project (smbclient, rpcclient)
        if '%' in args.email:
            email, password = args.email.split('%')
        else:
            # Read password from STDIN
            password = getpass.getpass()
            email = args.email
        if len(password) < 8 or len(password) > 20:
            sys.stderr.write('ERROR: Password must be between 8 and 20 characters\n')
            parser.print_help()
            sys.exit(-1)

        # Get the JWT
        jwt = login(email, password)
    else:
        # Allow JWT to include 'Bearer ' prefix
        if (args.jwt[0:7] == 'Bearer '):
            jwt = args.jwt[7:]
        else:
            jwt = args.jwt

        # Email is not supplied when authenticating with JWT
        email = None

    if (checkjwt(jwt) is False):
        sys.stderr.write('ERROR: Invalid JWT. Double-check the JWT specified with -J.\n')
        sys.exit(-1)

    if args.nutrition:
        requestnutrition = True
        nutritionarr = []
    else:
        requestnutrition = False

    authheader = {'Authorization': f'Bearer {jwt}'}

    # Start generating the Markdown report
    if (email is not None):
        print(f'# Weight Watchers Tracked Food Report for {email}\n\n> {args.start} - {args.end}\n')
    else:
        print(f'# Weight Watchers Tracked Food Report\n\n> {args.start} - {args.end}\n')

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
        print(f'\n## {date}')

        try:
            print('\n### Breakfast\n')
            morning = trackedday['today']['trackedFoods']['morning']
            printfood(morning)
        except KeyError:
            pass

        try:
            print('\n### Lunch\n')
            midday = trackedday['today']['trackedFoods']['midday']
            printfood(midday)
        except KeyError:
            pass

        try:
            print('\n### Dinner\n')
            evening = trackedday['today']['trackedFoods']['evening']
            printfood(evening)
        except KeyError:
            pass

        try:
            print('\n### Snacks\n')
            anytime = trackedday['today']['trackedFoods']['anytime']
            printfood(anytime)
        except KeyError:
            pass

        print('')

    if requestnutrition:
        writenutritiondata(nutritionarr)
