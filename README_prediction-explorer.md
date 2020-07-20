# Pod.Cast 🎱 🐋 | Prediction explorer  

This is a simple flask-based web-application meant to be run locally to quickly visualize/listen to some audio files & view predictions from your model to get an idea of it's performance & error pattern. 

## How to use 

1. Install python prerequisites 
2. Run `python prediction_explorer.py PREDICTIONS.tsv WAV_DIR`
    - `PREDICTIONS.tsv` has columns `(start_time_s, duration_s, confidence, wav_filename)` 
    - `WAV_DIR` is the directory containing the wavfiles in the TSV  
3. Follow instruction on the page, and see comments in py file for more info. 

## Example 

To run an example, you could simply use one of the Pod.Cast test sets. (these are already in the above format)

You can download it using [AWS CLI](https://github.com/orcasound/orcadata/wiki/Data-access-via-AWS-CLI) with:

```
aws --no-sign-request s3 cp s3://acoustic-sandbox/labeled-data/detection/test/OrcasoundLab09272017_Test.tar.gz [DESTINATION]
```

[Extract](https://github.com/orcasound/orcadata/wiki/Pod.Cast-data-archive#DataFormat) the archive and point the script to the files as in step 2. above. 
