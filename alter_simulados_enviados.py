from app_db import db

# Remover a chave estrangeira antiga
drop_fk = """
ALTER TABLE simulados_enviados 
DROP FOREIGN KEY simulados_enviados_ibfk_1;
"""

# Modificar a coluna simulado_id para aceitar ambos os tipos de simulados
modify_column = """
ALTER TABLE simulados_enviados
MODIFY COLUMN simulado_id INT NOT NULL;
"""

# Executar as alterações
with db.engine.connect() as conn:
    conn.execute(drop_fk)
    conn.execute(modify_column)
    print("Alterações realizadas com sucesso!")
