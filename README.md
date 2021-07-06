# TW-Harvest-Project-Integ

This project integrates our TeamworkPM and Harvest web applications. It syncs companies, project names, people assigned, and time spent on projects.

## Setup
With [Virtualenv](https://virtualenv.readthedocs.org/en/latest/), run:
```shell
$ virtualenv teamwork-venv-2.7 && cd "$_" && source bin/activate
```

Configure ``settings_local.py`` + install app dependencies:
```shell
$ settings='settings_local'
$ cd src && pip install -r requirements.txt
$ cp "${settings}.templ.py" "${settings}.py"
```

Build the Teamwork database:
```shell
$ python manage.py setup_db
```

## Webhook Info
Note -- ``webhook.py`` is triggered on POST by five events:
* PROJECT.CREATED
* PROJECT.UPDATED
* PROJECT.COPIED
* COMPANY.CREATED
* COMPANY.UPDATED

## Requirements
Python 2.7
Flask 1.1.4
Flask-Script 2.0.5
Requests 1.1.0
