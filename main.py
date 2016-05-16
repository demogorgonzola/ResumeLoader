import argparse

import auth
from utils import driveutils
from utils.jobutils import JobFileCache,createResume,createCoverLetter,createDescription,stampPosition



APPLICATION_NAME = 'ResumeLoader'

CLIENT_SECRET_PATH = 'auth/client_secret.json'
CREDENTIALS_PATH = 'auth/.credentials'

SCOPES = ['https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/drive.metadata']



def createPosition(service,company_name,position_name,description):
    job_files = JobFileCache(service)
    j_id,created = job_files.loadJobApplications()
    c_id,created = job_files.loadCompany(company_name)
    p_id,created = job_files.loadPosition(company_name,position_name,description)
    ###
    if not created:
        stampPosition(service,p_id)
        p_id,created = job_files.loadPosition(company_name,position_name,description)
    ###
    createResume(service,p_id,j_id)
    createCoverLetter(service,p_id,j_id)
    createDescription(service,p_id,j_id)

def createCompany(service,company_name):
    job_files = JobFileCache(service)
    j_id,created = job_files.loadJobApplications()
    c_id,created = job_files.loadCompany(company_name)
    ##
    if created:
        createResume(service,c_id,j_id)
        createCoverLetter(service,c_id,j_id)
    else:
        print('Company already created! Exiting...')

######################

def main(flags,company_name,position_name,description):
    credentials = auth.get_credentials(flags,CLIENT_SECRET_PATH,SCOPES,CREDENTIALS_PATH)
    service = driveutils.get_drive_service(credentials)

    if position_name:
        createPosition(service,company_name,position_name,description)
    else:
        createCompany(service,company_name)

######################

import time

if __name__ == '__main__':
    parser = argparse.ArgumentParser(parents=[auth.argparser])
    parser.add_argument('--cname',required=True)
    parser.add_argument('--pname')
    parser.add_argument('--desc')

    flags = parser.parse_args()
    company_name = flags.cname
    position_name = flags.pname
    description = flags.desc

    start = time.time()
    main(flags,company_name,position_name,description)
    end = time.time()
    total_time = end-start
    print(str(total_time)+'s')