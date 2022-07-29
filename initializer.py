from google.cloud import datastore
import requests
import json

client = datastore.Client()

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

def initialize_league(league_name, api_football_league_id, season="2022", initialize_teams=True):
    url = "https://api-football-v1.p.rapidapi.com/v3/teams"

    querystring = {"league":api_football_league_id,"season":season}

    headers = {
        "X-RapidAPI-Key": "9f0303d58bmsh4ba4d5e0c9d5e51p17a64ajsnd6ba4f5a2e07",
        "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
        }

    response = requests.request("GET", url, headers=headers, params=querystring)

    team_list = []
    for team in json.loads(response.text)['response']:
        initialize_team_info(team['team']['name'],team['team']['id'])
        team_list.append(team['team']['name'])
    
    league_name = league_name.replace(' ','')
    entity = datastore.Entity(client.key('league_teams',league_name))
    entity[league_name] = team_list
    client.put(entity)
        
def delete_league_teams_entity(league_name):
    client.delete(client.key('league_teams',league_name))
