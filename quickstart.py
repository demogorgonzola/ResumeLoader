
from __future__ import print_function
import httplib2
import os

from apiclient import discovery
import oauth2client
from oauth2client import client
from oauth2client import tools

'''
try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None
'''

import sys
flags = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/drive-python-quickstart.json
SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/drive.metadata.readonly']
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'ResumeLoader'


def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'drive-python-quickstart.json')

    store = oauth2client.file.Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials


def find_folder(service,q):
    results = service.files().list(
        pageSize=1, q = q, fields="nextPageToken, files(id, name)").execute()
    results = results.get('files',[])
    if len(results) == 1:
        return results[0]
    else:
        return None

def main(argv):
    """Shows basic usage of the Google Drive API.

    Creates a Google Drive API service object and outputs the names and IDs
    for up to 10 files.
    """
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('drive', 'v3', http=http)

    ##

    # find folder Job Applications
    q_ja = "name = 'Job Applications'"
    folder = find_folder(service,q_ja)
    ja_folder_id = folder['id']
    
    print('Job Applications Folder ID: \n\t'+str(ja_folder_id))

    # find the template files Cover Letter and Resume in Job Applications
    q_ja_cvres = "'"+str(ja_folder_id)+"' in parents and (name = 'Cover Letter' or name = 'Resume' or name = 'Description')"
    results = service.files().list(
        pageSize=3, q = q_ja_cvres, fields="nextPageToken, files(id, name)").execute()
    cvres_ids = results.get('files', [])

    print('Template CoverLetter and Resume Ids: \n\t'+str(cvres_ids[0]['id'])+',\n\t'+str(cvres_ids[1]['id']))

    # copy both template files and put the in company folder with new Description file
    company_name = argv[0]
    position_name = argv[1]
    tag = argv[2]

    #find out if company name already exists, if not then create it and store info
    company_folder_id = None
    q_company = "name = '"+company_name+"'"
    folder = find_folder(service,q_company)
    if not folder:
        folder_metadata = {
            'name' : company_name,
            'mimeType' : 'application/vnd.google-apps.folder',
            'parents' : [ ja_folder_id ]
        }
        company_folder_id = service.files().create(body=folder_metadata, fields='id').execute().get('id')
    else:
        company_folder_id = folder['id']
    print('Company Folder ID: '+str(company_folder_id))
    #create copies of template files and move them to new Position folder
    folder_metadata = {
        'name' : position_name,
        'mimeType' : 'application/vnd.google-apps.folder',
        'parents' : [ company_folder_id ],
        'description' : str(argv[2])
    }
    position_folder_id = service.files().create(body=folder_metadata, fields='id').execute().get('id')
    service.files().copy(fileId=cvres_ids[0]['id'],body={'parents' : [str(position_folder_id)]}).execute()
    service.files().copy(fileId=cvres_ids[1]['id'],body={'parents' : [str(position_folder_id)]}).execute()
    service.files().copy(fileId=cvres_ids[2]['id'],body={'parents' : [str(position_folder_id)]}).execute()




if __name__ == '__main__':
    if len(sys.argv) == 4:
        main(sys.argv[1:])
    else:
        print('failed')