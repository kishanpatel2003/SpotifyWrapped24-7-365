from flask import Flask, request, redirect, url_for, session, render_template_string
import os
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import FlaskSessionCacheHandler

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(64)

CLIENT_ID = 'use your own lolll'
CLIENT_SECRET = 'use your own lolll'
redirect_uri = 'http://localhost:5000/callback'
scope = 'user-read-recently-played user-top-read playlist-read-private playlist-modify-public'

cache_handler = FlaskSessionCacheHandler(session)
sp_oauth = SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=redirect_uri,
    scope=scope,
    cache_handler=cache_handler,
    show_dialog=True
)
sp = Spotify(auth_manager=sp_oauth)


@app.route('/')
def home():
    state = session.get('state')
    if not state:
        state = os.urandom(16).hex()
        session['state'] = state

    if not sp_oauth.validate_token(cache_handler.get_cached_token()):
        auth_url = sp_oauth.get_authorize_url(state=state)
        return redirect(auth_url)
    
    return render_template_string("""
    <h1>Welcome to the Spotify Flask App</h1>
    <p>Select an option below:</p>
    <ul>
        <li><a href="{{ url_for('recently_played') }}">Recently Played Tracks</a></li>
        <li><a href="{{ url_for('top_tracks') }}">Top Tracks</a></li>
        <li><a href="{{ url_for('top_artists') }}">Top Artists</a></li>
        <li><a href="{{ url_for('recommendations') }}">Get Recommendations</a></li>
    </ul>
    <br>
    <a href="{{ url_for('logout') }}">Logout</a>
    """)


@app.route('/callback')
def callback():
    try:
        if 'code' not in request.args:
            return "Authorization code not found in request.", 400

        token_info = sp_oauth.get_access_token(request.args['code'])
        session['token_info'] = token_info
        return redirect(url_for('home'))
    except Exception as e:
        print(f"Error in callback: {str(e)}")
        return f"Error during authentication: {str(e)}"


@app.route('/recently_played')
def recently_played():
    if not sp_oauth.validate_token(cache_handler.get_cached_token()):
        auth_url = sp_oauth.get_authorize_url()
        return redirect(auth_url)

    recently_played_tracks = get_recently_played_tracks()
    tracks_html = '<br>'.join(
        [f'{track["name"]} by {track["artist"]} - Played at: {track["played_at"]}' for track in recently_played_tracks]
    )
    return f"""
    <h2>Recently Played Tracks</h2>
    {tracks_html}
    <br><br>
    <a href="{url_for('home')}">Back to Home</a>
    """


def get_recently_played_tracks():
    from datetime import datetime, timedelta
    three_months_ago = datetime.now() - timedelta(days=90)
    after_timestamp = int(three_months_ago.timestamp() * 1000)

    results = sp.current_user_recently_played(limit=50, after=after_timestamp)
    recently_played = []
    for item in results['items']:
        track = item['track']
        recently_played.append({
            'name': track['name'],
            'artist': track['artists'][0]['name'],
            'played_at': item['played_at']
        })
    return recently_played


@app.route('/top_tracks')
def top_tracks():
    if not sp_oauth.validate_token(cache_handler.get_cached_token()):
        auth_url = sp_oauth.get_authorize_url()
        return redirect(auth_url)

    top_tracks = get_top_tracks()
    tracks_html = '<br>'.join(
        [f'{idx + 1}. {track["name"]} by {track["artist"]} - Popularity: {track["popularity"]}' for idx, track in enumerate(top_tracks)]
    )
    return f"""
    <h2>Top Tracks</h2>
    {tracks_html}
    <br><br>
    <a href="{url_for('home')}">Back to Home</a>
    """


def get_top_tracks(limit=50, time_range='short_term'):
    results = sp.current_user_top_tracks(limit=limit, time_range=time_range)
    top_tracks = []
    for item in results['items']:
        top_tracks.append({
            'name': item['name'],
            'artist': item['artists'][0]['name'],
            'popularity': item['popularity']
        })
    return top_tracks


@app.route('/top_artists')
def top_artists():
    if not sp_oauth.validate_token(cache_handler.get_cached_token()):
        auth_url = sp_oauth.get_authorize_url()
        return redirect(auth_url)

    top_artists = get_top_artists()
    artists_html = '<br>'.join(
        [f'{idx + 1}. {artist["name"]} - Genres: {", ".join(artist["genres"])}' for idx, artist in enumerate(top_artists)]
    )
    return f"""
    <h2>Your Top Artists</h2>
    {artists_html}
    <br><br>
    <a href="{url_for('home')}">Back to Home</a>
    """


def get_top_artists(limit=20, time_range='short_term'):
    results = sp.current_user_top_artists(limit=limit, time_range=time_range)
    top_artists = []
    for item in results['items']:
        top_artists.append({
            'name': item['name'],
            'genres': item['genres']
        })
    return top_artists

@app.route('/recommendations')
def recommendations():
    try:
        if not sp_oauth.validate_token(cache_handler.get_cached_token()):
            auth_url = sp_oauth.get_authorize_url()
            return redirect(auth_url)

        # Get the user's top artist as a seed
        top_artist = sp.current_user_top_artists(limit=1)
        seed_artists = [top_artist['items'][0]['id']] if top_artist['items'] else []

        # Use both artist and genre seeds
        params = {
            'seed_artists': seed_artists,
            'seed_genres': ['pop', 'dance'],  # Using two genres
            'limit': 20
        }

        print("Recommendation parameters:", params)  # Debug print
        
        recommended_tracks = sp.recommendations(**params)['tracks']

        recommendations_html = '<br>'.join(
            [f"{idx + 1}. {track['name']} by {', '.join([artist['name'] for artist in track['artists']])}"
             for idx, track in enumerate(recommended_tracks)]
        )
        
        return f"""
        <h2>Recommended Tracks</h2>
        {recommendations_html}
        <br><br>
        <a href="{url_for('home')}">Back to Home</a>
        """
        
    except Exception as e:
        print(f"Full error: {str(e)}")
        return f"""
        <h2>Error Getting Recommendations</h2>
        <p>{str(e)}</p>
        <br><br>
        <a href="{url_for('home')}">Back to Home</a>
        """

@app.route('/logout')
def logout():
    session.clear() 
    return redirect(url_for('home'))


if __name__ == "__main__":
    app.run(debug=True)