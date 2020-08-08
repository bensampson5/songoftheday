# songoftheday
Script that integrates with Google Calendar API to pull song of the day requests, queries iTunes
for the 30 second preview and album artwork of that song, and does some simple audio processing.

The current song of the day audio files are written to the `songs/` directory in the .m4a and .wav formats. The album artwork is written to the same directory as well in the .jpg and .png formats.

## How to use

1. Clone the songoftheday repository from GitHub.

```bash
git clone https://github.com/bensampson5/songoftheday.git
```

2. Get the client_secret json file for accessing the Google Calendar from the Google API and save it to the top-level directory in the project.

3. Build the docker image.

**No proxy**
```bash
docker build -f Dockerfile -t songoftheday .
```

**Proxy**
```bash
docker build -f Dockerfile -t songoftheday --build-arg http_proxy=http://proxy.example.com:80 .
```

4. Run the songoftheday.py script within the docker image.

 The first time you run this you will need to authenticate with Google Calendar so follow the instructions. After this first authentication,
 the songoftheday application stores the credentials used so that all subsequent runs can happen without user input.

```bash
docker run -i --rm -v $(pwd):/code songoftheday python songoftheday.py
```

5. Output files are written to the `data/` directory.