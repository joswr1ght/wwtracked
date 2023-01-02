#!/usr/bin/env python3

import sys
import datetime
import requests
import json
import pdb
import logging
import http.client as http_client


# WW API endpoint with date at the end in the format YYYY-MM-DD
ENDPOINT = 'https://cmx.weightwatchers.com/api/v3/cmx/operations/composed/members/~/my-day'

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
        url = f'{ENDPOINT}/{date}'
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




