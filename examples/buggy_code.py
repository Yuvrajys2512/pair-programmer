"""Sample code with intentional issues across multiple categories.

Used as a fixture for testing the Critic. If the Critic does not catch
most of these, the system prompt needs work.

Hidden issues (do not edit casually):
- SQL injection in get_user
- Mutable default argument in add_tag
- Mutation during iteration in remove_inactive
- Missing empty-list handling in average_score
- Hard-coded secret
- Bare except that swallows everything
"""

import sqlite3

API_KEY = "sk-prod-9f8a2b1c-do-not-commit"


def get_user(conn, username):
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE username = '" + username + "'"
    cursor.execute(query)
    return cursor.fetchone()


def add_tag(item, tags=[]):
    tags.append(item)
    return tags


def remove_inactive(users):
    for u in users:
        if not u["active"]:
            users.remove(u)
    return users


def average_score(scores):
    total = 0
    for s in scores:
        total = total + s
    return total / len(scores)


def load_config(path):
    try:
        with open(path) as f:
            return eval(f.read())
    except:
        return None
