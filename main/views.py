from django.shortcuts import render, redirect
from django.http import HttpResponse
from igdb.wrapper import IGDBWrapper
from datetime import date
from pathlib import Path
from time import sleep
import environ, json, random, requests

# Load environment variables
env = environ.Env()
environ.Env.read_env(Path(__file__).resolve().parent.parent / '.env')

# Set up wrapper global
igdb_wrapper = None

def igdb_request(endpoint, fields, options):
    
    # Convert fields and options list to strings
    field_string = ', '.join(fields)
    options_string = '; '.join(options)

    # Make the request
    # Convert results to JSON
    # Get JSON from single-item list
    result = json.loads(igdb_wrapper.api_request(endpoint, f'fields {field_string}; {options_string};'))[0]
    print(result)

    # Sleep 1/4 of a second between requests
    # The IGDB API only accepts 4 requests per second
    sleep(0.25)

    # Finally, return the JSON
    return result

# Create your views here.
def index(request):

    # Set up context
    context = {
        'game_name': None,
        'game_cover_url': None,
        'game_genres': None,
        'game_release_date': 'Unknown'
    }

    # Get globals
    global env
    global igdb_wrapper

    if request.method == "POST":
        if 'next' in request.POST: # The Next button was pressed
            
            # Access IGDB API
            token_request = requests.post(f'https://id.twitch.tv/oauth2/token?client_id={env("IGDB_CLIENT_ID")}&client_secret={env("IGDB_CLIENT_SECRET")}&grant_type=client_credentials')
            token = token_request.json()['access_token']

            # Initialize IGDB wrapper
            igdb_wrapper = IGDBWrapper(env('IGDB_CLIENT_ID'), token)

            game_fields = [
                'cover',
                'genres',
                'first_release_date',
                'involved_companies',
                'name'
            ]

            # Get highest game id
            highest_result = igdb_request('games', ['id'], ['limit 1'])

            # Establish random offset with highest ID
            random_offset = random.randint(1, int(highest_result.get('id')))

            # Find a random game
            game_result = igdb_request('games', game_fields, ['limit 1', f'offset {random_offset}'])
            context['game_name'] = game_result['name']

            # Check if cover is available
            if 'cover' in game_result:

                # Get cover
                cover_result = igdb_request('covers', ['url'], [f'where id={game_result["cover"]}'])
                context['game_cover_url'] = cover_result['url']

            # Check if genres are available
            if 'genres' in game_result:

                # Iterate through each genre ID
                genre_results = []
                game_genres = []
                i = 0
                for genre in game_result['genres']:

                    # Get each genre and populate the genre list
                    genre_results.insert(i, igdb_request('genres', ['slug'], [f'where id={genre}']))
                    game_genres.insert(i, genre_results[i]['slug'])
                    i += 1

                context['game_genres'] = ', '.join(game_genres)

            # Check if release date is available
            if 'first_release_date' in game_result:

                # Convert release date from UNIX timestamp
                release_date_result = date.fromtimestamp(game_result['first_release_date'])
                print(release_date_result)
                context['game_release_date'] = release_date_result.strftime('%B %d, %Y')

    return render(request, 'main/index.html', context)