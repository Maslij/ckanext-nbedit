import ckan.plugins.toolkit as toolkit
import requests
import logging

get_or_bust = toolkit.get_or_bust
log = logging.getLogger('ckanext-nbedit')


def start_server(context, data_dict):
    log.debug('action:start_server')
    jhub_api_url = get_or_bust(data_dict, 'jhub_api_url')
    log.debug('jhub_api_url: '+jhub_api_url)
    user_id = get_or_bust(data_dict, 'user_id')
    log.debug('user_id: '+user_id)
    notebook_server_image = get_or_bust(data_dict, 'notebook_server_image')
    log.debug('notebook_server_image: ' + notebook_server_image)
    url = '{}/users/{}/server'.format(jhub_api_url, user_id)
    log.debug('url: ' + url)
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': 'token ' + get_or_bust(data_dict, 'user_token')
    }
    kubespawner_override = {
        'environment': {
            'ACCOUNT_ID': get_or_bust(data_dict, 'account_id'),
            'API_TOKEN': get_or_bust(data_dict, 'ckan_api_token'),
            'AUTHORIZATION_SERVER_URL': get_or_bust(data_dict, 'authorization_server_url'),
            'CONTENT_ID': get_or_bust(data_dict, 'content_id'),
            'INSTANCE_BASE_URL': get_or_bust(data_dict, 'instance_base_url'),
            'INSTANCE_HOST': get_or_bust(data_dict, 'instance_host'),
            'OAUTH_CLIENT_ID': get_or_bust(data_dict, 'oauth_client_id'),
            'REDIS_HOST': get_or_bust(data_dict, 'redis_host'),
            'REDIS_PASSWORD': get_or_bust(data_dict, 'redis_password'),
            'SHARED_SECRET': get_or_bust(data_dict, 'shared_secret'),
            'SPACE_KEY': get_or_bust(data_dict, 'space_key')
        }
    }
    log.debug('status:notebook_image_check')
    if notebook_server_image is not None:
        kubespawner_override.update({ 'image': notebook_server_image })
        
    log.debug('status:notebook_spawn_pre')
    resp = requests.post(url, headers=headers, json={
        'kubespawner_override': kubespawner_override
    })
    log.debug('status:notebook_spawn_post')
    status_code = resp.status_code
    if status_code < 200 or status_code > 299:
        resp.raise_for_status()


def stop_server(context, data_dict):
    log.debug('action:stop_server')
    jhub_api_url = get_or_bust(data_dict, 'jhub_api_url')
    user_id = get_or_bust(data_dict, 'user_id')
    jhub_token = get_or_bust(data_dict, 'jhub_token')
    url = '{}/users/{}/server'.format(jhub_api_url, user_id)
    resp = requests.delete(url, headers=_jhub_headers(jhub_token))
    status_code = resp.status_code
    if status_code < 200 or status_code > 299:
        resp.raise_for_status()


@toolkit.side_effect_free
def jhub_user_exists_and_server_running(context, data_dict):
    log.debug('action:jhub_user_exists_and_server_running')
    jhub_api_url = get_or_bust(data_dict, 'jhub_api_url')
    user_id = get_or_bust(data_dict, 'user_id')
    jhub_token = get_or_bust(data_dict, 'jhub_token')
    url = '{}/users/{}'.format(jhub_api_url, user_id)
    resp = requests.get(url, headers=_jhub_headers(jhub_token))
    status_code = resp.status_code
    if status_code < 200 or status_code > 299:
        return (False, False)

    try:
        jhub_user = resp.json()
    except ValueError as err:
        log.error('JSON Decode Error: ' + str(err))
        log.error('response: ' + (resp.text if resp else 'None'))
        return (False, False)

    if not type(jhub_user) is dict:
        return (False, False)

    return (
        True if jhub_user['name'] else False,  # user_exists
        True if jhub_user['server'] else False # server_is_running
    )


def create_jhub_group(context, data_dict):
    log.debug('action:create_jhub_group')
    jhub_api_url = get_or_bust(data_dict, 'jhub_api_url')
    group_id = get_or_bust(data_dict, 'group_id')
    jhub_token = get_or_bust(data_dict, 'jhub_token')
    url = '{}/groups/{}'.format(jhub_api_url, group_id)
    resp = requests.post(url, headers=_jhub_headers(jhub_token))
    status_code = resp.status_code
    if status_code < 200 or status_code > 299:
        resp.raise_for_status()


def create_jhub_user(context, data_dict):
    log.debug('action:create_jhub_user')
    jhub_api_url = get_or_bust(data_dict, 'jhub_api_url')
    user_id = get_or_bust(data_dict, 'user_id')
    jhub_token = get_or_bust(data_dict, 'jhub_token')
    url = '{}/users/{}'.format(jhub_api_url, user_id)
    resp = requests.post(url, headers=_jhub_headers(jhub_token))
    status_code = resp.status_code
    if status_code < 200 or status_code > 299:
        resp.raise_for_status()


def add_user_to_group(context, data_dict):
    log.debug('action:add_user_to_group')
    jhub_api_url = get_or_bust(data_dict, 'jhub_api_url')
    group_id = get_or_bust(data_dict, 'group_id')
    user_id = get_or_bust(data_dict, 'user_id')
    jhub_token = get_or_bust(data_dict, 'jhub_token')
    url = '{}/groups/{}/users'.format(jhub_api_url, group_id)
    resp = requests.post(url, headers=_jhub_headers(jhub_token), data={
        'users': [user_id]
    })
    status_code = resp.status_code

    if status_code == 404:
        # group doesn't exist, db out of sync
        # create the group now
        create_jhub_group(context, data_dict)
        # and try again
        add_user_to_group(context, data_dict)

    elif status_code < 200 or status_code > 299:
        resp.raise_for_status()


def create_user_token(context, data_dict):
    log.debug('action:create_user_token')
    jhub_api_url = get_or_bust(data_dict, 'jhub_api_url')
    user_id = get_or_bust(data_dict, 'user_id')
    jhub_token = get_or_bust(data_dict, 'jhub_token')
    jhub_token_expiry_sec = get_or_bust(data_dict, 'jhub_token_expiry_sec')
    url = '{}/users/{}/tokens'.format(jhub_api_url, user_id)
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': 'token ' + jhub_token
    }
    payload = {
        'token_params': {
            'expires_in': jhub_token_expiry_sec,
            'note': 'Requested by ckanext-nbedit via API'
        }
    }
    resp = requests.post(url, headers=headers, json=payload)
    status_code = resp.status_code
    if status_code < 200 or status_code > 299:
        resp.raise_for_status()

    body = resp.json()
    return body['token'] if body else None


def _jhub_headers(jhub_token):
    return {
        'Accept': 'application/json',
        'Authorization': 'token ' + jhub_token
    }
