var fs = require('fs')
var readline = require('readline')
var events = require('events')
var google = require('googleapis')
var googleAuth = require('google-auth-library')

// If modifying these scopes, delete your previously saved credentials
// at ~/.credentials/drive-nodejs-quickstart.json
var SCOPES = ['https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/drive.metadata']
var TOKEN_DIR = process.env.PWD + '/.credentials/'
var TOKEN_PATH = TOKEN_DIR + 'credentials-ResumeLoader.json'

// Load client secrets from a local file.
fs.readFile('client_secret.json', function processClientSecrets(err, content) {
  if (err) {
    console.log('Error loading client secret file: ' + err)
    return
  }
  // Authorize a client with the loaded credentials, then call the
  // Drive API.
  authorize(JSON.parse(content), main)
})

/**
 * Create an OAuth2 client with the given credentials, and then execute the
 * given callback function.
 *
 * @param {Object} credentials The authorization client credentials.
 * @param {function} callback The callback to call with the authorized client.
 */
function authorize(credentials, callback) {
  var clientSecret = credentials.installed.client_secret
  var clientId = credentials.installed.client_id
  var redirectUrl = credentials.installed.redirect_uris[0]
  var auth = new googleAuth()
  var oauth2Client = new auth.OAuth2(clientId, clientSecret, redirectUrl)

  // Check if we have previously stored a token.
  fs.readFile(TOKEN_PATH, function(err, token) {
    if (err) {
      getNewToken(oauth2Client, callback)
    } else {
      oauth2Client.credentials = JSON.parse(token)
      callback(oauth2Client)
    }
  })
}

/**
 * Get and store new token after prompting for user authorization, and then
 * execute the given callback with the authorized OAuth2 client.
 *
 * @param {google.auth.OAuth2} oauth2Client The OAuth2 client to get token for.
 * @param {getEventsCallback} callback The callback to call with the authorized
 *     client.
 */
function getNewToken(oauth2Client, callback) {
  var authUrl = oauth2Client.generateAuthUrl({
    access_type: 'offline',
    scope: SCOPES
  })
  console.log('Authorize this app by visiting this url: ', authUrl)
  var rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
  })
  rl.question('Enter the code from that page here: ', function(code) {
    rl.close()
    oauth2Client.getToken(code, function(err, token) {
      if (err) {
        console.log('Error while trying to retrieve access token', err)
        return
      }
      oauth2Client.credentials = token
      storeToken(token)
      callback(oauth2Client)
    })
  })
}

/**
 * Store token to disk be used in later program executions.
 *
 * @param {Object} token The token to store to disk.
 */
function storeToken(token) {
  try {
    fs.mkdirSync(TOKEN_DIR)
  } catch (err) {
    if (err.code != 'EEXIST') {
      throw err
    }
  }
  fs.writeFile(TOKEN_PATH, JSON.stringify(token))
  console.log('Token stored to ' + TOKEN_PATH)
}

////////////////////

var MIMETYPE_FOLDER = 'application/vnd.google-apps.folder'
var MIMETYPE_FILE = 'application/vnd.google-apps.document'



function construct_querystring(props) {
  var q = null
  if ( typeof props == 'object' ) {
    if ( typeof props['trashed'] === 'undefined' ) {
      props['trashed'] = false
    }
    q = ''
    var trashed_specified = false
    for ( var prop in props ) {
      q += ' and '
      if ( prop == 'parents' ) {
        q += '"'+String(props[prop][0])+'" in '+String(prop)
      } else if ( prop == 'trashed' ) {
        q += String(prop)+' = '+String(props[prop])
      } else if ( prop == 'name' || prop == 'mimeType' ) {
        q += String(prop)+' = "'+String(props[prop])+'"'
      } else {
        q = q.slice(0,q.length-5)
      }
    }
    q = q.slice(5,q.length)
  }
  return q
}

function find_file(service,auth,file_metadata,callback) {
  upfunc = function(err, response) {
    if (err) {
      console.log('FIND_FILE: The API returned an error: ' + err)
      return
    }
    var files = response.files
    if (files.length == 1) {
      callback(String(files[0]['id']))
    } else {
      callback(null)
    }
  }

  var q = construct_querystring(file_metadata)
  if ( q != null )  {
    results = service.files.list( {
      auth: auth,
      pageSize: 1,
      q: q,
      fields: 'files(id)'
    }, upfunc)
  } else {
    callback(null)
  }
}


//START TRANSLATING AGAIN HERE!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

//produce a file that matches file_metadata (search)
//   create the file if file_metadata_template is specified or there isn't a result and the file_metadata is a folder
function produce_file(service,auth,file_metadata,file_metadata_template,callback) {
  if (typeof callback === 'undefined') {
    callback = file_metadata_template
    file_metadata_template = null
  }

  var file_target = null
  var created = false

  id_callback = function(err,response) {
    if (err) {
      console.log('PRODUCE_CALLBACK: The API returned an error: ' + err)
      return
    }
    var file_target = String(response.id)
    var created = true
    callback(file_target,created)
  }
  if ( file_metadata_template != null ) {
    findfile_callback = function(file_template) {
      if ( file_template  ) {
        service.files.copy( {
          auth: auth,
          fileId: file_template,
          resource: file_metadata,
          fields: 'name,id'
        }, id_callback)
      } else {
        service.files.create( {
          auth: auth,
          resource: file_metadata,
          media: fs.createReadStream(file_metadata_template),
          fields: 'id'
        }, id_callback)
      }
    }
    find_file(service,auth,file_metadata_template,findfile_callback)
  } else {
    findfile_callback = function(file_target) {
      if ( !file_target && file_metadata['mimeType'] == MIMETYPE_FOLDER ) {
        service.files.create( {
          auth: auth,
          resource: file_metadata,
          fields: 'id'
        }, id_callback)
      } else {
        callback(file_target,false)
      }
    }
    find_file(service,auth,file_metadata,findfile_callback)
  }
}

