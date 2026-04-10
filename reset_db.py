from sqlalchemy import create_engine, text

engine = create_engine("postgresql+psycopg://validator:password@localhost:5432/rules_db", isolation_level="AUTOCOMMIT")
with engine.begin() as conn:
    print("Dropping tables...")
    conn.execute(text("DROP TABLE IF EXISTS test_encounters CASCADE;"))
    conn.execute(text("DROP TABLE IF EXISTS rule_nodes CASCADE;"))

with engine.begin() as conn:
    print("Creating tables...")
    with open("init.sql", "r") as f:
        # execute multiple statements, sqlalchemy text might choke on this, better to run raw connection
        raw_conn = engine.raw_connection()
        try:
            with raw_conn.cursor() as cur:
                cur.execute(f.read())
            raw_conn.commit()
        finally:
            raw_conn.close()

    print("Success")

with engine.connect() as conn:
    res = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'rule_nodes'")).fetchall()
    print("rule_nodes columns:", [r[0] for r in res])
