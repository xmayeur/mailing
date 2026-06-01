import logging
import os
import socket
import urllib.parse
from os import getenv
from os.path import join

import requests
import urllib3
import yaml
from certifi import where

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p')

_config = None
_home = None


def get_home():
    """
    Determines the home directory of the current user based on the operating system.

    This function checks the operating system and retrieves the appropriate
    environment variable that represents the user's home directory. For Windows,
    it uses the `USERPROFILE` environment variable. For other operating systems,
    it uses the `HOME` environment variable.

    :return: The path to the user's home directory as a string, or None if it
        cannot be determined.
    :rtype: Optional[str]
    """
    return getenv("USERPROFILE") if os.name == 'nt' else getenv("HOME")


def get_config():
    """
    Parses and loads the Vault configuration file based on the operating system.

    This function determines the correct location of the Vault configuration file
    depending on the operating system being used. It attempts to load the file's
    contents into a dictionary. If the configuration file is not found, it logs an
    error and falls back to a default location, creating the directory if necessary.
    If the configuration is successfully loaded, the configuration file path is
    added to the resulting dictionary.

    :return: A dictionary containing the Vault configuration data, or None if no
             configuration file is found.
    :rtype: dict or None
    """
    global _config, _home
    _config = {}
    if os.name == 'nt':
        _config_file = "vault.yml"
    else:
        _config_file = ".config/.vault/vault.yml"

    _home = get_home() if _home is None else _home
    try:
        _config = yaml.safe_load(open(join(_home, _config_file)))
    except (FileNotFoundError, TypeError):
        if os.name == 'nt':
            logging.error("No vault configuration found in %s", _home)
            _config = None
        if not os.path.exists("/etc/vault"):
            os.makedirs("/etc/vault")
        _home = "/etc/vault"
        _config_file = "vault.yml"
        try:
            _config = yaml.safe_load(open(join(_home, _config_file)))
        except FileNotFoundError:
            logging.error(f"No vault configuration found in {_home}")
            _config = None
    finally:
        if _config:
            _config['config_file'] = _config_file
    return _config


def get_certs(base_url):
    """
    Retrieve the certificate bundle file path for a given base URL.

    This function determines the proper certificate bundle file to use, based on the
    provided base URL and the system's configuration. If no valid certificate bundle
    is found, the function disables certificate verification and issues a warning
    about insecure work.

    :param base_url: A string representing the base URL for which the certificate
        bundle is to be resolved.
    :return: The file path to the certificate bundle if found and valid; otherwise,
        `False` if no valid certificate bundle is available and insecure connections
        are allowed.
    """
    global _config, _home
    _config = get_config() if _config is None else _config
    _home = get_home() if _home is None else _home
    if _home == '/etc/vault':
        certs = '/etc/vault/bundle.pem'
    else:
        certs = join(_home, _config['vault']['certs'].replace("~/", ''))
    parsed_url = urllib.parse.urlparse(base_url)
    hostname = parsed_url.netloc.split(':')[0]
    ip = socket.gethostbyname(hostname)
    if '192.168.' not in ip:
        certs = where()
    # check if file exist, else make insecure
    if not (os.path.exists(certs)):
        certs = False
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        logging.warning(f"No vault bundle.pem found at {certs} - working insecure !!")
    return certs


def get_secret(id: str, repo: str = 'secret') -> dict:
    """
    Fetches a secret from a secure vault based on the provided ID and repository name. If the secret
    exists in the internal configuration cache, it is retrieved directly; otherwise, a request is
    sent to the vault endpoint to fetch the secret.

    :param id: Unique identifier for the secret to be retrieved.
    :type id: str
    :param repo: Name of the repository to search for the secret in. Defaults to 'secret'.
    :type repo: str, optional
    :return: A dictionary containing the retrieved secret data. Returns an empty dictionary if the
        request fails or the secret is not found.
    :rtype: dict
    """
    # check if data is available in config file
    global _config
    _config = get_config() if _config is None else _config
    if id in _config:
        return _config[id]
    else:
        base_url = _config['vault']['vault_addr']

        certs = get_certs(base_url)
        token = _config['vault']['token']
        headers = {"X-Vault-Token": token}
        uri = f"/v1/{repo}/data/"
        url = f"{base_url}{uri}{id}"
        resp = requests.get(url, headers=headers, verify=certs)
        if resp.status_code == 200:
            secret = resp.json()["data"]["data"]
            return secret

        else:
            print(f"http error {resp.status_code}")
            logging.error(f"Vault api error {resp}")
            return {}


