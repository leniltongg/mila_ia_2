from app_db import db, app

with app.app_context():
    with db.engine.connect() as conn:
        conn.execute(db.text("ALTER TABLE simulados_gerados ADD COLUMN codigo_ibge VARCHAR(10);"))
        conn.commit()
        print("Coluna adicionada com sucesso!")
