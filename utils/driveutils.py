import httplib2
from apiclient import discovery
from apiclient.http import MediaFileUpload
from utils import HashableDict



MIMETYPE_FOLDER = 'application/vnd.google-apps.folder'
MIMETYPE_FILE = 'application/vnd.google-apps.document'



def get_drive_service(credentials):
    """ Returns an interface that interacts with Drive.

    Given valid credentials, this will return an interface
    which allows interacting with the clients Drive.

    In:
        credentials = The crendentials needed to access the clients Drive.
    Out:
        service = The interface used to interact with the clients Drive.

    """
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('drive', 'v3', http=http)
    return service

class DriveFileCache:
    """ A cache for Drive files.

    A simple class which gives back requested files ids
    and whether or not they were created in the process.
    This cache only keeps the most recent request, a
    default of 10 at a time, but can be increased. It also
    "re-finds" the file if it's metadata was changed after
    the previous request.

    >>> Future Notes <<<
    Will eventually make it so that instead of just getting 
    the id, any requested metadata would be returned as well.

    Init:
        service = The Drive interface which allows requests.
        cap = The capcity of the cache.
    """
    def __init__(self,service,cap=10):
        self.__service = service
        self.__drivefiles = {}
        self.__order = []
        self.__cap = cap

    def loadFile(self,file_metadata,fields=None):
        """ Returns info requested info on the target file.

        Loads information (right now only the file ID) on the target
        file found from the metadata given. Will load a pre-existing
        cached file if one is loaded or, if not or if the Drive version
        is changed, then will load a new version of the file to the
        cache.

        >>> Future Notes <<<
        Will load in additional information to be stored later, but
        right now will only load in the file ID.

        In:
            file_metadata = The metadata used to find the target file.
        Out:
            target_file = The file found when using file_metadata.
            created = Whether or not the target file was created during.
        """
        #fields is not active, will be at a later date
        target_file,created = (None,False)

        hashable_file_metadata = HashableDict(file_metadata)
        target_file,modified_time = self.__drivefiles[hashable_file_metadata] if hashable_file_metadata in self.__drivefiles else (None,None)
        new_modified_time = None
        if target_file:
            new_modified_time = self.__service.files().get(fileId=target_file,fields='modifiedTime').execute().get('modifiedTime')
        if not target_file or (new_modified_time and new_modified_time != modified_time):
            target_file,created = produce_file(self.__service,file_metadata)
            self.__drivefiles[hashable_file_metadata] = (target_file,new_modified_time)
            self.__order.insert(0,file_metadata)

        if file_metadata in self.__order:
            self.__order.remove(file_metadata)
        elif len(self.__order) == self.__cap:
            cache_kill = self.__order.pop()
            del self.__service[HashableDict(cache_kill)]

        self.__order.insert(0,file_metadata)

        return (target_file,created)

    def __contains__(self,file_metadata):
        """ Checks if the cache has a target file.

        Checks the cache if there is a current file
        loaded under the metadata given.

        """
        hashable_file_metadata = HashableDict(file_metadata)
        return hashable_file_metadata in self.__drivefiles

def construct_querystring(props):
    """ Constructs a query-string for Google Drive queries.

    Uses file metadata to construct a simple query string that
    can be used to query a file based on...
        name: the name of the file
        parents: the parents of the file
        mimeType: the type of the file
        trashed: whether or not the file is in the trash
        appProperties: the private application properties of the file

    >>> Future Note <<<
        This will be expanded into a class which can spawn instances
        with default values to make constructing certain queries more
        stream-line.

    In:
        props = The file metadata used to create query-string.
    Out:
        q = The constructed query-string of the files metadata.
    """
    q = None
    if type(props) is dict:
        q = ''
        trashed_specified = False
        for prop in props:
            q += ' and '
            if prop == 'parents':
                parents = props[prop]
                for parent in parents:
                    q += '"'+str(parent)+'" in '+str(prop)
                    q += ' and '
                q = q[:len(q)-5]
            elif prop == 'trashed':
                q += str(prop)+' = '+str(props[prop])
                trashed_specified = True
            elif prop == 'appProperties':
                appProps = props[prop]
                for appProp in appProps:
                    q += str(prop)+' has { key="'+str(appProp)+'" and value="'+str(appProps[appProp])+'" }'
                    q += ' and '
                q = q[:len(q)-5]
            elif prop == 'name' or prop == 'mimeType':
                q += str(prop)+' = "'+str(props[prop])+'"'
            else:
                q = q[:len(q)-5]
        if not trashed_specified:
            q += ' and trashed = False'
        q = q[5:]
    return q


def find_file(service,file_metadata):
    """ Finds the first file that matches the file metadata.

    Uses query-string constructed from file metadata and then searches
    the clients Drive for the first file that matches the query.

    In:
        service = The interface which allows access to the clients Drive.
        file_metadata = The file metadata that is being used to search for the file.
    Out:
        file_target = The identifier of the file in the clients Drive.
    """
    file_target = None

    q = construct_querystring(file_metadata)
    if q:
        results = service.files().list(pageSize=1, q=q, fields='files(id)').execute().get('files')
        if len(results) == 1:
            file_target = str(results[0]['id'])

    return file_target

def produce_file(service,file_metadata,file_metadata_template=None):
    """ Produces a file based on file metadata, that may optionally take 
        form from a template file.

    Either finds an existing file, or generates a new one based off a template
    file, using file metadata. If a template metadata is specified, then a new
    file is created either by using an existing one on the clients Drive or by
    uploading a copy of local file, and then written with the file metadata. If
    no template is specified, but the file is a folder, then a new folder is
    created with the file_metadata. Otherwise, the file is just searched for.

    In:
        service = The interface which allows access to the clients Drive.
        file_metadata = The file metadata used to produce the file.
        file_metadata_template = The template files metadata used to locate the template. (Optional)
    Out:
        file_target = The indentifier of the file produced.
        created = Whether or not the file was created in the process.
    """
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

def cascade_file(service,file_metadata,folder_target,folder_stop):
    """ Finds a path between a child folder and its parent who has a file it
        wants; and then, creates a copy for each node along the path.

    Searches for a file matching file metadata starting from folder target and looks up
    each parent until reaching a folder along the parent-child line (stop_folder) which
    it then exits. If the file is found, the nodes in the current generated path between
    the target folder and its closest containing parent are populated with a copy of the
    target file.

    In:
        service = The interface which allows access to the clients Drive.
        file_metadata = The file metadata of the file being searched for and copied.
        folder_target = The folder which the target file is meant for.
        folder_stop = The folder which the search is stopped at.
    Out:
        file_target = The identifier of the file cascaded into the target folder.
    """
    file_target = None

    file_template = None
    folder_targets = []

    current_folder = folder_target
    while not file_template:
        file_metadata['parents'] = [ current_folder ]
        file_template = find_file(service,file_metadata)
        folder_targets.insert(0,current_folder)

        if not file_template and current_folder == folder_stop:
            print ('CASCADE_FILE ERROR: Can not find template file in folder parent structure')
            raise

        current_folder_parents = service.files().get(fileId=current_folder,fields='parents').execute().get('parents')
        current_folder = current_folder_parents[0] if current_folder_parents else None
    folder_targets.pop(0)

    for folder_target in folder_targets:
        file_metadata['parents'] = [ folder_target ]
        file_target = str(service.files().copy(fileId=file_template,body=file_metadata,fields='id').execute().get('id'))

    del file_metadata['parents']

    return file_target
