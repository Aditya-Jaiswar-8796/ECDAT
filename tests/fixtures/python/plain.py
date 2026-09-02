# tests/fixtures/python/plain.py
def total(items):
    return sum(items)


def name_of(user):
    if user:
        return user.get("name", "unknown")
    return "unknown"