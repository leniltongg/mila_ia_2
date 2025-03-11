from extensions import db
from models import Escolas, Usuarios, Turmas
from flask import Flask
from urllib.parse import quote_plus

app = Flask(__name__)

# Configuração do banco de dados
password = quote_plus("31952814Gg@")
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://mila_user:{password}@127.0.0.1/mila_educacional'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

def limpar_escolas(confirmar=False):
    """
    Exclui todos os dados da tabela escolas e registros relacionados.
    
    Args:
        confirmar (bool): Se True, executa a exclusão. Se False, apenas mostra o que seria excluído
    """
    with app.app_context():
        # Primeiro, vamos ver quantos registros seriam excluídos
        total_escolas = Escolas.query.count()
        total_usuarios = Usuarios.query.count()
        total_turmas = Turmas.query.count()
        
        print(f"\nTotal de registros que serão excluídos:")
        print(f"- Escolas: {total_escolas}")
        print(f"- Usuários vinculados: {total_usuarios}")
        print(f"- Turmas vinculadas: {total_turmas}")
        
        if not confirmar:
            print("\nEste foi apenas um teste. Para excluir os registros, execute novamente com confirmar=True")
            return

        try:
            engine = db.get_engine()
            with engine.connect() as conn:
                # Primeiro excluir registros relacionados em simulados_gerados_professor
                result = conn.execute(
                    "DELETE FROM simulados_gerados_professor WHERE professor_id IN (SELECT id FROM usuarios)"
                )
                print(f"Excluídos {result.rowcount} registros de simulados_gerados_professor")
                
                # Excluir registros em banco_questoes
                result = conn.execute("DELETE FROM banco_questoes")
                print(f"Excluídos {result.rowcount} registros de banco_questoes")
                
                # Excluir registros em simulados_enviados
                result = conn.execute("DELETE FROM simulados_enviados")
                print(f"Excluídos {result.rowcount} registros de simulados_enviados")
                
                # Excluir usuários
                result = conn.execute("DELETE FROM usuarios")
                print(f"Excluídos {result.rowcount} usuários")
                
                # Excluir turmas
                result = conn.execute("DELETE FROM turmas")
                print(f"Excluídas {result.rowcount} turmas")
                
                # Por fim, excluir escolas
                result = conn.execute("DELETE FROM escolas")
                print(f"Excluídas {result.rowcount} escolas")
                
                print("\nExclusão concluída com sucesso!")

        except Exception as e:
            print(f"Erro ao excluir registros: {e}")

if __name__ == '__main__':
    # Primeiro rode com confirmar=False para ver o que será excluído
    # limpar_escolas(confirmar=False)
    
    # Depois, se estiver tudo certo, rode com confirmar=True
    limpar_escolas(confirmar=True)
