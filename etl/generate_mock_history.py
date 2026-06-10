#!/usr/bin/env python3
"""
Back-fills 14 days of staging data directly into PostgreSQL.
Safe to re-run (ON CONFLICT DO NOTHING for lastfm; TRUNCATE+INSERT for others).

Usage:
    python etl/generate_mock_history.py
    cd transform && dbt run --profiles-dir .
"""
import hashlib
import random
from datetime import date, timedelta, datetime, timezone

import psycopg2
import psycopg2.extras

DAYS = 14
random.seed(42)

DB = dict(dbname="MusicaBi", user="admin", password="admin", host="localhost", port=5432)

GROWTH = {
    "breakout":  (0.030, 0.055),
    "growing":   (0.005, 0.020),
    "stable":    (-0.002, 0.004),
    "declining": (-0.010, -0.003),
}

# (today_listeners, country_iso2, [genres], growth_type)
# base_listeners aligned to real Last.fm values scraped 2026-06-09
ARTISTS = {
    "Chappell Roan":                   (2_611_546, "US", ["pop", "indie pop", "synth-pop"], "breakout"),
    "Sabrina Carpenter":               (3_307_571, "US", ["pop", "dance pop"], "breakout"),
    "Benson Boone":                    (1_518_165, "US", ["pop", "indie pop"], "growing"),
    "Shaboozey":                       (765_986,   "US", ["country", "hip-hop", "country rap"], "breakout"),
    "Tommy Richman":                   (1_517_706, "US", ["r&b", "soul", "hip-hop"], "growing"),
    "Tyla":                            (1_536_833, "ZA", ["afropop", "pop", "r&b"], "growing"),
    "Teddy Swims":                     (1_191_546, "US", ["soul", "pop", "r&b"], "growing"),
    "Sexyy Red":                       (1_020_152, "US", ["hip-hop", "rap"], "stable"),
    "The Last Dinner Party":           (821_151,   "GB", ["indie rock", "art rock", "indie"], "growing"),
    "Mk.gee":                          (727_142,   "US", ["indie", "indie pop", "alternative"], "growing"),
    "Renée Rapp":                      (650_000,   "US", ["pop", "musical theatre", "indie pop"], "growing"),
    "Doechii":                         (2_078_299, "US", ["hip-hop", "rap", "r&b"], "breakout"),
    "Lay Bankz":                       (690_410,   "US", ["hip-hop", "rap"], "growing"),
    "Friko":                           (129_357,   "US", ["indie rock", "indie", "alternative"], "growing"),
    "Been Stellar":                    (124_891,   "US", ["indie rock", "post-punk", "indie"], "growing"),
    "Royel Otis":                      (1_001_401, "AU", ["indie pop", "indie", "alternative"], "growing"),
    "GloRilla":                        (943_992,   "US", ["hip-hop", "rap"], "stable"),
    "Bossman DLow":                    (391_382,   "US", ["hip-hop", "rap", "drill"], "growing"),
    "Gracie Abrams":                   (1_852_509, "US", ["indie pop", "folk", "alternative"], "breakout"),
    "Wave to Earth":                   (881_954,   "KR", ["indie", "indie pop", "lo-fi"], "growing"),
    "Laufey":                          (2_416_152, "IS", ["jazz", "indie pop", "bedroom pop"], "growing"),
    "ILLIT":                           (1_216_317, "KR", ["k-pop", "pop"], "growing"),
    "Babymonster":                     (520_000,   "KR", ["k-pop", "pop", "hip-hop"], "stable"),
    "Kiss of Life":                    (749_959,   "KR", ["k-pop", "r&b", "funk"], "growing"),
    "TWS":                             (257_793,   "KR", ["k-pop", "pop"], "growing"),
    "English Teacher":                 (182_928,   "GB", ["indie rock", "post-punk", "indie"], "growing"),
    "CHINCHILLA":                      (193_270,   "GB", ["pop", "indie pop"], "growing"),
    "Brigette Calls Me Baby":          (32_000,    "US", ["indie pop", "pop"], "growing"),
    "Trout":                           (9_004,     "US", ["indie", "lo-fi", "indie rock"], "stable"),
    "Fcukers":                         (354_691,   "GB", ["punk", "post-punk", "indie"], "breakout"),
    "Snow Strippers":                  (954_033,   "US", ["electronic", "darkwave", "synth-pop"], "breakout"),
    "Rachel Chinouriri":               (777_140,   "GB", ["indie pop", "r&b", "soul"], "breakout"),
    "Barry Can't Swim":                (409_306,   "GB", ["electronic", "dance", "uk garage"], "growing"),
    "Lastlings":                       (149_102,   "AU", ["synth-pop", "electronic", "indie pop"], "stable"),
    "Kenya Grace":                     (978_558,   "GB", ["electronic", "pop", "dance pop"], "growing"),
    "Artemas":                         (1_656_112, "GB", ["pop", "indie pop", "alternative"], "breakout"),
    "Dasha":                           (569_482,   "US", ["country", "pop country"], "growing"),
    "Ella Langley":                    (429_342,   "US", ["country", "pop country"], "growing"),
    "41":                              (361_200,   "US", ["pop", "indie pop"], "growing"),
    "310babii":                        (265_252,   "US", ["hip-hop", "rap", "west coast rap"], "stable"),
    "Richy Mitch and the Coal Miners": (32_000,    "US", ["folk", "americana", "indie folk"], "stable"),
    "Good Neighbours":                 (520_859,   "GB", ["indie rock", "indie", "alternative"], "breakout"),
    "Wasia Project":                   (519_313,   "GB", ["indie pop", "r&b", "alternative r&b"], "growing"),
    "The Red Clay Strays":             (316_439,   "US", ["americana", "country rock", "blues rock"], "growing"),
    "Megan Moroney":                   (318_585,   "US", ["country", "pop country"], "growing"),
    "Tucker Wetmore":                  (166_986,   "US", ["country"], "growing"),
    "Wyatt Flores":                    (144_405,   "US", ["country", "folk", "indie folk"], "growing"),
    "Tanner Adell":                    (54_654,    "US", ["country", "pop country"], "growing"),
    "Kadhja Bonet":                    (216_411,   "US", ["soul", "r&b", "folk"], "stable"),
    "Jayahadadream":                   (11_204,    "GB", ["indie pop", "indie", "alternative"], "growing"),
    "Mon Rovia":                       (115,       "GB", ["indie", "indie pop"], "stable"),
    "Konyikeh":                        (17_720,    "GB", ["r&b", "soul", "indie"], "growing"),
    "es.cher":                         (73_001,    "GB", ["indie pop", "bedroom pop", "lo-fi"], "growing"),
    "Joy Anonymous":                   (104_920,   "US", ["electronic", "dance", "indie pop"], "growing"),
    "Overmono":                        (293_570,   "GB", ["electronic", "techno", "dance"], "stable"),
    "Nia Archives":                    (395_664,   "GB", ["jungle", "electronic", "drum and bass"], "growing"),
    "Skin on Skin":                    (160_357,   "GB", ["electronic", "dance", "house"], "stable"),
    "salute":                          (302_787,   "AU", ["electronic", "bass music", "dance"], "stable"),
    "TSHA":                            (226_904,   "GB", ["electronic", "dance", "house"], "stable"),
    "Model/Actriz":                    (181_719,   "US", ["post-punk", "art rock", "indie rock"], "growing"),
    "Militarie Gun":                   (140_893,   "US", ["punk rock", "hardcore", "rock"], "growing"),
    "Gel":                             (151_646,   "US", ["hardcore", "punk", "hardcore punk"], "growing"),
    "Scowl":                           (157_522,   "US", ["hardcore", "punk", "hardcore punk"], "growing"),
    "Zulu":                            (113_796,   "US", ["hardcore", "metal", "noise"], "stable"),
    "Hotline TNT":                     (106_598,   "US", ["shoegaze", "indie rock", "noise pop"], "growing"),
    "Wednesday":                       (383_739,   "US", ["indie rock", "country rock", "alternative"], "growing"),
    "MJ Lenderman":                    (381_577,   "US", ["indie rock", "indie", "alternative"], "growing"),
    "Blondshell":                      (379_156,   "US", ["indie rock", "alternative rock", "indie"], "growing"),
    "Joanna Sternberg":                (75_781,    "US", ["folk", "indie folk", "singer-songwriter"], "stable"),
    "Kara Jackson":                    (97_782,    "US", ["folk", "indie folk", "singer-songwriter"], "growing"),
    "Hemlocke Springs":                (501_743,   "US", ["indie pop", "pop", "alternative"], "growing"),
    "Say She She":                     (153_456,   "US", ["soul", "funk", "r&b"], "growing"),
    "Charlotte Cardin":                (246_279,   "CA", ["pop", "indie pop", "electropop"], "stable"),
    "NewJeans":                        (1_857_678, "KR", ["k-pop", "pop", "r&b"], "stable"),
    "LE SSERAFIM":                     (1_725_197, "KR", ["k-pop", "pop", "dance pop"], "stable"),
    "RIIZE":                           (420_462,   "KR", ["k-pop", "pop"], "growing"),
    "ZEROBASEONE":                     (343_618,   "KR", ["k-pop", "pop"], "growing"),
    "BOYNEXTDOOR":                     (370_349,   "KR", ["k-pop", "pop", "indie pop"], "growing"),
    "PLAVE":                           (151_549,   "KR", ["k-pop", "pop", "virtual idol"], "growing"),
    "XG":                              (870_660,   "JP", ["k-pop", "pop", "hip-hop"], "growing"),
    "QWER":                            (91_077,    "KR", ["k-pop", "pop rock", "indie"], "growing"),
    "KATSEYE":                         (1_631_872, "US", ["k-pop", "pop", "dance pop"], "breakout"),
    "UNIS":                            (109_754,   "KR", ["k-pop", "pop"], "growing"),
    "bad invitations":                 (22_000,    "US", ["indie rock", "indie", "lo-fi"], "stable"),
    "bar italia":                      (276_213,   "GB", ["indie rock", "post-punk", "shoegaze"], "stable"),
    "Geese":                           (585_682,   "US", ["indie rock", "art rock", "alternative"], "growing"),
    "Nation of Language":              (258_183,   "US", ["synth-pop", "new wave", "indie pop"], "stable"),
    "Paris Paloma":                    (759_415,   "GB", ["folk pop", "indie folk", "singer-songwriter"], "growing"),
    "Isabel LaRosa":                   (1_131_034, "US", ["indie pop", "pop", "bedroom pop"], "breakout"),
    "grentperez":                      (685_462,   "AU", ["indie pop", "pop", "r&b"], "growing"),
    "Stephen Sanchez":                 (1_565_323, "US", ["pop", "indie pop", "soft rock"], "growing"),
    "d4vd":                            (2_343_122, "US", ["indie pop", "bedroom pop", "r&b"], "breakout"),
    "Lizzie McAlpine":                 (620_000,   "US", ["folk pop", "indie folk", "singer-songwriter"], "growing"),
    "Noah Kahan":                      (1_643_871, "US", ["folk", "indie folk", "singer-songwriter"], "stable"),
    "Zach Bryan":                      (1_224_413, "US", ["country", "americana", "folk"], "stable"),
    "Warren Zeiders":                  (180_353,   "US", ["country", "pop country"], "growing"),
    "Sam Barber":                      (307_492,   "US", ["country", "folk"], "growing"),
    "Megan Thee Stallion":             (2_394_657, "US", ["hip-hop", "rap", "trap"], "stable"),
    "Central Cee":                     (1_346_501, "GB", ["uk rap", "hip-hop", "drill"], "stable"),
    "Ice Spice":                       (1_520_504, "US", ["hip-hop", "rap", "drill"], "stable"),
}

