import driveutils
from driveutils import MIMETYPE_FOLDER,MIMETYPE_FILE
from utils import JSONFormat,Undefined

class JobFileCache:
    """ A simplfied version of DriveFileCache.

    Used to store only companies and positions in a DriveFileCache,
    this class simplifies its use by providing two methods which
    perform that behavior.

    In:
        service = The interface which allows interaction with Drive.
    """
    FOLDER_METADATA_JOBAPPLICATIONS = {
        'name' : 'Job Applications',
        'mimeType' : MIMETYPE_FOLDER,
    }

    FOLDER_METADATA_COMPANY_FORMAT = JSONFormat( {
        'name': Undefined('name'),
        'mimeType' : MIMETYPE_FOLDER,
        'parents': Undefined('parents'),
        'appProperties' : { 'tag' : 'company', },
    })

    FOLDER_METADATA_POSITION_FORMAT = JSONFormat( {
        'name': Undefined('name'),
        'mimeType' : MIMETYPE_FOLDER,
        'parents' : Undefined('parents'),
        'appProperties' : { 'tag' : 'position', 'actual_name': Undefined('name'), },
        'description' : Undefined('description'),
    })

    def __init__(self,service):
        self.__drivecache = driveutils.DriveFileCache(service)
        self.__namecache = {}

    def loadJobApplications(self):
        """ Loads the Job Application Folder into cache.

        This must be executed first to allow loadCompany and
        loadPosition to perform. It can be circumvented by
        making the load_req flags in either to be True.

        Out:
            folder_jobapplications = The identifier of the Job Applications folder.
            created = Whether or not the Job Applications folder was created during.
        """
        return self.__drivecache.loadFile(self.FOLDER_METADATA_JOBAPPLICATIONS)

    def loadCompany(self,company_name,load_req=False):
        """ Loads the Company Folder into cache.

        Loads the company folder identifier, of the corresponding
        company name, into the file cache. Must have the job Applications
        folder loaded first or set the load_req flag to True.

        In:
            company_name = Name of the company to load into cache.
            load_req (optional) = Whether or not to load its required files first.
        Out:
            folder_company = The identifier of the Company folder.
            created = Whether or not the Company folder was created during.
        """
        folder_metadata_company = self.__namecache[company_name] if company_name in self.__namecache else None
        if not folder_metadata_company:
            if not load_req and self.FOLDER_METADATA_JOBAPPLICATIONS not in self.__drivecache:
                print('ERROR: JobApplications must be loaded first!')
                raise
            folder_jobapplications,created = self.loadJobApplications()
            folder_metadata_company = self.FOLDER_METADATA_COMPANY_FORMAT.spawnInstance({
                'name' : company_name,
                'parents' : [ folder_jobapplications, ],
            })
            self.__namecache[company_name] = folder_metadata_company
        return self.__drivecache.loadFile(folder_metadata_company)

    def loadPosition(self,company_name,position_name,description,load_req=False):
        """ Loads the Position Folder into cache.

        Loads the positon folder identifier, of the corresponding position name
        in the specified company folder, into the file cache. Must have the
        company folder loaded first or set the load_req flag to True.

        In:
            company_name = Name of the company to either be in or loaded into the cache.
            position_name = Name of the position in the company that is to be loaded.
            load_req (optional) = Whether or not to load its required files first.
        Out:
            folder_company = The identifier of the Company folder.
            created = Whether or not the Company folder was created during.
        """
        actual_name = position_name+'-'+company_name        
        folder_metadata_position = self.__namecache[actual_name] if actual_name in self.__namecache else None
        if not folder_metadata_position:
            if not load_req and company_name not in self.__namecache:
                print('ERROR: Company must be loaded first!')
                raise
            folder_company,created = self.loadCompany(company_name)
            folder_metadata_position = self.FOLDER_METADATA_POSITION_FORMAT.spawnInstance({
                'name' : position_name,
                'parents' : [ folder_company, ],
                'appProperties' : { 'tag' : 'position', 'actual_name' : position_name, },
                'description' : description,
            })
            self.__namecache[actual_name] = folder_metadata_position
        return self.__drivecache.loadFile(folder_metadata_position)



FILE_NAME_RESUME = "Resume"
FILE_NAME_COVERLETTER = "Cover Letter"

def stampPosition(service,folder_position):
    """ Appends the creation date to a position.

    Given a position identifier, it will change
    the name of the file to...
        "<name> - <creationTime>"

    In:
        service = The interface used to interact with Drive.
        folder_position = The identifer of the position folder.
    """
    name_and_createdTime = service.files().get(fileId=folder_position,fields='name,createdTime').execute()
    name = str(name_and_createdTime.get('name'))
    createdTime = str(name_and_createdTime.get('createdTime'))
    service.files().update(fileId=folder_position,body={ 'name' : name+' - '+createdTime }).execute()

def createResume(service,folder_target,folder_jobapplications):
    """ Creates a resume in a target folder.

    Creates a resume in a specified target folder, by using the
    cascade_file method to look as far as the job applications folder
    for a local copy to be brought in.

    In:
        service = The interface used to interact with Drive.
        folder_target = The identifier of the target folder for the Resume to be copied to.
        folder_jobapplications = The identifer of the job applicaitons folder.

    """
    file_metadata_resume = {
        'name' : FILE_NAME_RESUME,
        'mimeType' : MIMETYPE_FILE,
    }
    driveutils.cascade_file(service,file_metadata_resume,folder_target,folder_jobapplications)

def createCoverLetter(service,folder_target,folder_jobapplications):
    """ Creates a cover letter in a target folder.

    Creates a cover letter in a specified target folder, by using the
    cascade_file method to look as far as the job applications folder
    for a local copy to be brought in.

    In:
        service = The interface used to interact with Drive.
        folder_target = The identifier of the target folder for the cover letter to be copied to.
        folder_jobapplications = The identifer of the job applicaitons folder.

    """
    file_metadata_coverletter = {
        'name' : FILE_NAME_COVERLETTER,
        'mimeType' : MIMETYPE_FILE,
    }
    driveutils.cascade_file(service,file_metadata_coverletter,folder_target,folder_jobapplications)

def createDescription(service,folder_target,folder_jobapplications):
    """ Creates a description file in a target folder.

    Creates a description filein a specified target folder, by sending
    a blank document with the name "Description"

    In:
        service = The interface used to interact with Drive.
        folder_target = The identifier of the target folder for the Description file to be sent.
        folder_jobapplications = The identifer of the job applicaitons folder.

    """
    file_metadata_description = {
        'name' : 'Description',
        'mimeType' : MIMETYPE_FILE,
        'parents' : [ folder_target ],
    }
    driveutils.produce_file(service,file_metadata_description,'empty.txt')