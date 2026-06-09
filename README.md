# MusicaBI
MusicaBI - interaktywny dashboard do danych analizy danych muzycznych i artystów. Projekt SBI - grupa D


## BUILD
In main directory run
`docker compose up --build`


## HOW TO LOGIN TO AIRFLOW !!!
Paste this **after building the container**
`docker exec airflow_musicabi cat /opt/airflow/simple_auth_manager_passwords.json.generated`

The output is:
`{"login": "password_random"}`