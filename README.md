# songoftheday
Script that integrates with Google Calendar API to pull song of the day requests, queries iTunes
for the 30 second preview and album artwork of that song, and does some simple audio processing.

The current song of the day audio files are written to the `songs/` directory in the .m4a and .wav formats. The album artwork is written to the same directory as well in the .jpg and .png formats.

## How to use

1. Get the client_secret json file for accessing the Google Calendar from the Google API and save it to the top-level directory in the project.

2. If behind a proxy, [modify the Dockerfile for your proxy configuration](https://github.com/bensampson5/songoftheday/blob/master/Dockerfile.ubuntu#L3).

3. Build the docker image.

```bash
docker build -f Dockerfile.ubuntu -t songoftheday . 
```

4. Run the songoftheday.py script within the docker image.

```bash
docker run --rm -v $(pwd):/code songoftheday python3 songoftheday.py
```

5. Output files are written to the `data/` directory.