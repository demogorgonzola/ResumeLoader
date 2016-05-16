import os
import argparse

from oauth2client.file import Storage
from oauth2client import client
from oauth2client import tools



argparser = argparse.ArgumentParser(parents=[tools.argparser],add_help=False)

def get_credentials(flags,client_secret_path,scopes,storage_path):
    """ Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    if not os.path.exists(storage_path):
        os.makedirs(storage_path)
    storage_path = os.path.join(storage_path,'tokens.json')

    storage = Storage(storage_path)
    credentials = storage.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(client_secret_path,scopes)
        credentials = tools.run_flow(flow, storage, flags)
        print('Storing credentials to ' + storage_path)
    return credentials