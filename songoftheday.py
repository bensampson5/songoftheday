#!/usr/bin/python3

import os
import datetime
import requests
import httplib2
import subprocess
import xml.etree.ElementTree as et
from urllib.parse import urlencode
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage
from googleapiclient import discovery
from PIL import Image, ImageDraw, ImageFont

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/calendar-python-songoftheday.json
SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'
CLIENT_SECRET_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'client_secrets.json')
#print(CLIENT_SECRET_FILE)
APPLICATION_NAME = 'Song of the Day'

def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'calendar-python-songoftheday.json')

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        credentials = tools.run_flow(flow, store)
        print('Storing credentials to ' + credential_path)
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


def get_itunes_song_data(search_terms="", random=False):
    """Queries iTunes based on search_terms and returns song data for first hit with a valid
    previewUrl. If no songs are found then it returns None. If random flag is true then it
    ignores the search_terms and gets the song data for a random song from iTunes.

    :param search_terms: str
    :param random: bool (default=False)
    :return: song data or None
    """

    if not random:
        # url encode search term input from user. Only look for songs
        query = urlencode({'term': search_terms, 'media': 'music', 'entity': 'song', 'explicit': 'No'})

        # request data from iTunes and process returned json object
        r = requests.get("https://itunes.apple.com/search?" + query)
        data = r.json()

        # return first hit that has a valid previewUrl
        for result in data['results']:
            if result['previewUrl'] is not None:
                return result

    else:
        # random is implemented by getting the first song from The Current's Song of the Day
        # that has a valid 30 second preview on iTunes

        # pull all items from Song of the Day feed from The Current
        r = requests.get("https://feeds.publicradio.org/public_feeds/song-of-the-day/rss/rss")
        rss_root = et.fromstring(r.content.decode("utf-8"))
        items_sotd = rss_root.find('channel').findall('item')

        # iterate through each item on Song of the Day feed from The Current and look up on iTunes
        # for a match
        for i in items_sotd:
            query = urlencode({'term': i.find('title').text, 'media': 'music', 'entity': 'song'})

            # request data from iTunes and process returned json object
            r = requests.get("https://itunes.apple.com/search?" + query)
            data = r.json()

            # return first hit that has a valid previewUrl
            for result in data['results']:
                if result['previewUrl']:
                    return result

if __name__ == "__main__":

    FILE_BASE_NAME = 'songoftheday'  # base name for audio files
    SONGS_DIR = os.path.join(os.path.split(os.path.dirname(os.path.abspath(__file__)))[0], "songs")

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
            sotd_itunes_data = get_itunes_song_data(random=True)

    else:  # case: no eligible sotd events found on the calendar for today so get a random song
        sotd_itunes_data = get_itunes_song_data(random=True)

    if sotd_itunes_data:

        # delete any old song of the day audio files if they exist
        files = os.listdir(SONGS_DIR)
        for f in files:
            if f.endswith('.wav') or f.endswith('.m4a'):
                os.remove(os.path.join(SONGS_DIR, f))

        # grab 30 second song preview (is in .m4a format)
        preview_m4a = requests.get(sotd_itunes_data['previewUrl'])

        # save data bytes to .m4a file
        m4a_fname = os.path.join(SONGS_DIR, FILE_BASE_NAME + str(datetime.date.today()) + '.m4a')
        with open(m4a_fname, 'wb') as f:
            f.write(preview_m4a.content)

        # use ffmpeg to open the .m4a file and convert to .wav file
        wav_fname = os.path.join(SONGS_DIR, FILE_BASE_NAME + str(datetime.date.today()) + '.wav')
        process = subprocess.Popen(['ffmpeg', '-i', m4a_fname, wav_fname], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        # print(stdout, stderr)

        # Log completed request in songs.log
        dt = str(datetime.datetime.now())
        track = sotd_itunes_data['trackName']
        artist = sotd_itunes_data['artistName']
        album = sotd_itunes_data['collectionName']
        log_string = "Timestamp: " + dt + "\n" + "Requester: " + requester + "\n"\
                    + "Track: " + track + "\n" + "Artist: " + artist + "\n"\
                    + "Album: " + album + "\n\n"
        album_art_Url = sotd_itunes_data['artworkUrl100']
    #    print(album_art_Url)
        album_art_Url = album_art_Url.replace("100x100","400x400")
    #    print(album_art_Url)

        album_bitmap = requests.get(album_art_Url)    #  raw jpg bitmap
    #    print(album_bitmap)

        bitmap_fname = os.path.join(SONGS_DIR,"bitmap.jpg")
        if album_bitmap.status_code == 200:
            with open(bitmap_fname, 'wb') as f:
                f.write(album_bitmap.content)
        else:
            os.remove(bitmap_fname)
        
        album_bitmap = Image.open(bitmap_fname)
        bkgnd = Image.new("RGB",(1024,768),"black")
        (sizeX,sizeY) = album_bitmap.size
        bkgnd.paste(album_bitmap,(512-sizeX//2,768-sizeY))  # note integer division
        draw = ImageDraw.Draw(bkgnd)                      #  create pointer to draw on bkgnd
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",40)  # generate font
        title = "Song of the Day"
        (width,height) = draw.textsize(title,font=font)
        draw.text(((1024-width)/2,20),title,fill="white",font=font)

        draw.text((40,80), "Song: "+track ,fill="white",font=font)
        draw.text((40,140), "Artist: "+artist ,fill="white",font=font)
        draw.text((40,200), "Album: "+album ,fill="white",font=font)

        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",30)  # generate font
        draw.text((40,260), "Email Complaints To: "+requester,fill="white",font=font)

        bkgnd.save("~/Pictures/sotd.png")


        # log completion of script
        with open(os.path.join(SONGS_DIR, "songs.log"), 'a') as log:
            log.write(log_string)

    else:
        # Log error
        dt = str(datetime.datetime.now())
        log_string = "Timestamp: " + dt + "\n" + "Error: Failed to find a song for Song of the Day\n\n"
        with open(os.path.join(SONGS_DIR, "songs.log"), 'a') as log:
            log.write(log_string)

