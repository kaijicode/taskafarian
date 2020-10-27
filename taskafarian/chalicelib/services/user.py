from chalicelib.core.database import get_db


def get_teams(user_id: int):
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute('''
        SELECT team_id, user_role
        FROM user_to_team
        WHERE user_id = %(user_id)s
        ;
        ''', {'user_id': user_id})
        return cursor.fetchall()


def get_user_role_in_team(user_id: int, team_id: int):
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute('''
        SELECT user_role
        FROM user_to_team
        WHERE user_id = %(user_id)s AND team_id = %(team_id)s
        ;
        ''', {'user_id': user_id, 'team_id': team_id})
        return cursor.fetchone()
