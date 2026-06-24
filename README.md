# MusicaBI
MusicaBI - interaktywny dashboard do analizy danych muzycznych i artystów (Projekt SBI - grupa D).

---

## 1. Budowanie i Uruchomienie (BUILD)

Aby zbudować i uruchomić całe środowisko w tle, wykonaj w głównym katalogu:
```bash
docker compose up --build -d
```

### Ważne wskazówki przed uruchomieniem:
* **Czysty start (Reset bazy):** Jeśli chcesz całkowicie usunąć dane z bazy i zacząć od zera:
  ```bash
  docker compose down --volumes
  ```

---

## 2. Panel Airflow (Logowanie i Uruchamianie)

* **Adres:** [http://localhost:8080](http://localhost:8080)
* **Login:** `admin`
* **Odczytanie hasła:** (wygenerowane losowo przy starcie kontenera):
  ```bash
  docker exec airflow_musicabi cat /opt/airflow/simple_auth_manager_passwords.json.generated
  ```

### Uruchamianie potoku (DAG):
1. Używaj wyłącznie DAG-a o nazwie **`music_pipeline`** (drugi DAG `lastfm_pipeline` to nieaktywny szablon).
2. Potok możesz wyzwolić w panelu Airflow (klikając **Trigger**) lub bezpośrednio z konsoli:
   ```bash
   docker exec airflow_musicabi airflow dags trigger music_pipeline
   ```
*Zadanie Spotify oraz Google Trends są automatycznie mockowane, dzięki czemu potok przechodzi w pełni na zielono bez kluczy API, pobierając jednocześnie prawdziwe dane z Last.fm oraz MusicBrainz.*

### Generowanie / Aktualizacja Mocka Spotify:
Atrapa Spotify wczytuje dane z pliku `etl/sources/spotify_mock.json`. Aby wygenerować lub zaktualizować ten plik (np. po modyfikacji listy w `etl/artists.txt`), uruchom na swoim komputerze:
```bash
uv run python scratch/generate_spotify_mock.py
```

---

## 3. Baza Danych Postgres (Logowanie przez pgAdmin)

1. Wejdź na adres: [http://localhost:5050](http://localhost:5050)
2. Zaloguj się do pgAdmina:
   * **Email:** `musicabi@sysbi.com`
   * **Hasło:** `musicabi`
3. Aby dodać i połączyć się z serwerem Postgres w pgAdminie (kliknij *Add New Server* -> zakładka *Connection*):
   * **Host name/address:** `postgres` *(Używamy nazwy kontenera w sieci Dockera, a nie localhost!)*
   * **Port:** `5432`
   * **Maintenance database:** `MusicaBi`
   * **Username:** `admin`
   * **Password:** `admin`