# Real album data for major artists; others get generated fallbacks
KNOWN_ALBUMS = {
    "Chappell Roan":       [("The Rise and Fall of a Midwest Princess", "2023-09-22", "album")],
    "Sabrina Carpenter":   [("Short n' Sweet", "2024-08-23", "album"),
                            ("emails i can't send", "2022-09-23", "album")],
    "Benson Boone":        [("Fireworks & Rollerblades", "2024-03-08", "album")],
    "Shaboozey":           [("Where I Come From", "2024-05-31", "album")],
    "Tyla":                [("TYLA", "2024-03-22", "album")],
    "Teddy Swims":         [("I've Tried Everything But Therapy (Part 1)", "2023-10-13", "album")],
    "Gracie Abrams":       [("Good Riddance", "2023-02-24", "album"),
                            ("Minor", "2022-06-17", "album")],
    "Laufey":              [("Bewitched", "2023-09-08", "album"),
                            ("Everything I Know About Love", "2022-07-26", "album")],
    "Doechii":             [("Alligator Bites Never Heal", "2024-08-30", "album")],
    "Noah Kahan":          [("Stick Season", "2022-10-14", "album"),
                            ("Cape Elizabeth", "2023-02-17", "album")],
    "Zach Bryan":          [("Zach Bryan", "2023-08-25", "album"),
                            ("American Heartbreak", "2022-05-20", "album")],
    "NewJeans":            [("Get Up", "2023-07-21", "album"),
                            ("OMG", "2023-01-02", "single")],
    "LE SSERAFIM":         [("EASY", "2024-02-19", "album"),
                            ("UNFORGIVEN", "2023-05-01", "album")],
    "Megan Thee Stallion": [("MEGAN", "2024-06-28", "album"),
                            ("Traumazine", "2022-08-12", "album"),
                            ("Good News", "2020-11-20", "album")],
    "Central Cee":         [("Can't Rush Greatness", "2024-02-23", "album"),
                            ("23", "2022-02-25", "album")],
    "Ice Spice":           [("Y2K!", "2024-01-12", "album")],
    "MJ Lenderman":        [("Manning Fireworks", "2024-09-06", "album"),
                            ("Boat Songs", "2022-09-09", "album")],
    "Wednesday":           [("Rat Saw God", "2023-04-07", "album"),
                            ("Twin Plagues", "2021-09-10", "album")],
    "Royel Otis":          [("Pratts & Pain", "2023-06-09", "album")],
    "Blondshell":          [("Blondshell", "2023-04-07", "album")],
    "Hotline TNT":         [("Lemon Everything", "2023-05-05", "album")],
    "Overmono":            [("Good Lies", "2023-04-14", "album")],
    "Paris Paloma":        [("Cacophony", "2024-01-12", "album")],
    "Charlotte Cardin":    [("99 Nights", "2023-09-29", "album"),
                            ("Phoenix", "2021-04-02", "album")],
    "Stephen Sanchez":     [("Angel Face", "2023-06-09", "album")],
    "Lizzie McAlpine":     [("the door", "2024-03-01", "album"),
                            ("five seconds flat", "2022-04-08", "album")],
    "bar italia":          [("The Twits", "2023-06-09", "album"),
                            ("Tracey Denim", "2023-02-24", "album")],
    "Barry Can't Swim":    [("When Will We Land?", "2024-03-08", "album")],
    "Nia Archives":        [("Silence Is Loud", "2024-03-08", "album")],
    "Hemlocke Springs":    [("Graduate!", "2024-09-13", "album")],
    "Gracie Abrams":       [("Good Riddance", "2023-02-24", "album")],
    "RIIZE":               [("RIIZE UP", "2023-09-04", "album")],
    "Barry Can't Swim":    [("When Will We Land?", "2024-03-08", "album")],
}

