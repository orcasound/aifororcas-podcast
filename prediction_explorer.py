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
from collections import OrderedDict
from pathlib import Path

# NOTE: the code here is a little messy as it's a quick-and-dirty hack 
# setting some globals 
STATIC_JSON_DIR = "./static/pred_explorer_tmp/json"
STATIC_WAV_DIR = "./static/pred_explorer_tmp/wav"
args = None
last_served_sessionid = 0
json_map = None 

app = Flask(__name__, static_folder='./static', template_folder='./templates')


# some convenience functions/classes

def load_and_split_tsv(predictions_tsv, wav_dir):
    """
    Converts a TSV file (wav_filename, start_time_s, duration_s) to 
    JSON of { wav_filename:{ "uri": ,"annotations":[], "backend_state":{} } }
    """
    global json_map
    # TODO@Akash: if file too long - break it up 

    # load as dataframe & sort annotations within a wav file by start_time 
    predictions_df = pd.read_csv(predictions_tsv, sep='\t').sort_values(['wav_filename','start_time_s'])
    if "confidence" not in predictions_df:
        print("WARNING: no confidence score provided, will mark everything as 1.0 for display")
        predictions_df["confidence"] = 1.0  

    # get unique wavfilenames 
    wav_filenames = predictions_df['wav_filename'].unique()
    n = len(wav_filenames)
    print("Unique wavfiles:",n)

    # create JSON map of {wav_fname:{session_json}}
    json_map = OrderedDict()
    for i, wav_filename in enumerate(wav_filenames):

        annotations_df = predictions_df[predictions_df["wav_filename"]==wav_filename]

        session_json = {
            "uri": os.path.join(STATIC_WAV_DIR, wav_filename)
            }
        session_json["annotations"] = []
        for j in range(len(annotations_df)):
            row = annotations_df.iloc[j]
            try:
                session_json["annotations"].append(
                        {
                            "start_time_s": row["start_time_s"], 
                            "duration_s": row["duration_s"],
                            "confidence": row["confidence"] 
                        }
                    )
            except Exception as e:
                print(e)
                print(i, j, wav_filename)
                print(row)

        # indicators for the progress bar 
        sessionid = i+1 # 1-indexed for convenience of display 
        session_json["backend_state"] = {"written": sessionid, "remaining": n-sessionid}
        json_map[wav_filename] = session_json

    return json_map


def prepare_session(sessionid):
    global json_map, args 

    # sessionid is 1-indexed
    json_index = sessionid-1
    fname = list(json_map.keys())[json_index]

    os.makedirs(STATIC_JSON_DIR, exist_ok=True)
    os.makedirs(STATIC_WAV_DIR, exist_ok=True)
    static_json_path = "{}/{}.json".format(STATIC_JSON_DIR, sessionid)
    static_wav_path = os.path.join(STATIC_WAV_DIR, fname)

    skipped = True 
    if not os.path.isfile(static_json_path):
        with open(static_json_path, 'w') as f:
            json.dump(json_map[fname], f)
        skipped = False
    if not os.path.isfile(static_wav_path):
        _ = shutil.copyfile(os.path.join(args.wav_dir, fname), static_wav_path)
        skipped = False 
    
    if not skipped:
        print("Prepared session {}, file:{}".format(sessionid, fname))
    else:
        print("Reuse session from /static {}, file:{}".format(sessionid, fname))
   

# api functions 

@app.route('/')
def index():
    """
    The homepage makes two HTTP requests:
    - GET to /fetch/session: fetches an un-annotated sessionid
    - GET to /load/session/sessionid: retrieves a particular JSON containing predictions 
    - GET to STATIC_WAV_DIR/wav file to retrieve audio 
    - POST to /submit/session: does nothing in this case 
    """
    return render_template('prediction_explorer.html')

@app.route('/fetch/session', methods=['GET'])
def fetch_new_session():
    try:
        # return the next sessionid after what was last served 
        global last_served_sessionid
        sessionid = last_served_sessionid+1
        response = dict(sessionid=sessionid)
        return json.dumps(response)
    except Exception as e:
        print(e)
        abort(400)

@app.route('/load/session/<sessionid>', methods=['GET'])
def load_session(sessionid):
    try:
        global last_served_sessionid 

        # prepares the JSON & wav files in the static folder 
        prepare_session(int(sessionid))

        # load session_json to serve 
        with open("./static/pred_explorer_tmp/json/{}.json".format(sessionid)) as f:
            json_content = json.load(f)
        print("Served session:", sessionid)
        last_served_sessionid = int(sessionid)
        return json.dumps(json_content)
    except Exception as e:
        print(e)
        abort(400)



if __name__ == '__main__':
    """
    The Pod.Cast tool is retrofitted to quickly view/listen and explore some model predictions to get a sense of the 
    accuracy & error pattern. 
    The flask app copies over wav files to STATIC_WAV_DIR so that your browswer can access and display them 

    Hence, don't forget to clean up STATIC_JSON_DIR, STATIC_WAV_DIR when done! 
    """

    parser = argparse.ArgumentParser()
    parser.add_argument("predictions_tsv", type=str)
    parser.add_argument("wav_dir", type=str)
    args = parser.parse_args()

    json_map = load_and_split_tsv(args.predictions_tsv, args.wav_dir)
    app.run(debug=True, threaded=True)
