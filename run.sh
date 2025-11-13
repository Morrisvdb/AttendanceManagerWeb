# git pull

python3 -m venv .

source ./bin/activate

pip install -r requirements.txt

export set FLASK_APP=main.app

flask run --host 0.0.0.0 --port 5002 --debug
