#!/usr/bin/env python3
"""
Parse a record collection in CSV format and upload it to a user's Discogs collection
"""
import argparse
import csv
import sys
import time

import requests

TOKEN_FILE = './.api_token'
API_HOST = 'https://api.discogs.com'
DB_API = API_HOST + '/database'
USERS_API = API_HOST + '/users'

def authenticate(username):
    """
    Authenticates all requests with the Discogs API. Expects a personal access token in TOKEN_FILE.

    Arguments:
    username (str) - Discogs username (used in the User-Agent string for each request)

    Returns:
    session (requests.Session) - Authenticated session object to be used for API calls
    """
    try:
        with open(TOKEN_FILE) as token_file:
            token = token_file.readline().strip()
    except Exception as err:
        print(f'Failed to read access token from .api_token: {err}')
        sys.exit(1)
    session = requests.Session()
    session.headers.update({'Authorization': f'Discogs token={token}',
                            'User-Agent': f'{username}/discogs_import'})
    return session

def search(session, **kwargs):
    """
    Searches the Discogs API for a release object

    Arguments:
    session (requests.Session) - API session object
    **kwargs (dict) - All kwargs are added as query parameters in the search call

    Returns:
    dict - The first result returned in the search

    Raises:
    Exception if release cannot be found
    """
    try:
        url = DB_API + '/search?'
        for param, value in kwargs.items():
            url += f'{param}={value}&'
        res = session.get(url)
        data = res.json()
        if res.status_code != 200 or 'results' not in data.keys():
            raise Exception(f'Unexpected error when querying Discogs API ({res.status_code})')
        if not data['results']:
            raise Exception('No results found')
        return data['results'][0]
    except Exception as err:
        print(f'Failed to find release for search {kwargs} in Discogs database: {err}')
        raise

def get_csv_collection(filename, **kwargs):
    """
    Loads a record collection from a CSV file. The CSV file MUST include columns for
    Artist, Title, and Year

    Arguments:
    filename (str) - CSV filename
    **kwargs (dict) - Optional kwargs: skip=0, don't load the first <skip> rows

    Returns:
    list - List of record dicts
    """
    skip = kwargs.get('skip', 0)
    collection = []
    with open(filename, newline='') as collection_file:
        collection_dict = csv.DictReader(collection_file)
        count = 1
        for record in collection_dict:
            if count <= skip:
                count += 1
                continue
            collection.append({'artist': record['Artist'], 'release_title': record['Title'],
                               'year': record['Year'], 'type': 'release', 'country': 'US'})
            count += 1
    return collection

def update_discogs_collection(session, username, collection, **kwargs):
    """
    Updates a user's Discogs collection with all releases provided. Calls are automatically
    rate limited based on Discog's rate limit policy.

    Arguments:
    session (requests.Session) - API session object
    username (str) - Discogs username
    collection (list) - List of record dicts
    **kwargs (dict) - Optional kwargs: limit=0, only update the first <limit> records

    Raises:
    Exception if the API does not return a 201 for an update
    """
    limit = kwargs.get('limit', 0)
    url = f'{USERS_API}/{username}/collection/folders/1/releases/' # folder 1 = "Uncategorized"
    count = 1
    for record in collection:
        try:
            release = search(session, **record)
        except Exception:
            count += 1
            continue
        title = release['title']
        print(f'Adding {title} to collection...', end='')
        res = session.post(url + str(release['id']))
        if res.status_code != 201:
            raise Exception(f'Failed to add {title} to collection: {res.status_code}')
        print('Done!')
        if count == limit:
            break
        count += 1
        # check rate limit
        remaining_calls = res.headers.get('X-Discogs-Ratelimit-Remaining', 0)
        if int(remaining_calls) < 5:
            print('Discogs API rate limit reached. Pausing for 60 seconds...')
            time.sleep(60)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Parse a record collection in CSV format and ' + \
                                     'upload it to a user\'s Discogs collection')
    parser.add_argument('username', help='Discogs username')
    parser.add_argument('filename', help='Collection file in CSV format. ' + \
                        'The file must contain the following fields: Artist, Title, Year')
    parser.add_argument('--limit', '-l', metavar='NUM', type=int, default=0,
                        help='Limit operations to the first NUM operations (default: 0/unlimited)')
    parser.add_argument('--skip', '-s', metavar='NUM', type=int, default=0,
                        help='Skip operations for the first NUM rows (default: 0/unlimited)')
    args = parser.parse_args()
    collection = get_csv_collection(args.filename, skip=args.skip)
    if not collection:
        print('Unable to find any records in {args.filename}!')
        sys.exit(1)
    session = authenticate(args.username)
    update_discogs_collection(session, args.username, collection, limit=args.limit)
