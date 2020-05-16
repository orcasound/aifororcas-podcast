#!flask/bin/python
from flask import Flask, jsonify
from flask import abort
from flask import request
from flask import render_template
# from flask_httpauth import HTTPBasicAuth
# auth = HTTPBasicAuth()
from azure.storage.blob import BlockBlobService
import json
import tempfile, random
from collections import deque

app = Flask(__name__, static_folder='./static', template_folder='./templates')

# NOTE: this file is only for demonstration as you don't have blob account credentials 
accountName = 'PLACEHOLDER'
accountKey = 'PLACEHOLDER'
getCallContainerName = 'orcasoundlabpreds'
postCallContainerName = 'dummydata'

toServe = set()
served = set()
written = set()
blob_count = 0

def ends_with_json(s):
    if s.endswith('.json'):
        return True
    return False

def get_blob_json_listings(containerName):
    block_blob_service = BlockBlobService(account_name=accountName,
                                          account_key=accountKey)
    generator = block_blob_service.list_blobs(containerName)
    tmp_list = [x.name for x in generator]

    return set(filter(ends_with_json, tmp_list))

def get_blob(file_name):
    block_blob_service = BlockBlobService(account_name=accountName,
                                          account_key=accountKey)
    json_data = block_blob_service.get_blob_to_text(getCallContainerName, file_name)
    return json_data.content

def clear_globals():
    global toServe
    toServe = set()
    global served
    served = set()
    global written
    written = set()
    global blob_count
    blob_count = 0

def get_blob_data():
    #Get listings from blob
    #Pick one that has not been served
    written, remaining = set(), set()

    # scan blob container on every request
    # randomly choose a candidate not already written to postCallContainer
    written = get_blob_json_listings(postCallContainerName)
    candidates = get_blob_json_listings(getCallContainerName)
    remaining = list(candidates-written)

    if len(remaining)==0:
        raise Exception('Finished! No more data to annotate')
    else:
        chosen_file = random.choice(remaining)

    return (chosen_file,get_blob(chosen_file)), (written,remaining)

def write_blob_data(file_name, content):
    try:
        block_blob_service = BlockBlobService(account_name=accountName,
                                              account_key=accountKey)
        block_blob_service.create_blob_from_text(postCallContainerName, file_name, content)
        tmp = tempfile.NamedTemporaryFile()
        block_blob_service.get_blob_to_stream(postCallContainerName, file_name, tmp)
        return 201
    except:
        return 400


@app.route('/')
def index():
    """
    The homepage makes two HTTP requests:
    - GET to /load/session : fetch a new JSON containing predictions 
    - POST to /submit/annotation : save passed JSON to blob location 
    """
    return render_template('index.html')


@app.route('/load/session', methods=['GET'])
def load_session():
    try:
        # state is maintained on the blob itself
        # NOTE: there is a chance that concurrent requests are served the same file
        (fn,content), (written,remaining) = get_blob_data()
        json_content = json.loads(content)
        # for debugging purposes
        json_content["backend_state"] = {}
        json_content["backend_state"]["written"] = len(written)
        json_content["backend_state"]["remaining"] = len(remaining)
        print("AFTER:","remaining",len(remaining),"written",len(written))

        return json.dumps(json_content)
    except Exception as e:
        print(e)
        abort(400)


@app.route('/submit/annotation', methods=['POST'])
def submit_annotation():
    # NOTE: there's a small chance the file may be overwritten
    # if with concurrent GET requests, the same session is served to different users
    # most recently written version is kept
    # assume that Azure Blob can handle concurrent write requests for the same file 

    if not request.json:
        abort(400)
    uri = request.json.get('uri')
    val = uri.split('/')[-1].split('.')[0]
    fname = val + '.json'
    status = write_blob_data(fname, json.dumps(request.json))

    if status >= 300:
        abort(500)
    else:
        return jsonify({'task': fname}), 201


if __name__ == '__main__':
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
    app.run(debug=True, threaded=True)
