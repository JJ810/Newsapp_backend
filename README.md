<!-- BACKEND COMMANDS -->

Filtering: `pip install django-filter==2.0` must install
Start server: `manage.py runserver`
Migrate: `manage.py migrate`
Start Migrations: `manage.py makemigrations`
In case of database re migrate: `manage.py migrate --run-syncdb`

TO CREATE SUPER USER FROM BACKEND

1. python manage.py createsuperuser
2. Username: ola
3. Email address: ola@example.com
4. Password:
5. Password (again):
   Superuser created successfully.

You can access the backend admin here:
localhost:8000/admin


#### Running Django server

Setup-I
```
pip install pipenv
pipenv shell
pip install django djoser djangorestframework django-rest-swagger django-allauth django-rest-auth django-filter
```
Or Setup-II
```
python3 -m virtualenv venv
source venv/bin/activate
pip3 install -r requirements.txt
```

Run migrations
```
manage.py migrate
manage.py migrate --run-syncdb
```

Start Server
```
manage.py runserver
```

#### Running Tests
```
nosetests
```
