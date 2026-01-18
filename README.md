This readme and project are a work in progress. (This is effectively my notepad for this project.)

## SSL
To create a self-signed SSL certificate for local development, you can use the following OpenSSL command:

```bash
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
```


## Babel Translation Commands
```
Create messages.pot:
pybabel extract -F babel.cfg -k _l -o messages.pot .

Create Catalog:
pybabel init -i messages.pot -d main/translations -l en

Compile Catalog:
pybabel compile -d main/translations


babel.cfg:
[python: main/**.py]


[jinja2: main/templates/**.html]
```
