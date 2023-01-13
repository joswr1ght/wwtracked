#!/usr/bin/env python3

import sys
import datetime
import requests
import json
import csv
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
    for n in range(int((date2 - date1).days) + 1):
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


"""
Takes the food entry passed to it and calculates the nutrition of the 
food entry by matching the serving type of the entry to the nutritional
data from WW and multiplying by the entry serving size. Returns dict of data  
"""
def getfoodentrynutrition(foodentry):
    if foodentry['sourceType'] != 'MEMBERFOODQUICK':  # ignore quick add items
        data = {'name': foodentry['name'], 'id': foodentry['_id'], 'entryId': foodentry['entryId'],
                'trackedDate': foodentry['trackedDate'], 'timeOfDay': foodentry['timeOfDay'],
                'sourceType': foodentry['sourceType'], 'portionName': "", 'portionSize': foodentry['portionSize'],
                'calories': 0, 'fat': 0, 'saturatedFat': 0, 'sodium': 0, 'carbs': 0, 'fiber': 0, 'sugar': 0,
                'addedSugar': 0, 'protein': 0}

        # Different types of entries have different API endpoints
        urlprefix = {"WWFOOD": "https://cmx.weightwatchers.com/api/v3/public/foods/",
                     "MEMBERFOOD": "https://cmx.weightwatchers.com/api/v3/cmx/members/~/custom-foods/foods/",
                     "WWVENDORFOOD": "https://cmx.weightwatchers.com/api/v3/public/foods/",
                     "MEMBERRECIPE": "https://cmx.weightwatchers.com/api/v3/cmx/members/~/custom-foods/recipes/",
                     "WWRECIPE": "https://cmx.weightwatchers.com/api/v3/public/recipes/"}

        entryurl = f'{urlprefix[foodentry["sourceType"]]}{foodentry["_id"]}?fullDetails=true'

        # Recipes must be handled differently
        if "RECIPE" in foodentry["sourceType"]:
            recipe = True
            data['portionName'] = 'serving(s)'
            foodnutrition = requests.get(entryurl, headers=authheader).json()
        else:
            recipe = False
            data['portionName'] = foodentry['portionName']
            foodnutrition = requests.get(entryurl, headers=authheader).json()['portions']

        size = data["portionSize"]  # portion size applies to both recipes and non-recipe entries

        while True and not recipe:
            for nutrition in foodnutrition:
                # match entry serving type (oz, g, cups, etc) to correct nutritional data type from WW API
                if nutrition['name'] == foodentry["portionName"]:
                    data["calories"] = round(nutrition['nutrition']['calories'] / nutrition['size'] * size)
                    data["fat"] = round(nutrition['nutrition']['fat'] / nutrition['size'] * size, 1)
                    data["saturatedFat"] = round(nutrition['nutrition']['saturatedFat'] / nutrition['size'] * size, 1)
                    data["sodium"] = round(nutrition['nutrition']['sodium'] / nutrition['size'] * size, 1)
                    data["carbs"] = round(nutrition['nutrition']['carbs'] / nutrition['size'] * size, 1)
                    data["fiber"] = round(nutrition['nutrition']['fiber'] / nutrition['size'] * size, 1)
                    data["sugar"] = round(nutrition['nutrition']['sugar'] / nutrition['size'] * size, 1)
                    data["addedSugar"] = round(nutrition['nutrition']['addedSugar'] / nutrition['size'] * size, 1)
                    data["protein"] = round(nutrition['nutrition']['protein'] / nutrition['size'] * size, 1)
                    break
            break  # in case for some reason there is no match

        if recipe:
            def ingredientnutrition(x): return ingredient['itemDetail']['portions'][0]['nutrition'][x] / \
                                            ingredient['itemDetail']['portions'][0]['size'] * ingredient['quantity'] / \
                                            foodnutrition['servingSize'] * size

            for ingredient in foodnutrition['ingredients']:
                data["calories"] += round(ingredientnutrition('calories'))
                data["fat"] += round(ingredientnutrition('fat'), 1)
                data["saturatedFat"] += round(ingredientnutrition('saturatedFat'), 1)
                data["sodium"] += round(ingredientnutrition('sodium'), 1)
                data["carbs"] += round(ingredientnutrition('carbs'), 1)
                data["fiber"] += round(ingredientnutrition('fiber'), 1)
                data["sugar"] += round(ingredientnutrition('sugar'), 1)
                data["addedSugar"] += round(ingredientnutrition('addedSugar'), 1)
                data["protein"] += round(ingredientnutrition('protein'), 1)

        return data


"""
Takes the array of food nutrition dictionaries and writes to CSV  
"""
def writenutritiondata(nutritionarr):
    fields = ['Date', 'When', 'Food', 'Calories', 'Fat', 'Saturated Fat', 'Sodium', 'Carbohydrates', 'Fiber', 'Sugars',
              'Added Sugar', 'Protein']

    filename = f'Nutrition Data {sys.argv[1]} to {sys.argv[2]}.csv'

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
    if (len(sys.argv) < 4 or len(sys.argv) > 5):
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

    if len(sys.argv) == 5 and (sys.argv[4] == '--nutrition' or sys.argv[4] == '-n'):
        requestnutrition = True
        nutritionarr = []
    else:
        requestnutrition = False

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

    if requestnutrition:
        writenutritiondata(nutritionarr)