function parseArgs(n) {
  var sorted = {}

  if ( (process.argv.length-2)/2 != n ) {
    throw 'INCORRECT NUMBER OF ARGS!!!'
  }
  try {
    var args = process.argv
    for (i=2 ; i < args.length ; i+=2) {
      sorted[args[i]] = args[i+1] 
    }
  } catch (err) {
    throw 'ARGS ARE INCORRECT!!!'
  }

  return sorted
}


var FOLDER_NAME_JOBAPPLICATIONS = "Job Applications"
var FILE_NAME_RESUME = "Resume"
var FILE_NAME_COVERLETTER = "Cover Letter"

function main(auth) {
  args = parseArgs(2)
  //

  var eventEmitter = new events.EventEmitter()
  var START = 'start'
  var SUCCESS_FINDJOBAPPLICATIONS = 'success_findjobapplications'
  var SUCCESS_FINDCOMPANY = 'success_findcompany'
  var SUCCESS_FINDPOSITION = 'success_findposition'

  //////////

  var service = google.drive('v3')

  var folder_jobapplications = null
  var folder_company = null
  var folder_position = null

  var company_name = args['--cname']
  var position_name = args['--pname']

  //

  find_jobapplications = function() {
    folder_metadata_jobapplications = {
      'name' : FOLDER_NAME_JOBAPPLICATIONS,
      'mimeType' : MIMETYPE_FOLDER,
    }
    callback = function(file_target,created) {
      folder_jobapplications = file_target
      process.stdout.write('Job Applications Folder: \n\t'+folder_jobapplications+'\n')
      eventEmitter.emit(SUCCESS_FINDJOBAPPLICATIONS)
    }
    produce_file(service,auth,folder_metadata_jobapplications,callback)
  }

  find_company = function() {
    folder_metadata_company = {
      'name' : company_name,
      'mimeType' : MIMETYPE_FOLDER,
      'parents' : [ folder_jobapplications ],
      'properties' : { ResumeLoaderTag: 'company' },
    }
    callback = function(file_target,created) {
      folder_company = file_target
      process.stdout.write('Company Folder: \n\t'+folder_company+'\n')
      eventEmitter.emit(SUCCESS_FINDCOMPANY)
    }
    produce_file(service,auth,folder_metadata_company,callback)
  }

  find_position = function() {
    folder_metadata_position = {
      'name' : position_name,
      'mimeType' : MIMETYPE_FOLDER,
      'parents' : [ folder_company ],
      'properties' : { ResumeLoaderTag: 'position' },
    }
    callback = function(file_target,created) {
      if ( !created ) {
        process.stdout.write('Error: Position already exists!!!')
        throw null
      }
      folder_position = file_target
      process.stdout.write('Position Folder: \n\t'+folder_position+'\n')
      eventEmitter.emit(SUCCESS_FINDPOSITION)
    }
    produce_file(service,auth,folder_metadata_position,callback)
  }

  //

  create_resume = function() {
    file_metadata_resume = {
      'name' : FILE_NAME_RESUME,
      'mimeType' : MIMETYPE_FILE,
      'parents' : [ folder_position ],
    }
    file_metadata_template_resume = {
      'name' : FILE_NAME_RESUME,
      'mimeType' : MIMETYPE_FILE,
      'parents' : [ folder_jobapplications ],
    }
    callback = function(file_target,created) {
      file_resume = file_target
      process.stdout.write('Resume File: \n\t'+file_resume+'\n')
    }
    produce_file(service,auth,file_metadata_resume,file_metadata_template_resume,callback)
  }

  create_coverletter = function(callback) {
    var file_metadata_coverletter = {
      'name' : FILE_NAME_COVERLETTER,
      'mimeType' : MIMETYPE_FILE,
      'parents' : [ folder_position ],
    }
    var file_metadata_template_coverletter = {
      'name' : FILE_NAME_COVERLETTER,
      'mimeType' : MIMETYPE_FILE,
      'parents' : [ folder_jobapplications ],
    }
    callback = function(file_target,created) {
      var file_coverletter = file_target
      process.stdout.write('Cover Letter File: \n\t'+file_coverletter+'\n')
    }
    produce_file(service,auth,file_metadata_coverletter,file_metadata_template_coverletter,callback)
  }

  create_description = function(callback) {
    file_metadata_description = {
      'name' : 'Description',
      'mimeType' : MIMETYPE_FILE,
      'parents' : [ folder_position ],
    }
    callback = function(file_target,created) {
      var file_description = file_target
      process.stdout.write('Description File: \n\t'+file_description+'\n')
    }
    produce_file(service,auth,file_metadata_description,'empty.txt',callback)
  }

  //////////

  eventEmitter.on(START, find_jobapplications)
              .on(SUCCESS_FINDJOBAPPLICATIONS,find_company)
              .on(SUCCESS_FINDCOMPANY,find_position)
              .on(SUCCESS_FINDPOSITION,create_resume)
              .on(SUCCESS_FINDPOSITION,create_coverletter)
              .on(SUCCESS_FINDPOSITION,create_description)
  eventEmitter.emit(START)
}