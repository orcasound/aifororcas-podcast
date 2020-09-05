#!flask/bin/python
from flask import Flask, jsonify
from flask import abort
from flask import request, redirect
from flask import render_template
# from flask_httpauth import HTTPBasicAuth
# auth = HTTPBasicAuth()
from azure.storage.blob import BlockBlobService
import yaml
import json
import tempfile, random

CREDS_FILE = "CREDS.yaml"

app = Flask(__name__, static_folder='./static', template_folder='./templates')

# some convenience functions/classes

def dict_to_str(d):
    """Pretty print contents of a dict, with fixed width as [KEY] : [VALUE]"""
    return "\n".join(["{0: <25}: {1}".format(k,v) for k,v in d.items()])

class YAMLConfig:
    def __init__(self, yaml_file):
        with open(yaml_file, 'r') as f: yaml_dict = yaml.load(f, Loader=yaml.BaseLoader)
        for k, v in yaml_dict.items():
            setattr(self, k, v)
    
    def __repr__(self):
        return dict_to_str(self.__dict__)

def ends_with_json(s):
    if s.endswith('.json'): return True
    return False

# core functions  

def list_blob_sessionids(containerName):
    """Returns available sessionids in a blob container by listing JSON files"""
    block_blob_service = BlockBlobService(account_name=creds.blobaccount,
                                          account_key=creds.blobaccountkey)
    generator = block_blob_service.list_blobs(containerName)
    # e.g. returns [11, 22] for available json files [11.json, 22.json]
    return [ x.name.rsplit(".",1)[0] for x in generator if ends_with_json(x.name) ]

def get_session_json(roundid, sessionid):
    file_name = "{}.json".format(sessionid)
    """Retrieves a session JSON for annotation UI"""
    getcontainer = "{}-{}".format(creds.getcontainer, roundid)
    block_blob_service = BlockBlobService(account_name=creds.blobaccount,
                                          account_key=creds.blobaccountkey)
    json_data = block_blob_service.get_blob_to_text(getcontainer, file_name)
    return json_data.content

def get_unannotated_session(roundid):
    """Find un-annotated sessions, pick one that not been served"""
    # {sessionid: _, backend_state:{written: _, remaining: _} }
    global backend_state

    getcontainer = "{}-{}".format(creds.getcontainer, roundid)
    postcontainer = "{}-{}".format(creds.postcontainer, roundid)

    # scan blob container on request
    written = set(list_blob_sessionids(postcontainer))
    candidates = set(list_blob_sessionids(getcontainer))
    remaining = list(candidates-written)
    # update backend state
    backend_state['written'] = len(written)
    backend_state['remaining'] = len(remaining)

    # choose candidate at random from those not already written to postcontainer  
    if len(remaining)==0:
        print('Finished! No more data to annotate, choosing any session at random.')
        sessionid = random.choice(list(candidates))
    else:
        sessionid = random.choice(remaining)
    
    return dict(sessionid=sessionid)
    
def write_blob_data(roundid, file_name, content):
    global backend_state
    postcontainer = "{}-{}".format(creds.postcontainer, roundid)
    try:
        block_blob_service = BlockBlobService(account_name=creds.blobaccount,
                                              account_key=creds.blobaccountkey)
        block_blob_service.create_blob_from_text(postcontainer, file_name, content)
        tmp = tempfile.NamedTemporaryFile()
        block_blob_service.get_blob_to_stream(postcontainer, file_name, tmp)
        backend_state['written'] += 1
        backend_state['remaining'] -= 1
        return 201
    except:
        return 400

# api functions 

@app.route('/')
def index():
    """
    The front-end makes these HTTP requests:
    - GET to /fetch/session: fetches an un-annotated sessionid
    - GET to /load/session/sessionid : retrieves a particular JSON containing predictions 
    - GET to Azure blob to retrieve wav file for playback & computing spectrogram 
    - POST to /submit/session : save passed JSON to blob location 
    """
    return redirect("round4", code=303)

@app.route('/<roundid>')
def index_with_roundid(roundid):
    # simply dummy as all logic is in the client
    return render_template('index.html')

@app.route('/fetch/session', methods=['GET'])
def fetch_new_session():
    try:
        # state is maintained on the blob itself
        # HACK: if concurrent requests are served the same random file, annotation is overwritten  
        response = get_unannotated_session()
        return json.dumps(response)
    except Exception as e:
        print(e)
        abort(400)

@app.route('/fetch/session/<roundid>', methods=['GET'])
def fetch_new_session_with_roundid(roundid):
    try:
        # state is maintained on the blob itself
        # HACK: if concurrent requests are served the same random file, annotation is overwritten  
        response = get_unannotated_session(roundid)
        return json.dumps(response)
    except Exception as e:
        print(e)
        abort(400)

@app.route('/load/session/<roundid>/<sessionid>', methods=['GET'])
def load_session(roundid, sessionid):
    global backend_state
    try:
        response = json.loads(get_session_json(roundid, sessionid))
        response["backend_state"] = backend_state
        print("Served round: {}, session: {}".format(roundid, sessionid))
        return json.dumps(response)
    except Exception as e:
        print("Error in loading session:",e)
        abort(400)

@app.route('/submit/session/<roundid>/<sessionid>', methods=['POST'])
def submit_annotation(roundid, sessionid):
    # NOTE: there's a small chance the file may be overwritten
    # if with concurrent GET requests, the same session is served to different users
    # most recently written version is kept
    # assume that Azure Blob can handle concurrent write requests for the same file 

    if not request.json:
        abort(400)
    # uri = request.json.get('uri')
    # val = uri.split('/')[-1].split('.')[0]
    fname = sessionid + '.json'
    status = write_blob_data(roundid, fname, json.dumps(request.json))

    if status >= 300:
        abort(500)
    else:
        return jsonify({'task': fname}), 201


"""
Stateless application:
1. On a GET request, scan preds and annotations containers and randomly return one to annotate
# NOTE: there is a chance that concurrent requests are served the same file
2. On POST request, simply attempt to write to the annotations container
# NOTE: there is a chance that a file is overwritten due to concurrent GET requests
# assume that Azure Blob can handle concurrent write requests for the same file 
# most recently written version is kept

The earlier attempt to maintain state had bugs due to multithreading. See:
https://stackoverflow.com/questions/32815451/are-global-variables-thread-safe-in-flask-how-do-i-share-data-between-requests
"""
# initialize app globals 

# create credentials object from YAML file 
creds = YAMLConfig(CREDS_FILE) # NOTE: the file in the repo contains dummy data 
# global variable maintained for the progress bar 
backend_state = {}
get_unannotated_session("round4") # just to initialize backend_state  