GROUPS = {
    "The Last Dinner Party", "Royel Otis", "Richy Mitch and the Coal Miners",
    "Good Neighbours", "Wasia Project", "The Red Clay Strays", "Snow Strippers",
    "Model/Actriz", "Hotline TNT", "Wednesday", "Say She She", "NewJeans",
    "LE SSERAFIM", "RIIZE", "ZEROBASEONE", "BOYNEXTDOOR", "PLAVE", "XG",
    "QWER", "KATSEYE", "UNIS", "ILLIT", "Babymonster", "Kiss of Life", "TWS",
    "bad invitations", "bar italia", "Geese", "Nation of Language", "Overmono",
    "Skin on Skin", "Fcukers", "Lastlings", "Been Stellar", "Friko", "Wave to Earth",
    "English Teacher", "Zulu", "Scowl", "Militarie Gun", "Gel",
}

KNOWN_DEBUTS = {
    "Chappell Roan": 2017, "Sabrina Carpenter": 2014, "Laufey": 2020,
    "Noah Kahan": 2019, "Zach Bryan": 2019, "Megan Thee Stallion": 2016,
    "Central Cee": 2020, "Ice Spice": 2021, "NewJeans": 2022, "LE SSERAFIM": 2022,
    "Doechii": 2019, "GloRilla": 2022, "Tyla": 2019, "RIIZE": 2023,
    "Gracie Abrams": 2020, "Laufey": 2020, "Wednesday": 2018, "Blondshell": 2022,
    "MJ Lenderman": 2020, "Overmono": 2017, "Barry Can't Swim": 2022,
    "Nia Archives": 2021, "Charlotte Cardin": 2016, "Royel Otis": 2021,
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _dlt_id(*parts: str) -> str:
    return hashlib.md5("|".join(parts).encode()).hexdigest()


def _mbid(artist: str) -> str:
    h = hashlib.md5(artist.encode()).hexdigest()
    return f"{h[:8]}-{h[8:12]}-4{h[13:16]}-a{h[17:20]}-{h[20:32]}"


def _album_id(artist: str, title: str) -> str:
    return hashlib.md5(f"{artist}|{title}".encode()).hexdigest()[:22]


def _listeners_history(base: int, growth_type: str) -> list:
    """14 listener counts oldest→today, ending at `base`.
    Daily noise (±12%) simulates organic fluctuations: bad weeks,
    playlist drops, viral moments."""
    lo, hi = GROWTH[growth_type]
    values = [base]
    for _ in range(DAYS - 1):
        r = random.uniform(lo, hi)
        noise = random.uniform(-0.12, 0.12)
        values.append(max(500, int(values[-1] / (1 + r + noise))))
    values.reverse()
    return values


def _playcount_history(listener_series: list) -> list:
    """Cumulative playcount growing forward from oldest day."""
    base_pc = int(listener_series[0] * random.uniform(50, 160))
    counts = [base_pc]
    for listeners in listener_series[1:]:
        daily_inc = int(listeners * random.uniform(0.006, 0.014))
        counts.append(counts[-1] + daily_inc)
    return counts


# ─── Staging loaders ──────────────────────────────────────────────────────────

def load_lastfm(cur, load_id: str, dates: list):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS staging.stg_lastfm_artists (
            artist_name  varchar NOT NULL,
            mbid         varchar,
            listeners    bigint,
            playcount    bigint,
            url          varchar,
            scraped_at   timestamptz,
            scraped_date varchar NOT NULL,
            _dlt_load_id varchar NOT NULL,
            _dlt_id      varchar NOT NULL
        )
    """)
    # Ensure unique index so ON CONFLICT works
    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS _lfm_dlt_id_uidx
        ON staging.stg_lastfm_artists (_dlt_id)
    """)

    rows = []
    for artist, (base, _, _, growth) in ARTISTS.items():
        hist_l = _listeners_history(base, growth)
        hist_p = _playcount_history(hist_l)
        url = f"https://www.last.fm/music/{artist.replace(' ', '+')}"
        for i, d in enumerate(dates):
            rows.append((
                artist,
                _mbid(artist),
                hist_l[i],
                hist_p[i],
                url,
                datetime(d.year, d.month, d.day, 12, 0, tzinfo=timezone.utc),
                d.isoformat(),
                load_id,
                _dlt_id("lfm", artist, d.isoformat()),
            ))

    psycopg2.extras.execute_values(cur, """
        INSERT INTO staging.stg_lastfm_artists
            (artist_name, mbid, listeners, playcount, url,
             scraped_at, scraped_date, _dlt_load_id, _dlt_id)
        VALUES %s
        ON CONFLICT (_dlt_id) DO UPDATE
            SET listeners    = EXCLUDED.listeners,
                playcount    = EXCLUDED.playcount,
                scraped_at   = EXCLUDED.scraped_at,
                _dlt_load_id = EXCLUDED._dlt_load_id
    """, rows, page_size=500)
    print(f"  stg_lastfm_artists    : {len(rows)} rows  ({DAYS} days × {len(ARTISTS)} artists)")


