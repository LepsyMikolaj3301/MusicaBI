import hashlib
from datetime import date
import psycopg2

def _dlt_id(*parts):
    return hashlib.md5("|".join(parts).encode()).hexdigest()

june9 = date(2026, 6, 9).isoformat()

with open("etl/artists.txt") as f:
    artists = [line.strip() for line in f if line.strip()]

ids = [_dlt_id("lfm", a, june9) for a in artists]

conn = psycopg2.connect(dbname="MusicaBi", user="admin", password="admin", host="localhost", port=5432)
cur = conn.cursor()
cur.execute("DELETE FROM staging.stg_lastfm_artists WHERE _dlt_id = ANY(%s)", (ids,))
print(f"Deleted {cur.rowcount} mock June 9 rows (kept real Last.fm data)")
conn.commit()

cur.execute("SELECT scraped_date::date AS date, count(*) FROM staging.stg_lastfm_artists GROUP BY 1 ORDER BY 1")
for row in cur.fetchall():
    print(row)
conn.close()
