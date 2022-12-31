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
            suffix = f", {foodsize} {foodportion}"
        except KeyError:
            # Quick add foods lack a portion size and portion name
            suffix = ''
        print(f"* {foodname}{suffix}")


if __name__ == '__main__':
    if (len(sys.argv) != 4):
        sys.stderr.write(f"Usage: {sys.argv[0]} startdate enddate JWT\n")
        sys.stderr.write('\nDates must be in the format YYYY-MM-DD. Omit leading zeros.\n')
        sys.exit(1)

    startdate = datetime.date(*map(int, sys.argv[1].split('-')))
    enddate = datetime.date(*map(int, sys.argv[2].split('-')))
    authheader = {'Authorization': f"Bearer {sys.argv[3]}"}

    print(f"# Weight Watchers Tracked Food Report\n\n> {sys.argv[1]} - {sys.argv[2]}\n")

    for date in daterange(startdate, enddate):
        url = f'{ENDPOINT}/{date}'
        response = requests.get(url, headers=authheader)
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




