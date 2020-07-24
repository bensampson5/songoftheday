import datetime
import requests
import httplib2
import subprocess
from pathlib import Path
import xml.etree.ElementTree as et
from urllib.parse import urlencode
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage
from googleapiclient import discovery
from PIL import Image, ImageDraw, ImageFont
import billboard
import random


def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    cwd = Path('.')
    credentials_dir = cwd / '.credentials'
    if not credentials_dir.exists():
        credentials_dir.mkdir()
    credential_path = credentials_dir / 'calendar-python-songoftheday.json'

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:

        # try to find a client_secrets json file in the current directory
        client_secret = list(cwd.glob('client_secret*.json'))

        if client_secret:
            # validate credentials using client_secret
            scopes = 'https://www.googleapis.com/auth/calendar.readonly'
            flow = client.flow_from_clientsecrets(client_secret[0], scopes)
            flow.user_agent = 'Song of the Day'
            credentials = tools.run_flow(flow, store)
            print('Storing credentials to ' + str(credential_path))
        else:
            raise FileNotFoundError('Could not find client_secret json file')
            
    return credentials


def get_eligible_sotd_events():
    """Goes to the google calendar any pulls any eligible song of the day events for
    today. Eligible song of the days events are non-recurring all-day events. If this
    method doesn't find any eligible events then it returns None.

    :return:
        sotd_events, list of today's eligible events or None if no eligible events found
        sorted by order of when event was created (oldest to newest)
    """

    # start service to calendar using credentials
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('calendar', 'v3', http=http)

    today = datetime.date.today()  # get today's date on the local machine

    # define min and max times for events that land today for google calendar request
    min_time = datetime.datetime(
        today.year, today.month, today.day).isoformat() + "-05:00"  # Central Time
    max_time = datetime.datetime(
        today.year, today.month, today.day,
        hour=23, minute=59, second=59).isoformat() + "-05:00"  # Central Time

    # make request to google calendar for all events happening today
    # response events are sorted in ascending order of last updated (oldest to newest)
    events_result = service.events().list(
        calendarId='primary', timeMin=min_time, timeMax=max_time,
        singleEvents=False, orderBy='updated').execute()
    events = events_result.get('items', [])  # get list of events from response

    # Identify all eligible song of the day events and return
    if events:
        return [e for e in events if e['start'].get('date') == str(datetime.date.today())]


def get_itunes_song_data(search_terms="", select_random=False):
    """Queries iTunes based on search_terms and returns song data for first hit with a valid
    previewUrl. If no songs are found then it returns None. If random flag is true then it
    ignores the search_terms and gets the song data for a random song from iTunes.

    :param search_terms: str
    :param select_random: bool (default=False)
    :return: song data or None
    """
    if not select_random:
        # url encode search term input from user. Only look for songs
        query = urlencode(
            {'term': search_terms, 'media': 'music', 'entity': 'song'})

        # request data from iTunes and process returned json object
        r = requests.get("https://itunes.apple.com/search?" + query)
        data = r.json()

        # return first hit that has a valid previewUrl
        for result in data['results']:
            if result['previewUrl']:
                    if result['trackExplicitness'] != 'explicit':
                        return result

    else:
        # select_random is implemented by getting a random song from the billboard hot 100
        # that has a valid 30 second preview on iTunes
        chart = billboard.ChartData('hot-100')
        songs = [song.title + ' ' + song.artist for song in chart]
        random.shuffle(songs)

        for song in songs:
            query = urlencode({'term': song, 'media': 'music', 'entity': 'song'})

            # request data from iTunes and process returned json object
            r = requests.get("https://itunes.apple.com/search?" + query)
            data = r.json()
            print(data)

            # return first hit that has a valid previewUrl and is not explicit
            for result in data['results']:
                if result['previewUrl']:
                    if result['trackExplicitness'] != 'explicit':
                        return result


