# taskafarian
REST API for imaginary task management app built using Chalice, raw SQL and PostgreSQL for the AWS Lambda platform. 
A toy project for learning purposes.

#### Development
```
cd taskafarian

python3 -m venv venv
. venv/bin/activate

pip install pip-tools
pip install -r taskafarian/requirements.txt
pip install -r taskafarian/dev-requirements.txt

cd taskafarian/taskafarian
# postgres
docker-compose up

# chalice local development server
chalice local --stage local

# tests
pytest

# psql 
docker-compose exec postgresql /bin/bash
psql -h 0.0.0.0 -p 5555 --username taskafarian --password
```

#### Routes
```
GET     /health

POST    /auth/register
POST    /auth/log-in
POST    /auth/activate
POST    /auth/password/request-reset
POST    /auth/password/reset
DELETE  /auth/log-out

POST    /task
GET     /task
GET     /task/<id>
DELETE  /task/<id>
PATCH   /task/<id>

POST    /time-entry
PATCH   /time-entry/<id>
DELETE  /time-entry/<id>
```

#### Deployment
- See [Creating Your Project](https://aws.github.io/chalice/quickstart.html#creating-your-project).
- Setup PostgreSQL on EC2 and make sure the security group (`subnet_ids` & `security_group_ids`) are specified in `.chalice/config.json` correctly.
- Create role, database and schema

Note that `.chalice` directory is in .gitignore so it is not part of the project source code.


#### Examples
##### Log in
```
echo '{"username": "alice", "password": "12345678"}' | http post localhost:8000/auth/log-in
```
```json
{
    "expiresAt": "2020-10-28T07:49:07.074354+00:00",
    "token": "5a8f4c2daf1fccca3df8365bd95b11b2909602d0ec2f157026386cbb24eb1678"
}
```


##### Add new task 
```
echo '{"name": "fix that", "status": "todo"}' | http post localhost:8000/task "Authorization: Bearer 5a8f4c2daf1fccca3df8365bd95b11b2909602d0ec2f157026386cbb24eb1678"
```

```json
{
    "assignee": {
        "firstName": null,
        "lastName": null,
        "userId": null,
        "username": null
    },
    "createdAt": "2020-10-28T06:47:14.103068+00:00",
    "creator": {
        "firstName": "Alice",
        "lastName": "Alicelast",
        "userId": 1,
        "username": "alice"
    },
    "description": "",
    "dueDate": null,
    "estimation": null,
    "name": "fix that",
    "projectId": null,
    "status": "todo",
    "taskId": 103,
    "teamId": null
}
```


##### Fetch tasks
```
http get localhost:8000/task "Authorization: Bearer 5a8f4c2daf1fccca3df8365bd95b11b2909602d0ec2f157026386cbb24eb1678"
```

```json
{
    "meta": {
        "offset": 0,
        "count": 3,
        "limit": 20
    },
    "entities": [
        {
            "dueDate": null,
            "name": "fix that",
            "teamId": null,
            "assignee": {
                "lastName": null,
                "firstName": null,
                "userId": null,
                "username": null
            },
            "createdAt": "2020-10-28T06:47:14.103068+00:00",
            "status": "todo",
            "projectId": null,
            "description": "",
            "taskId": 103
            "creator": {
                "lastName": "Alicelast",
                "firstName": "Alice",
                "userId": 1,
                "username": "alice"
            },
            "estimation": null,
            "timeEntries": []
        },
        {
            "dueDate": null,
            "name": "add header",
            "teamId": 1,
            "assignee": {
                "lastName": "Alicelast",
                "firstName": "Alice",
                "userId": 1,
                "username": "alice"
            },
            "createdAt": "2020-10-28T06:15:24.315171+00:00",
            "status": "todo",
            "projectId": 1,
            "description": "",
            "taskId": 1,
            "creator": {
                "lastName": "Alicelast",
                "firstName": "Alice",
                "userId": 1,
                "username": "alice"
            },
            "estimation": null,
            "timeEntries": [
                {
                    "endDatetime": null,
                    "startDatetime": "2020-10-28T06:15:24.318846+00:00",
                    "timeEntryId": 1,
                    "assigneeId": 1,
                    "taskId": 1
                }
            ]
        },
        {
            "dueDate": null,
            "name": "fix user cant log in",
            "teamId": 1,
            "assignee": {
                "lastName": "Boblast",
                "firstName": "Bob",
                "userId": 2,
                "username": "bob"
            },
            "createdAt": "2020-10-28T06:15:24.315171+00:00",
            "status": "todo",
            "projectId": 1,
            "description": "",
            "taskId": 2,
            "creator": {
                "lastName": "Alicelast",
                "firstName": "Alice",
                "userId": 1,
                "username": "alice"
            },
            "estimation": null,
            "timeEntries": []
        }
    ]
}
```

##### Fetch task by id
```
http get localhost:8000/task/1 "Authorization: Bearer 5a8f4c2daf1fccca3df8365bd95b11b2909602d0ec2f157026386cbb24eb1678"
```
```json
{
    "assignee": {
        "firstName": "Alice",
        "lastName": "Alicelast",
        "userId": 1,
        "username": "alice"
    },
    "createdAt": "2020-10-28T06:15:24.315171+00:00",
    "creator": {
        "firstName": "Alice",
        "lastName": "Alicelast",
        "userId": 1,
        "username": "alice"
    },
    "description": "",
    "dueDate": null,
    "estimation": null,
    "name": "add header",
    "projectId": 1,
    "status": "todo",
    "taskId": 1,
    "teamId": 1
}
```

#### Add new time entry for the task
```
echo '{"taskId": 1, "startDatetime": "2020-10-28T09:08:12.082450+00:00", "assigneeId": 1}' | http post localhost:8000/time-entry "Authorization: Bearer b9bccc7def66b0a1ff09031b7972b145c44ac78bc49f74d3845881678fbd6a98"
```

```json
{
    "assigneeId": 1,
    "endDatetime": null,
    "startDatetime": "2020-10-28T09:08:12.082450+00:00",
    "taskId": 1,
    "timeEntryId": 103
}
```

#### Thoughts / Improvements
- See TODO's in the source code
- database connection is closed after each request, consider keeping it alive to improve performance (`taskafarian/chalicelib/core/__init__.py`)
- `bcrypt` is used for password hashing, is it has noticeable impact on performance? (adjust the "work factor"?)
- all ids should be obfuscated 