def get_user_pwd(id: str, repo: str = 'secret') -> tuple:
    """
    Retrieve the username and password associated with a given `id`. The function
    first checks if the credentials are available in a local configuration. If not,
    it communicates with a Vault server to fetch the credentials. The credentials
    are expected to be stored as `username` and `password`.

    :param id: Identifier used to locate stored credentials.
    :type id: str
    :param repo: Name of the repository where the credentials are stored in the
        Vault server. Defaults to 'secret'.
    :type repo: str, optional
    :return: A tuple containing the username and password. If the credentials
        are not found or if an error occurs, returns a tuple of two `None` values.
    :rtype: tuple
    """
    # check if data is available in config file
    global _config
    _config = get_config() if _config is None else _config
    if id in _config:
        return _config[id]['username'], _config[id]['password']
    else:
        base_url = _config['vault']['vault_addr']
        certs = get_certs(base_url)
        token = _config['vault']['token']

        headers = {"X-Vault-Token": token}
        uri = f"/v1/{repo}/data/"
        url = f"{base_url}{uri}{id}"
        resp = requests.get(url, headers=headers, verify=certs)
        if resp.status_code == 200:
            secret = resp.json()["data"]["data"]
            if 'username' in secret and 'password' in secret:
                return secret['username'], secret['password']
            else:
                return None, None

        else:
            print(f"http error {resp.status_code}")
            logging.error(f"Vault api error {resp}")
            return None, None


def list_secret(repo: str = 'secret'):
    """
    Lists the secret keys from a configured Vault repository.

    This function connects to a Vault service, fetches the metadata for the
    specified secret repository, and extracts the secret keys listed. If the
    response is successful, it returns the list of secret keys. Otherwise, it logs
    an error and returns None.

    :param repo: The name of the secret repository from which keys are to
                 be listed. Defaults to 'secret'.
    :type repo: str
    :return: A list of secret keys if the API call is successful, otherwise
             returns None.
    :rtype: list or None
    """
    global _config
    _config = get_config() if _config is None else _config
    base_url = _config['vault']['vault_addr']
    certs = get_certs(base_url)
    token = _config['vault']['token']

    headers = {"X-Vault-Token": token}
    uri = f"/v1/{repo}/metadata"
    url = f"{base_url}{uri}"
    resp = requests.request('LIST', url, headers=headers, verify=certs)
    if resp.status_code == 200:
        return resp.json()["data"]["keys"]

    else:
        print(f"http error {resp.status_code}")
        logging.error(f"Vault api error {resp}")
        return None, None


def upd_secret(id: str, data, repo: str = 'secret'):
    """
    Updates a secret with the given `id` and `data` either in the local configuration file
    or in the defined secret repository (e.g., Vault). If the secret exists in the local
    configuration, it updates and persists the changes locally. Otherwise, it interacts
    with the Vault API to update the secret remotely based on the provided repository.

    :param id: The identifier for the secret to be updated.
    :type id: str
    :param data: The new data to be stored for the secret.
    :param repo: The name of the repository or secret storage to use. Defaults to 'secret'.
    :type repo: str
    :return: HTTP status code (e.g., 200) if the update was successful, or `None` on
             failure.
    :rtype: int or None
    """
    global _config
    _config = get_config() if _config is None else _config
    _home = get_home()
    # check if data is available in config file
    if id in _config:
        _config[id] = data
        with open(join(_home, _config["config_file"]), 'w') as fd:
            yaml.safe_dump(_config, fd)
        return 200

    else:
        base_url = _config['vault']['vault_addr']
        certs = get_certs(base_url)
        token = _config['vault']['token']

        headers = {"X-Vault-Token": token}
        uri = f"/v1/{repo}/data/"
        url = f"{base_url}{uri}{id}"
        resp = requests.request('GET', url, headers=headers, verify=certs)
        if resp.status_code == 200:
            version = resp.json()["data"]['metadata']['version']
            obj = {
                "options": {
                    "cas": version
                },
                "data": data
            }

            resp2 = requests.request('POST', url, headers=headers, json=obj, verify=certs)
            if resp2.status_code != 200:
                logging.warning(f"Vault update error for {id} with new {data}")
            return resp2.status_code

        else:
            print(f"http error {resp.status_code}")
            logging.error(f"Vault api error {resp}")
            return None, None

