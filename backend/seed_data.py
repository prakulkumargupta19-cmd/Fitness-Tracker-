"""Legacy demo seeding is disabled; application identities are real signups."""


def seed():
    raise RuntimeError("Demo user seeding is disabled. Create accounts through the application.")


if __name__ == "__main__":
    seed()
