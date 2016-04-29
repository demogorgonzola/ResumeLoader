
from __future__ import print_function
import httplib2
import os
import sys

from apiclient import discovery
import oauth2client
from oauth2client import client
from oauth2client import tools

#Future: Migrate from Drive v2 to v3


# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/drive-python-quickstart.json
SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/drive.metadata.readonly']
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'ResumeLoader'


def get_credentials(flags):
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    working_dir = os.getcwd() #might not work on mac
    credential_dir = os.path.join(working_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'credentials-ResumeLoader.json')

    store = oauth2client.file.Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        flags = None
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

#Future: Identify if the query produces only 1 result, if it does then construct a
#           folder that adopts all characteristics of the query
'''
def produce_folder(service,name,q):
    results = service.files().list(
        pageSize=1, q = q, fields="nextPageToken, files(id, name)").execute()
    results = results.get('files',[])
    if len(results) == 0:
        return results[0]
    else:
        return None
'''

MIMETYPE_FOLDER = 'application/vnd.google-apps.folder'
MIMETYPE_FILE = 'application/vnd.google-apps.file'

FOLDER_NAME_JOBAPPLICATIONS = "Job Applications"
FILE_NAME_RESUME = "Resume"
FILE_NAME_COVERLETTER = "CoverLetter"

def retrieve_folder_JobApplications(service):
    # find folder Job Applications
    query_folder_jobapplications = \
        'name = "'+FOLDER_NAME_JOBAPPLICATIONS+'" and ' + \
        'mimeType = "'+MIMETYPE_FOLDER+'"'
    folder = find_folder(service,query_folder_jobapplications)
    if not folder:
        folder_metadata = {
            'name' : FOLDER_NAME_JOBAPPLICATIONS,
            'mimeType' : MIMETYPE_FOLDER
        }
        folder = service.files().create(body=folder_metadata, fields='id').execute().get('id')
    else:
        folder = folder['id']

    folder_jobapplications = str(folder)

    return folder_jobapplications

def retrieve_files_templates(service,folder_jobapplications):
    # find the template files Cover Letter and Resume in Job Applications
    query_files_templates = \
        '"'+folder_jobapplications+'" in parents and ' + \
        '(name = "'+FILE_NAME_RESUME+'" or ' + \
        'name = "'+FILE_NAME_COVERLETTER+'")'
    files = service.files().list(
        pageSize=2, q=query_files_templates, fields="files(id, name)").execute()
    files_templates = files.get('files', [])

    file_resume = None
    file_coverletter = None
    if files_templates[0]['name'] == FILE_NAME_RESUME:
        file_resume = files_templates[0]['id']
        file_coverletter = files_templates[1]['id']
    else:
        file_resume = files_templates[1]['id']
        file_coverletter = files_templates[0]['id']

    file_resume = str(file_resume)
    file_coverletter = str(file_coverletter)

    return {'resume':file_resume,'coverletter':file_coverletter}



def main(flags,company_name,position_name,description):

    #pre-amble
    #   * grab credentials and construct the service 
    credentials = get_credentials(flags)
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('drive', 'v3', http=http)

    ##

    folder_jobapplications = retrieve_folder_JobApplications(service)
    print('Job Applications Folder: \n\t'+folder_jobapplications)

    files_templates = retrieve_files_templates(service,folder_jobapplications)
    print('Template CoverLetter and Resume Ids: \n\t'+files_templates['resume']+'\n\t'+files_templates['coverletter'])

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



import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser(parents=[tools.argparser])
    parser.add_argument('--cname',required=True)
    parser.add_argument('--pname',required=True)
    parser.add_argument('--desc')

    flags = parser.parse_args()
    company_name = flags.cname
    position_name = flags.pname
    description = flags.desc

    main(flags,company_name,position_name,description)