def load_tags(cur, load_id: str):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS staging.stg_lastfm_artist_tags (
            artist_name  varchar,
            tag_name     varchar,
            tag_count    bigint,
            scraped_at   timestamptz,
            _dlt_load_id varchar NOT NULL,
            _dlt_id      varchar NOT NULL
        )
    """)
    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS stg_lastfm_artist_tags_dlt_id
        ON staging.stg_lastfm_artist_tags (_dlt_id)
    """)

    scraped_at = datetime.now(timezone.utc)
    rows = []
    for artist, (_, _, genres, _) in ARTISTS.items():
        for rank, genre in enumerate(genres):
            count = max(30, 100 - rank * 25)
            rows.append((artist, genre, count, scraped_at, load_id,
                         _dlt_id("tag", artist, genre)))

    psycopg2.extras.execute_values(cur, """
        INSERT INTO staging.stg_lastfm_artist_tags
            (artist_name, tag_name, tag_count, scraped_at, _dlt_load_id, _dlt_id)
        VALUES %s
        ON CONFLICT (_dlt_id) DO NOTHING
    """, rows, page_size=500)
    print(f"  stg_lastfm_artist_tags: {len(rows)} rows")


def load_musicbrainz(cur, load_id: str):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS staging.stg_musicbrainz_artists (
            mbid           varchar NOT NULL,
            name           varchar,
            sort_name      varchar,
            country        varchar,
            disambiguation varchar,
            artist_type    varchar,
            debut_year     smallint,
            scraped_at     timestamptz,
            _dlt_load_id   varchar NOT NULL,
            _dlt_id        varchar NOT NULL
        )
    """)
    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS stg_musicbrainz_artists_dlt_id
        ON staging.stg_musicbrainz_artists (_dlt_id)
    """)

    scraped_at = datetime.now(timezone.utc)
    rows = []
    for artist, (_, country, _, _) in ARTISTS.items():
        debut = KNOWN_DEBUTS.get(artist, random.randint(2017, 2023))
        atype = "Group" if artist in GROUPS else "Person"
        parts = artist.split()
        sort = (f"{parts[-1]}, {' '.join(parts[:-1])}"
                if len(parts) > 1 and atype == "Person" else artist)
        rows.append((
            _mbid(artist), artist, sort, country, "", atype, debut,
            scraped_at, load_id, _dlt_id("mb", artist),
        ))

    psycopg2.extras.execute_values(cur, """
        INSERT INTO staging.stg_musicbrainz_artists
            (mbid, name, sort_name, country, disambiguation, artist_type,
             debut_year, scraped_at, _dlt_load_id, _dlt_id)
        VALUES %s
        ON CONFLICT (_dlt_id) DO NOTHING
    """, rows, page_size=200)
    print(f"  stg_musicbrainz_artists: {len(rows)} rows")


