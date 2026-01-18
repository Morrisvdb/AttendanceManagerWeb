git pull

python3 -m venv .

source ./bin/activate

pip install -r requirements.txt

export set FLASK_APP=main.app

gunicorn -c main/gunicorn_config.py main.app:app --certfile=cert.pem --keyfile=key.pem