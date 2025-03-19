from create_app import create_app
from models import db
import pymysql
from dotenv import load_dotenv

def update_schema():
    app = create_app()
    with app.app_context():
        # Conectar ao MySQL
        mysql_conn = pymysql.connect(
            host='127.0.0.1',
            user='mila_user',
            password='31952814Gg@',
            database='mila_educacional'
        )
        mysql_cursor = mysql_conn.cursor()

        try:
            # Desabilitar verificação de chave estrangeira temporariamente
            mysql_cursor.execute("SET FOREIGN_KEY_CHECKS=0")

            # Recria todas as tabelas
            db.drop_all()
            db.create_all()

            # Habilitar verificação de chave estrangeira novamente
            mysql_cursor.execute("SET FOREIGN_KEY_CHECKS=1")

            print("Esquema do banco de dados atualizado com sucesso!")

        except Exception as e:
            print(f"Erro ao atualizar o esquema: {str(e)}")
            raise
        finally:
            mysql_cursor.close()
            mysql_conn.close()

if __name__ == '__main__':
    update_schema()
