-- users
-- pwd: 12345678
INSERT INTO app_user (user_id, username, is_active, first_name, last_name, email, password_hash)
    VALUES (1, 'alice', true, 'Alice', 'Alicelast', 'alice@alice.com', '$2b$12$g7TibWQNvUasqbOcqzcYMuvTw7YyEYHMg0jhJcSUf1Ml9HSsIT3DO'),
           (2, 'bob', true, 'Bob', 'Boblast', 'bob@bob.com', '$2b$12$g7TibWQNvUasqbOcqzcYMuvTw7YyEYHMg0jhJcSUf1Ml9HSsIT3DO'),
           (3, 'charlie', true, 'Charlie', 'Charlast', 'charlie@charlie.com', '$2b$12$g7TibWQNvUasqbOcqzcYMuvTw7YyEYHMg0jhJcSUf1Ml9HSsIT3DO'),

           -- dave is member of alice's and charlie's teams
           (4, 'dave', true, 'Dave', 'Davelast', 'dave@dave.com', '$2b$12$g7TibWQNvUasqbOcqzcYMuvTw7YyEYHMg0jhJcSUf1Ml9HSsIT3DO'),

           -- eve has an expired token
           (5, 'eve', true, 'Eve', 'Evelast', 'eve@eve.com', '$2b$12$g7TibWQNvUasqbOcqzcYMuvTw7YyEYHMg0jhJcSUf1Ml9HSsIT3DO'),

           -- fiona's user is not active (maybe was disabled for misbehaving)
           (6, 'fiona', false, 'fiona', 'Fionalast', 'fiona@fiona.com', '$2b$12$g7TibWQNvUasqbOcqzcYMuvTw7YyEYHMg0jhJcSUf1Ml9HSsIT3DO')
;

-- advance the sequence to avoid 'duplicate key value violates unique constraint app_user_pkey' error
-- https://stackoverflow.com/questions/37970743/postgresql-unique-violation-7-error-duplicate-key-value-violates-unique-const
SELECT setval((SELECT pg_get_serial_sequence('app_user', 'user_id')), (SELECT max(user_id) FROM app_user));


-- teams
INSERT INTO team(team_id, name, creator_id)
    VALUES (1, 'Web Team', 1),
           (2, 'Dev Ops', 3)
;

-- team roles
INSERT INTO team_role(role_name) VALUES ('leader'), ('member');


-- team members
INSERT INTO user_to_team (user_id, team_id, user_role)
    VALUES (1, 1, 'leader'), -- alice is leader of the 'Web Team' team
           (2, 1, 'member'), -- bob
           (4, 1, 'member'), -- dave
           (5, 1, 'member'), -- eve

           (3, 2, 'leader'), -- charlie is the leader of 'Dev Ops' team
           (4, 2, 'member'), -- dave
           (6, 2, 'member')  -- fiona
;

-- token
INSERT INTO token (user_id, token, expires_at)
    VALUES (1, 'alice-token',   '2030-01-01 00:00:00'::timestamptz),
           (2, 'bob-token',     '2030-01-01 00:00:00'::timestamptz),
           (3, 'charlie-token', '2030-01-01 00:00:00'::timestamptz),
           (4, 'dave-token',    '2030-01-01 00:00:00'::timestamptz),

           -- expired
           (5, 'eve-token',     '1999-01-01 00:00:00'::timestamptz)
;

INSERT INTO project (project_id, team_id, name)
    VALUES
           (1, 1, 'Web Team Sprint #100'),
           (2, 2, 'DevOps Tasks')
;

INSERT INTO task (task_id, status, created_by, assignee_id, due_date, estimation, team_id, project_id, description, name)
    VALUES
            -- Web Team (alice, bob, dave, eve)
           (1, 'todo',      1, 1, NULL, NULL, 1, 1, DEFAULT, 'add header'),                                 -- alice
           (2, 'todo',      1, 2, NULL, NULL, 1, 1, DEFAULT, 'fix user cant log in'),                       -- alice
           (3, 'todo',      2, 2, NULL, NULL, 1, 1, DEFAULT, 'write tests for the profile update feature'), -- bob
           (4, 'completed', 4, 4, NULL, NULL, 1, 1, DEFAULT, 'deploy version to dev environment'),          -- dave
           (5, 'todo',      5, 5, NULL, NULL, 1, 1, DEFAULT, 'change link color to purple'),                -- eve

           -- Dev Ops (charlie, dave, fiona)
           (100, 'in_progress', 3, 3, NULL, NULL, 2, 2, DEFAULT, 'fix Dockerfile'),                         -- charlie
           (101, 'todo',        4, 4, NULL, NULL, 2, 2, DEFAULT, 'configure nginx'),                        -- dave
           (102, 'archived',    6, 6, NULL, NULL, 2, 2, DEFAULT, 'rm -rf everything')                       -- fiona
;
SELECT setval((SELECT pg_get_serial_sequence('task', 'task_id')), (SELECT max(task_id) FROM task));

INSERT INTO task_time_entry(time_entry_id, task_id, assignee_id, start_datetime, end_datetime)
    VALUES -- Web Team
            (1, 1, 1, now(), NULL),                                             -- alice
            (2, 3, 2, now(), NULL),                                             -- bob
            (4, 4, 4, now() - '1 day'::interval, now()),                        -- dave
            (5, 5, 5, now() - '1 day'::interval, now() - '4 hours'::interval),  -- eve

            -- Dev Ops Team
            (100, 100, 3, now(), NULL),                                         -- charlie
            (101, 102, 6, now() - '1 day'::interval, NULL),                     -- fiona
            (102, 101, 4, now(), NULL)                                          -- dave
;
SELECT setval((SELECT pg_get_serial_sequence('task_time_entry', 'time_entry_id')), (SELECT max(time_entry_id) FROM task_time_entry));
