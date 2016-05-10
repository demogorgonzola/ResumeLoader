from __future__ import print_function
import httplib2
import os

from apiclient import discovery
from apiclient.http import MediaFileUpload
import oauth2client
from oauth2client import client
from oauth2client import tools



# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/drive-python-quickstart.json
SCOPES = ['https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/drive.metadata']
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


#currently works with:
#   * name
#   * parent (one parent)
#   * mimeType
#   * trashed (default: false)
def construct_querystring(props):
    q = None
    if type(props) is dict:
        q = ''
        trashed_specified = False
        for prop in props:
            q += ' and '
            if prop == 'parents':
                q += '"'+str(props[prop][0])+'" in '+str(prop)
            elif prop == 'trashed':
                q += str(prop)+' = '+str(props[prop])
                trashed_specified = True
            elif prop == 'name' or prop == 'mimeType':
                q += str(prop)+' = "'+str(props[prop])+'"'
            else:
                q = q[:len(q)-5]
        if not trashed_specified:
            q += ' and trashed = False'
        q = q[5:]
    return q


def find_file(service,file_metadata):
    file_target = None

    q = construct_querystring(file_metadata)
    if q:
        results = service.files().list(pageSize=1, q=q, fields='files(id)').execute().get('files')
        if len(results) == 1:
            file_target = str(results[0]['id'])

    return file_target


#produce a file that matches file_metadata (search)
#   create the file if file_metadata_template is specified or there isn't a result and the file_metadata is a folder
def produce_file(service,file_metadata,file_metadata_template=None):
    file_target = None
    created = False

    if file_metadata_template:
        file_template = find_file(service,file_metadata_template)
        if file_template:
            file_target = str(service.files().copy(fileId=file_template,body=file_metadata,fields='id').execute().get('id'))
        else:
            try:
                file_upload = MediaFileUpload(file_metadata_template)
                file_target = str(service.files().create(body=file_metadata, media_body=file_upload, fields='id').execute().get('id'))
            except Error:
                print('Could not find template: '+str(file_metadata_template))
                raise
        created = True
    else:
        file_target = find_file(service,file_metadata)
    if not file_target and file_metadata['mimeType'] == MIMETYPE_FOLDER:
        file_target = str(service.files().create(body=file_metadata, fields='id').execute().get('id'))
        created = True

    return (file_target,created)

#Find a file matching file_metadata from the folders heiarchy
#of the folder_target (id) and copy that file from the closest
#avaiable parent to the folder_target
# In:   file_metadata = target file descriptor that is to be cascaded
#       folder_taret = target folder to be reached by the end of the cascade
# Out:  file_target = the id of the copy of the target file in folder_target
def cascade_file(service,file_metadata,folder_target):
    file_target = None

    file_template = None
    folder_targets = []

    current_folder = folder_target
    while not file_template and current_folder:
        print(file_template)
        print(current_folder)
        file_metadata['parents'] = [ current_folder ]
        file_template = find_file(service,file_metadata)
        folder_targets.insert(0,current_folder)
        current_folder = service.files().get(fileId=current_folder,fields='parents').execute().get('parents')
        if current_folder:
            current_folder = current_folder[0]
    if not current_folder:
        print ('CASCADE_FILE ERROR: Can not find template file in folder parent structure')
        raise
    folder_targets.pop(0)

    for folder_target in folder_targets:
        file_metadata['parents'] = [ folder_target ]
        file_target = str(service.files().copy(fileId=file_template,body=file_metadata,fields='id').execute().get('id'))

    del file_metadata['parents']

    return file_target



MIMETYPE_FOLDER = 'application/vnd.google-apps.folder'
MIMETYPE_FILE = 'application/vnd.google-apps.document'

FOLDER_NAME_JOBAPPLICATIONS = "Job Applications"
FILE_NAME_RESUME = "Resume"
FILE_NAME_COVERLETTER = "Cover Letter"

def main(flags,company_name,position_name,description):

    #pre-amble
    #   * grab credentials and construct the service 
    credentials = get_credentials(flags)
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('drive', 'v3', http=http)

    ##

    folder_metadata_jobapplications = {
        'name' : FOLDER_NAME_JOBAPPLICATIONS,
        'mimeType' : MIMETYPE_FOLDER,
    }
    folder_jobapplications,created = produce_file(service,folder_metadata_jobapplications)
    print('Job Applications Folder: \n\t'+folder_jobapplications)

    folder_metadata_company = {
        'name' : company_name,
        'mimeType' : MIMETYPE_FOLDER,
        'parents' : [ folder_jobapplications ],
        'appProperties' : { 'tag' : 'company' },
    }
    folder_company,created = produce_file(service,folder_metadata_company)
    print('Company Folder: '+folder_company)

    folder_metadata_position = {
        'name' : position_name,
        'mimeType' : MIMETYPE_FOLDER,
        'parents' : [ folder_company ],
        'appProperties' : { 'tag' : 'position' },
    }
    folder_position,created = produce_file(service,folder_metadata_position)
    if not created:
        print('Error: Position already exists!!!')
        raise
    print('Position Folder: '+folder_position)

    ##

    file_metadata_resume = {
        'name' : FILE_NAME_RESUME,
        'mimeType' : MIMETYPE_FILE,
    }
    file_template_resume = cascade_file(service,file_metadata_resume,folder_position)


    file_metadata_coverletter = {
        'name' : FILE_NAME_COVERLETTER,
        'mimeType' : MIMETYPE_FILE,
    }
    file_template_coverletter = cascade_file(service,file_metadata_coverletter,folder_position)

    file_metadata_description = {
        'name' : 'Description',
        'mimeType' : MIMETYPE_FILE,
        'parents' : [ folder_position ],
    }
    file_template_coverletter = produce_file(service,file_metadata_description,'empty.txt')



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