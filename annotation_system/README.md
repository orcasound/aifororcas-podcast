# Pod.Cast annotation system 

## Overview 

This is a prototype flask-based web-app to label unlabelled Orcasound data in live conditions, while viewing predictions from a model. 

As seen below, this has been used in an active learning style, where an initial model (when tuned for high recall) filters out candidates from unlabelled Orcasound archives that are then refined by human listeners. Each round generates new labelled data that improves models trained on this data, making them more robust to varied acoustic conditions at different hydrophone nodes. Held-out test sets are also created in a similar fashion as accuracy and robustness benchmarks. 

<!-- ![Flowchart of feedback loop between model & human listeners](./doc/podcast-activelearning-flowchart.png) -->

<img src="doc/podcast-activelearning-flowchart.png" width="70%">

## Architecture  

This prototype is a [single page application](https://en.wikipedia.org/wiki/Single-page_application#JavaScript_frameworks) with a simple flask backend that interfaces with Azure blob storage. 
For simplicity/ease of access, this version doubles up use of blob storage as a *sort of database*. A JSON file acts as a single entry, and separate containers as *sort of tables/collections* (this hack should eventually be fixed with a  database). 

<img src="doc/podcast-arch-diagram.png" width="100%">

The API consists of the following: 

> GET /fetch/session

Scans the blob container for an unlabelled session, randomly picks & returns a sessionid. The sessionid is simply the name of the corresponding JSON file & if you see, gets appended to the URL. 

> GET /load/session/sessionid
>
> GET Azure blob wav

Fetches the corresponding JSON file from the blob container. 

> POST /submit/session




# Use & setup  

## Setup & local debugging  

Create an isolate python environment, and `pip install --upgrade pip && pip install -r requirements.txt`. 
(Python 3.6.8 has been tested, though more recent versions should also work as dependencies are quite simple)

Set the environment variable `FLASK_APP=podcast_server.py`. 

Then, from this directory start the server with `python -m flask run`, and browse to the link in the terminal (e.g. `http://127.0.0.1:5000/`) in your browser (Edge and Chrome are tested). 

> Note that when you run this locally, you will still be writing to the actual blob storage, so be careful. 

For a modification of this code, to make it easier to explore/debug model predictions on some local wav files, see `prediction_explorer`. 


## Next up 

If you submit, do make sure you do your diligence with the annotations as we haven't setup any user differentiation yet :) 
A heads up, you might find this process quite addicting as there's always newer sessions that are loaded! 

We plan to hook this up to recent streams from OrcaSound, to both get a sense of the classifier's performance and help improve it in live conditions. If you want to try a different classifier, for now,  let us know. Eventually we're hoping to make it easier to try your own. 