if __name__ == "__main__":

    song_file_base_name = 'songoftheday'  # base name for audio files
    cwd = Path('.')
    data_dir = cwd / 'data'

    if not data_dir.exists():
        data_dir.mkdir()

    sotd_events = get_eligible_sotd_events()

    requester = "random"  # set to random by default, will get overwritten if valid requester
    if sotd_events:  # case: at least one eligible sotd events found on the calendar for today

        # loop through all eligible sotd events found
        for e in sotd_events:
            search_terms = e['summary']  # grab title of event for iTunes query

            # query iTunes to find a matching song with a previewUrl. Returns None if unable to match
            sotd_itunes_data = get_itunes_song_data(search_terms=search_terms)
            if sotd_itunes_data:  # if not None, then we've found a match on iTunes so exit loop
                requester = e['creator'].get('email')
                break

        # case: there was one or more eligible sotd events on calendar for today but couldn't match
        # query to any song preview on iTunes. In this case, get a random song.
        if not sotd_itunes_data:
            sotd_itunes_data = get_itunes_song_data(select_random=True)

    else:  # case: no eligible sotd events found on the calendar for today so get a random song
        sotd_itunes_data = get_itunes_song_data(select_random=True)

    if sotd_itunes_data:

        # delete any old song of the day audio files if they exist
        for p in data_dir.glob('*.wav'):
            p.unlink()
        for p in data_dir.glob('*.m4a'):
            p.unlink()

        # grab 30 second song preview (is in .m4a format)
        preview_m4a = requests.get(sotd_itunes_data['previewUrl'])

        # save data bytes to .m4a file
        m4a_fname = data_dir / (song_file_base_name +
                                '_' + str(datetime.date.today()) + '.m4a')
        with open(m4a_fname, 'wb') as f:
            f.write(preview_m4a.content)

        # use ffmpeg to open the .m4a file and convert to .wav file
        wav_fname = data_dir / (song_file_base_name +
                                '_' + str(datetime.date.today()) + '.wav')
        cmd = ' '.join(['ffmpeg', '-i', str(m4a_fname), str(wav_fname)])
        proc = subprocess.run(cmd, capture_output=True, timeout=10, shell=True)
        if proc.returncode != 0:  # check if completed successfully
            if proc.stdout:
                print('stdout:\n' + proc.stdout.decode() + '\n')
            if proc.stderr:
                print('stderr:\n' + proc.stderr.decode() + '\n')
            raise Exception('m4a to wav conversion using ffmpeg failed')

        # use sox to modify wav file for speaker system
        cmd = ' '.join(['sox', str(wav_fname), '-c 1', str(wav_fname).split('.')[0] + '_modified' +
                        wav_fname.suffix, 'lowpass 5000 silence 1 3 2% compand 0.3,1 6:-70,-60,-20 -5 -90 0.2'])
        proc = subprocess.run(cmd, capture_output=True, timeout=10, shell=True)
        if proc.returncode != 0:  # check if completed successfully
            if proc.stdout:
                print('stdout:\n' + proc.stdout.decode() + '\n')
            if proc.stderr:
                print('stderr:\n' + proc.stderr.decode() + '\n')
            raise Exception('wav modification using sox failed')

        # Grab important information from song of the day
        dt = str(datetime.datetime.now())
        track = sotd_itunes_data['trackName']
        artist = sotd_itunes_data['artistName']
        album = sotd_itunes_data['collectionName']

        album_art_Url = sotd_itunes_data['artworkUrl100'].replace(
            "100x100", "400x400")
        album_bitmap = requests.get(album_art_Url)  # raw jpg bitmap

        bitmap_fname = data_dir / 'bitmap.jpg'
        if album_bitmap.status_code == 200:
            with open(bitmap_fname, 'wb') as f:
                f.write(album_bitmap.content)
        else:
            bitmap_fname.unlink()

        album_bitmap = Image.open(bitmap_fname)
        bkgnd = Image.new("RGB", (1024, 768), "black")
        (sizeX, sizeY) = album_bitmap.size
        # note integer division
        bkgnd.paste(album_bitmap, (512-sizeX//2, 768-sizeY))
        draw = ImageDraw.Draw(bkgnd)  # create pointer to draw on bkgnd

        fonts_dir = cwd / 'fonts'
        fonts_path = fonts_dir / 'DejaVuSansMono.ttf'

        font = ImageFont.truetype(str(fonts_path), 40)  # generate font
        title = "Song of the Day"
        (width, height) = draw.textsize(title, font=font)
        draw.text(((1024-width)/2, 20), title, fill="white", font=font)

        draw.text((40, 80), "Song: "+track, fill="white", font=font)
        draw.text((40, 140), "Artist: "+artist, fill="white", font=font)
        draw.text((40, 200), "Album: "+album, fill="white", font=font)

        fonts_dir = cwd / 'fonts'
        font = ImageFont.truetype(str(fonts_path), 30)  # generate font
        draw.text((40, 260), "Email Complaints To: " +
                  requester, fill="white", font=font)

        bkgnd.save(data_dir / 'sotd.png')

        # log new songoftheday entry
        log_dir = cwd / 'logs'
        log_fname = 'songs.log'
        if not log_dir.exists():
            log_dir.mkdir()
        log_entry = "Timestamp: " + dt + "\n" + "Requester: " + requester + "\n" \
            + "Track: " + track + "\n" + "Artist: " + artist + "\n" \
            + "Album: " + album + "\n\n"
        with open(log_dir / log_fname, 'a') as log:
            log.write(log_entry)

    else:
        # Log error
        dt = str(datetime.datetime.now())
        log_string = "Timestamp: " + dt + "\n" + \
            "Error: Failed to find a song for Song of the Day\n\n"
        with open(log_dir / log_fname, 'a') as log:
            log.write(log_entry)
