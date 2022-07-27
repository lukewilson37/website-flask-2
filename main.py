import datetime
from google.cloud import datastore
from flask import Flask, render_template, request
import google.oauth2.id_token
import requests as r
import json

app = Flask(__name__)

datastore_client = datastore.Client()

@app.route('/')
def root():
	# Fetch the most recent 10 access times from Datastore.
	times = update_team_info('Barcelona')

	return render_template('index.html', times=json.loads(times)['Barcelona']['schedule'])


@app.route('/highlights')
def highlights_page():
	times = update_team_info('Barcelona')

	return render_template('index.html', times=json.loads(times)['Barcelona']['schedule'])

def store_time(dt):
    entity = datastore.Entity(key=datastore_client.key('visit'))
    entity.update({
        'timestamp': dt
    })

    datastore_client.put(entity)


def fetch_times(limit):
    query = datastore_client.query(kind='visit')
    query.order = ['-timestamp']

    times = query.fetch(limit=limit)

    return times

def update_team_info(team_name):
	# calls API and pushes to datastore
    team_info = {"Barcelona": {"schedule": [{},{},{}] }}
    url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"
    querystring = {"season":"2022","team":"529","last":2,"timezone":"America/New_York"}
    headers = {
	    "X-RapidAPI-Key": "9f0303d58bmsh4ba4d5e0c9d5e51p17a64ajsnd6ba4f5a2e07",
	    "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
    }
    response = json.loads(r.request("GET", url, headers=headers, params=querystring).text)
    for i in range(2):
        team_info[team_name]['schedule'][1+i]['home'] = response['response'][i]['teams']['home']['name']
        team_info[team_name]['schedule'][1+i]['away'] = response['response'][i]['teams']['away']['name']
        team_info[team_name]['schedule'][1+i]['time'] = response['response'][i]['fixture']['date']
        team_info[team_name]['schedule'][1+i]['embed_highlights'] = return_embed_highlights(\
                                                                  team_info[team_name]['schedule'][1+i]['home'],
                                                                  team_info[team_name]['schedule'][1+i]['away'])
    querystring = {"season":"2022","team":"529","next":1,"timezone":"America/New_York"}
    response = json.loads(r.request("GET", url, headers=headers, params=querystring).text)
    team_info[team_name]['schedule'][0]['home'] = response['response'][0]['teams']['home']['name']
    team_info[team_name]['schedule'][0]['away'] = response['response'][0]['teams']['away']['name']
    team_info[team_name]['schedule'][0]['time'] = response['response'][0]['fixture']['date']
    
    # UPDTATE HIGHLIGHTS
    return json.dumps(team_info)

def return_embed_highlights(home,away):

    url = "https://free-football-soccer-videos.p.rapidapi.com/"
    headers = {
	    "X-RapidAPI-Key": "9f0303d58bmsh4ba4d5e0c9d5e51p17a64ajsnd6ba4f5a2e07",
	    "X-RapidAPI-Host": "free-football-soccer-videos.p.rapidapi.com"
    }
    response = r.request("GET", url, headers=headers)
    for game in json.loads(response.text):
        if ((game['side1']['name'] in home or home in game['side1']['name']) or\
            (game['side2']['name'] in home or home in game['side2']['name'])) and\
            ((game['side1']['name'] in away or away in game['side1']['name']) or\
            (game['side2']['name'] in away or away in game['side2']['name'])):
            for video in game['videos']:
                if video['title'] == 'Highlights':
                    return video['embed']
            return "No highlights yet"
    return "cannot find game"
    
if __name__ == '__main__':
    # This is used when running locally only. When deploying to Google App
    # Engine, a webserver process such as Gunicorn will serve the app. This
    # can be configured by adding an `entrypoint` to app.yaml.
    # Flask's development server will automatically serve static files in
    # the "static" directory. See:
    # http://flask.pocoo.org/docs/1.0/quickstart/#static-files. Once deployed,
    # App Engine itself will serve those files as configured in app.yaml.
    app.run(host='127.0.0.1', port=8080, debug=True)
