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
    query = client.query(kind='league_teams')
    leagues = query.fetch()
    return render_template('highlights_home.html', leagues=leagues)

@app.route('/highlights/<league_name>')
def league_highlights_page(league_name):
    try: team_list = client.get(client.key('league_teams',league_name))
    except: return render_template('404.html')
    return render_template('highlights_league_home.html',team_list=team_list)

@app.route('/highlights/<league_name>/<team_name>')
def team_highlights_page(league_name, team_name):
    if team_name not in client.get(client.key('league_teams',league_name))[league_name]: abort(404)
    try: team_info = fetch_team_info(team_name)
    except: return render_template('404.html')
    return render_template('highlights.html', team_name=team_name,  games=json.loads(team_info)[team_name]['schedule'])

@app.errorhandler(404)
def invalid_address(e):
    return render_template('404.html')

# FUNCTIONS ---------------------------------------------------------

def fetch_team_info(team_name):
    key = client.key('team_info',team_name)
    try: 
        entity = client.get(key)
        team_info = json.loads(entity[team_name])
        next_game_time = datetime.strptime(team_info[team_name]['schedule'][0]['time'][2:19], '%y-%m-%dT%H:%M:%S') + timedelta(hours = 4)
        if next_game_time < datetime.utcnow(): 
            raise Exception()
        for i in range(2):
            if team_info[team_name]['schedule'][i]['embeded_highlights'][0] != '<': raise Exception()
        return entity[team_name]
    except: 
        update_team_info(team_name)
        entity = client.get(key)
        return entity[team_name]
    

def update_team_info(team_name):
    # calls API and pushes to datastore
    team_info = {team_name: {"schedule": [{},{},{}] }}
    url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"
    api_football_team_id = client.get(client.key('api_football_team_id',team_name))
    querystring = {"season":"2022","team":api_football_team_id[team_name],"last":2,"timezone":"America/New_York"}
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
    querystring = {"season":"2022","team":api_football_team_id[team_name],"next":1,"timezone":"America/New_York"}
    response = json.loads(r.request("GET", url, headers=headers, params=querystring).text)
    team_info[team_name]['schedule'][0]['home'] = response['response'][0]['teams']['home']['name']
    team_info[team_name]['schedule'][0]['away'] = response['response'][0]['teams']['away']['name']
    team_info[team_name]['schedule'][0]['time'] = response['response'][0]['fixture']['date']
    team_info[team_name]['schedule'][0]['embed_highlights'] = ['game has not started']

    # UPDTATE HIGHLIGHTS
    entity = datastore.Entity(client.key('team_info',team_name))
    entity[team_name] = json.dumps(team_info)
    client.put(entity)

# OLD FUNCTION
def OLD_return_embed_highlights(home,away):

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
                if 'Highlights' in video['title']:
                    return video['embed']
            return "No highlights yet"
    return "cannot find game"

def return_embed_highlights(home,away):
    q = r.get('https://www.youtube.com/results?search_query=' + home.replace(' ','+') + '+' + away.replace(' ','+') + '+highlights')
    video_id = q.text.split('/watch?v=')[1][0:11]
    embed_highlights = '<iframe width="420" height="315"src="https://www.youtube.com/embed/' + video_id + '"></iframe>'
    return embed_highlights
    

def initialize_team_info(team_name,api_football_team_id):
    # PUT TEAM INFO
    team_info = {team_name: {"schedule": [{},{},{}] }}
    entity = datastore.Entity(client.key('team_info',team_name))
    entity[team_name] = json.dumps(team_info)
    client.put(entity)
    # PUT API FOOTBALL TEAM ID
    entity = datastore.Entity(client.key('api_football_team_id',team_name))
    entity[team_name] = api_football_team_id
    client.put(entity)
    # UPDATE TEAM INFO
    update_team_info(team_name)
    
if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
