#!flask/bin/python
from flask import Flask, jsonify
from flask import abort
from flask import request
from flask import render_template, redirect
import json, os
import tempfile, random
import argparse
import pandas as pd
import shutil
from collections import deque
from pathlib import Path

import pdb

app = Flask(__name__, static_folder='./static', template_folder='./templates')
args = None


def ends_with_json(s):
    if s.endswith('.json'):
        return True
    return False


@app.route('/')
def index():
    """
    The homepage makes two HTTP requests:
    - GET to /load/session : fetch a new JSON containing predictions 
    - POST to /submit/annotation : save passed JSON to blob location 
    """
    return redirect("/1")


@app.route('/<int:file_index>')
def view_file_index(file_index):
    global args
    file_index -= 1 # using 1-based index for UI
    json_map = load_and_split_tsv(args.predictions_tsv, args.wav_dir)

    # randomly choose and dump JSON
    fname = list(json_map.keys())[file_index]
    with open("./static/json/session.json", 'w') as f:
        json.dump(json_map[fname], f)
    _ = shutil.copyfile(os.path.join(args.wav_dir, fname), os.path.join("./static/wav", fname))

    return render_template('index.html')


@app.route('/load/session', methods=['GET'])
def load_session():
    try:
        # /load/session, then load at random 
        # /load/filenumber/<filenumber> load this one 
        with open("./static/json/session.json") as f:
            json_content = json.load(f)
        return json.dumps(json_content)
    except Exception as e:
        print(e)
        abort(400)


# @app.route('/submit/annotation', methods=['POST'])
# def submit_annotation():
#     # NOTE: there's a small chance the file may be overwritten
#     # if with concurrent GET requests, the same session is served to different users
#     # most recently written version is kept
#     # assume that Azure Blob can handle concurrent write requests for the same file 

#     if not request.json:
#         abort(400)
#     uri = request.json.get('uri')
#     val = uri.split('/')[-1].split('.')[0]
#     fname = val + '.json'
#     status = write_blob_data(fname, json.dumps(request.json))

#     if status >= 300:
#         abort(500)
#     else:
#         return jsonify({'task': fname}), 201
    

def load_and_split_tsv(predictions_tsv, wav_dir):
    # load as dataframe & sort  
    # get unique wavfilenames 
    # create JSON map, and {filename:index} map
    # JSON: uri, annotations, backend_state 
    # TODO@Akash: if file too long - break it up 
    predictions_df = pd.read_csv(predictions_tsv, sep='\t').sort_values(['wav_filename','start_time_s'])
    wav_filenames = predictions_df['wav_filename'].unique()
    n = len(wav_filenames)
    print("Unique wavfiles:",n)

    json_map = {}
    for i, wav_filename in enumerate(wav_filenames):
        annotations_df = predictions_df[predictions_df["wav_filename"]==wav_filename]
        session = {"uri": os.path.join("./static/wav", wav_filename) }
        session["annotations"] = []
        for j in range(len(annotations_df)):
            row = annotations_df.iloc[j]
            try:
                session["annotations"].append(
                    {"start_time_s": row["start_time_s"], "duration_s": row["duration_s"]}
                    )
            except Exception as e:
                print(e)
                print(i, j, wav_filename)
                print(row)
        session["backend_state"] = {"written": i+1, "remaining": n-(i+1)}
        json_map[wav_filename] = session
    return json_map

"""
Input: TSV file (wav_filename, start_time_s, duration_s)
f(TSV) -> json list 
"""

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

    parser = argparse.ArgumentParser()
    parser.add_argument("predictions_tsv", type=str)
    parser.add_argument("wav_dir", type=str)
    args = parser.parse_args()

    app.run(debug=True, threaded=True)

