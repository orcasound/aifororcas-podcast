# Pod.Cast annotation system 

This is a simple flask-based web-application that loads audio & model predictions from an Azure blob, and writes back submitted annotations to a different blob container. For a modification of this code, to make it easier to explore/debug model predictions see `prediction_explorer`. 

## Running locally

Set the environment variable `FLASK_APP=podcast_server.py`. 

Then, from this directory start the server with `python -m flask run`, and browse to the link in the terminal (e.g. `http://127.0.0.1:5000/`) in your browser (Edge and Chrome are tested). 

## How to use

The system is currently setup to view and annotate unlabelled master tapes from the WHOIS dataset. See 1:22 at [hackbox page](https://garagehackbox.azurewebsites.net/hackathons/1857/projects/82146) video for how to use. 
You can continue to reload the page to get new sessions from the classifier. But if you submit, do make sure you do your diligence with the annotations as we haven't setup any user differentiation yet :) 
A heads up, you might find this process quite addicting as there's always newer sessions that are loaded! 

## Next up 

We plan to hook this up to recent streams from OrcaSound, to both get a sense of the classifier's performance and help improve it in live conditions. If you want to try a different classifier, for now,  let us know. Eventually we're hoping to make it easier to try your own. 