def load_spotify(cur, load_id: str):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS staging.stg_spotify_albums (
            spotify_album_id       varchar NOT NULL,
            spotify_artist_id      varchar,
            artist_name            varchar,
            title                  varchar,
            release_date           varchar,
            release_date_precision varchar,
            album_type             varchar,
            scraped_at             timestamptz,
            _dlt_load_id           varchar NOT NULL,
            _dlt_id                varchar NOT NULL
        )
    """)
    cur.execute("TRUNCATE staging.stg_spotify_albums")

    scraped_at = datetime.now(timezone.utc)
    rows = []
    for artist in ARTISTS:
        sp_artist_id = f"sp{_mbid(artist).replace('-', '')[:16]}"
        albums = KNOWN_ALBUMS.get(artist, [
            (artist, f"{KNOWN_DEBUTS.get(artist, 2022)}-01-01", "album"),
            (f"{artist} — Singles", f"{KNOWN_DEBUTS.get(artist, 2022) + 1}-06-01", "single"),
        ])
        for title, rel_date, alb_type in albums:
            precision = "day" if len(rel_date) == 10 else "year"
            rows.append((
                _album_id(artist, title), sp_artist_id, artist, title,
                rel_date, precision, alb_type,
                scraped_at, load_id, _dlt_id("alb", artist, title),
            ))

    psycopg2.extras.execute_values(cur, """
        INSERT INTO staging.stg_spotify_albums
            (spotify_album_id, spotify_artist_id, artist_name, title,
             release_date, release_date_precision, album_type,
             scraped_at, _dlt_load_id, _dlt_id)
        VALUES %s
    """, rows, page_size=500)
    print(f"  stg_spotify_albums    : {len(rows)} rows")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    today = date.today()
    # End 2 days ago — June 9 is reserved for real Last.fm scrape
    end_date = today - timedelta(days=2)
    dates = [end_date - timedelta(days=i) for i in range(DAYS - 1, -1, -1)]
    load_id = str(datetime.now(timezone.utc).timestamp())

    print(f"Connecting to {DB['host']}:{DB['port']}/{DB['dbname']} ...")
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()

    # Ensure staging schema exists
    cur.execute("CREATE SCHEMA IF NOT EXISTS staging")
    conn.commit()

    print(f"Generating {DAYS} days of data for {len(ARTISTS)} artists "
          f"({dates[0]} -> {dates[-1]}) ...\n")

    load_lastfm(cur, load_id, dates)
    conn.commit()

    load_tags(cur, load_id)
    conn.commit()

    load_musicbrainz(cur, load_id)
    conn.commit()

    load_spotify(cur, load_id)
    conn.commit()

    cur.close()
    conn.close()
    print("\nDone. Next step:")
    print("  cd transform && dbt run --profiles-dir .")


if __name__ == "__main__":
    main()
