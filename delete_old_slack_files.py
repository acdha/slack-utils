"""
Delete old files from Slack

You will be prompted for an API token which will be saved using Keyring to the
Mac, Windows, or Linux desktop secure password stores. Get your API token from
Get a token from https://api.slack.com/custom-integrations/legacy-tokens.
"""

import argparse
import getpass
import sys
from time import time

import keyring
import requests


def get_api_token(username, service_name='https://slack.com/api/'):
    token = keyring.get_password(service_name, username)

    if not token:
        token = getpass.getpass(f'Slack API token for {username}: ')
        keyring.set_password(service_name, username, token)

    return token


def list_files(token, uri='https://slack.com/api/files.list'):
    params = {
        'token': token,
        'count': 1000
    }

    while True:
        response = requests.get(uri, params=params)
        api_response = response.json()

        yield from api_response['files']

        paging = api_response['paging']

        if paging['page'] < paging['pages']:
            params['page'] = paging['page'] + 1
            print(f'Requesting page {params["page"]}')
        else:
            break


def delete_files_by_id(file_ids, token):
    print(f'Deleting {len(file_ids)} files…')

    for file_id in file_ids:
        params = {
            'token': token,
            'file': file_id
        }

        uri = 'https://slack.com/api/files.delete'
        response = requests.get(uri, params=params)
        if not response.ok:
            print(f'Unable to delete {file_id}: {response.status_code} {response.reason}',
                  file=sys.stderr)


def delete_old_files(token, max_age):
    file_ids_to_delete = []

    retained_file_sizes = []

    for i in list_files(token):
        if i['created'] < max_age:
            file_ids_to_delete.append(i['id'])
        else:
            retained_file_sizes.append((i['size'], i['name'], i['permalink']))

    delete_files_by_id(file_ids_to_delete, token=token)

    retained_file_sizes.sort(reverse=True)
    print('Largest remaining files')
    for i in retained_file_sizes[:25]:
        print(*i, sep='\t')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.strip())
    parser.add_argument('--max-age', default=time() - (60 * 86400),
                        help='Max age in seconds (default=%(default)s')
    parser.add_argument('--username', default=getpass.getuser(),
                        help='Slack username (default=%(default)s')

    args = parser.parse_args()

    token = get_api_token(args.username)

    delete_old_files(token, args.max_age)
