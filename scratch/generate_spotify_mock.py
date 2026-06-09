import os
import json
import time
import requests

ARTISTS_FILE = "/home/adam/Coding/MusicaBI/etl/artists.txt"
MOCK_FILE = "/home/adam/Coding/MusicaBI/etl/sources/spotify_mock.json"
USER_AGENT = "MusicaBI/0.1 (mikolaj.lepsy@gmail.com)"

def load_artists():
    with open(ARTISTS_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def fetch_artist_mbid(artist_name):
    url = "https://musicbrainz.org/ws/2/artist/"
    headers = {"User-Agent": USER_AGENT}
    params = {"query": f'artist:"{artist_name}"', "fmt": "json", "limit": 1}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        artists = resp.json().get("artists", [])
        if artists:
            return artists[0].get("id")
    except Exception as e:
        print(f"Error fetching MBID for {artist_name}: {e}")
    return None

def fetch_albums(artist_name, mbid):
    url = "https://musicbrainz.org/ws/2/release-group"
    headers = {"User-Agent": USER_AGENT}
    params = {"artist": mbid, "fmt": "json", "limit": 10}
    albums = []
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        release_groups = resp.json().get("release-groups", [])
        for rg in release_groups:
            primary_type = (rg.get("primary-type") or "album").lower()
            if primary_type not in ["album", "single"]:
                continue
            
            title = rg.get("title", "")
            raw_date = rg.get("first-release-date", "")
            
            # Determine precision
            if len(raw_date) == 10:
                precision = "day"
            elif len(raw_date) == 7:
                precision = "month"
            elif len(raw_date) == 4:
                precision = "year"
            else:
                raw_date = "2024-01-01"
                precision = "day"
                
            albums.append({
                "spotify_album_id": f"mock_album_{rg.get('id')}",
                "spotify_artist_id": f"mock_artist_{artist_name.lower().replace(' ', '_')}",
                "artist_name": artist_name,
                "title": title,
                "release_date": raw_date,
                "release_date_precision": precision,
                "album_type": primary_type
            })
            if len(albums) >= 5:
                break
    except Exception as e:
        print(f"Error fetching albums for {artist_name}: {e}")
    return albums

def get_fallback_albums(artist_name):
    return [
        {
            "spotify_album_id": f"mock_album_{artist_name.lower().replace(' ', '_')}_fallback",
            "spotify_artist_id": f"mock_artist_{artist_name.lower().replace(' ', '_')}",
            "artist_name": artist_name,
            "title": f"The Best of {artist_name}",
            "release_date": "2024-01-01",
            "release_date_precision": "day",
            "album_type": "album"
        }
    ]

def main():
    artists = load_artists()
    mock_data = {}
    print(f"Loaded {len(artists)} artists. Starting generation...")
    
    # Ensure output folder exists
    os.makedirs(os.path.dirname(MOCK_FILE), exist_ok=True)
    
    for i, artist in enumerate(artists):
        print(f"[{i+1}/{len(artists)}] Processing {artist}...")
        mbid = fetch_artist_mbid(artist)
        time.sleep(1.1)
        if mbid:
            albums = fetch_albums(artist, mbid)
            time.sleep(1.1)
            if albums:
                mock_data[artist] = albums
                print(f"  Found {len(albums)} albums.")
            else:
                print(f"  No albums found, using default fallback.")
                mock_data[artist] = get_fallback_albums(artist)
        else:
            print(f"  MBID not found, using default fallback.")
            mock_data[artist] = get_fallback_albums(artist)
            
    with open(MOCK_FILE, "w", encoding="utf-8") as f:
        json.dump(mock_data, f, indent=2, ensure_ascii=False)
    print("Done!")

if __name__ == "__main__":
    main()
