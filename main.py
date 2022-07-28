import datetime
from google.cloud import datastore
from flask import Flask, render_template, request
import google.oauth2.id_token
import requests as r
import json
from datetime import datetime, timedelta

app = Flask(__name__)

client = datastore.Client()

# ROUTES ----------------------------------------------------------

@app.route('/')
def root():
	return render_template('index.html')


@app.route('/highlights')
def highlights_page():
	return render_template('highlights_home.html')

@app.route('/highlights/<team_name>')
def team_highlights_page(team_name):
    try: team_info = fetch_team_info(team_name)
    except: return render_template('404.html')
    return render_template('highlights.html', games=json.loads(team_info)[team_name]['schedule'])

@app.errorhandler(404)
def invalid_address(e):
    return render_template('404.html')

# FUNCTIONS ---------------------------------------------------------

def fetch_team_info(team_name):
    key = client.key('team_info',team_name)
    try: entity = client.get(key)
    except: 
        update_team_info(team_name)
        entity = client.get(key)
        return entity[team_name]
    team_info = json.loads(entity[team_name])
    next_game_time = datetime.strptime(team_info[team_name]['schedule'][0]['time'][2:19], '%y-%m-%dT%H:%M:%S') + timedelta(hours = 4)
    if next_game_time < datetime.utcnow(): 
        update_team_info(team_name)
        entity = client.get(key)
    return entity[team_name]
    

def update_team_info(team_name):
	# calls API and pushes to datastore
    team_info = {team_name: {"schedule": [{},{},{}] }}
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
    team_info[team_name]['schedule'][0]['embed_highlights'] = ['game has not started']

    # UPDTATE HIGHLIGHTS
    entity = datastore.Entity(client.key('team_info',team_name))
    entity[team_name] = json.dumps(team_info)
    client.put(entity)

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
    app.run(host='127.0.0.1', port=8080, debug=True)
