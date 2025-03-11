from extensions import db
from models import Usuarios
from flask import Flask
from urllib.parse import quote_plus

app = Flask(__name__)

# Configuração do banco de dados
password = quote_plus("31952814Gg@")
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://mila_user:{password}@127.0.0.1/mila_educacional'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

def excluir_usuarios(id_inicial, id_final, confirmar=False):
    """
    Exclui usuários dentro do intervalo especificado.
    
    Args:
        id_inicial (int): ID inicial do intervalo de usuários a serem excluídos
        id_final (int): ID final do intervalo de usuários a serem excluídos
        confirmar (bool): Se True, executa a exclusão. Se False, apenas mostra o que seria excluído
    """
    with app.app_context():
        # Primeiro, vamos ver quais usuários seriam excluídos
        usuarios = Usuarios.query.filter(
            Usuarios.id.between(id_inicial, id_final)
        ).order_by(Usuarios.id).all()
        
        print(f"\nTotal de usuários no intervalo: {len(usuarios)}")
        print("\nPrimeiros 5 usuários que serão excluídos:")
        for i, usuario in enumerate(usuarios[:5], 1):
            print(f"{i}. ID: {usuario.id}")
            print(f"   Nome: {usuario.nome}")
            print(f"   CPF: {usuario.cpf}")
            print(f"   Email: {usuario.email}")
            print(f"   Escola ID: {usuario.escola_id}\n")
        
        if not confirmar:
            print("\nEste foi apenas um teste. Para excluir os usuários, execute novamente com confirmar=True")
            return

        try:
            # Primeiro excluir registros relacionados
            engine = db.get_engine()
            with engine.connect() as conn:
                # Excluir de simulados_gerados_professor
                result = conn.execute(
                    f"DELETE FROM simulados_gerados_professor WHERE professor_id BETWEEN {id_inicial} AND {id_final}"
                )
                print(f"Excluídos {result.rowcount} registros de simulados_gerados_professor")
                
                # Excluir de simulados_enviados
                result = conn.execute(
                    f"DELETE FROM simulados_enviados WHERE usuario_id BETWEEN {id_inicial} AND {id_final}"
                )
                print(f"Excluídos {result.rowcount} registros de simulados_enviados")
                
                # Excluir de respostas_simulado
                result = conn.execute(
                    f"DELETE FROM respostas_simulado WHERE usuario_id BETWEEN {id_inicial} AND {id_final}"
                )
                print(f"Excluídos {result.rowcount} registros de respostas_simulado")
                
                # Por fim, excluir os usuários
                result = conn.execute(
                    f"DELETE FROM usuarios WHERE id BETWEEN {id_inicial} AND {id_final}"
                )
                print(f"Excluídos {result.rowcount} usuários")
                
                conn.commit()
                print("\nExclusão concluída com sucesso!")

        except Exception as e:
            print(f"Erro ao excluir usuários: {e}")
            if 'conn' in locals():
                conn.rollback()

if __name__ == '__main__':
    # Primeiro rode com confirmar=False para ver quais usuários serão excluídos
    # excluir_usuarios(18, 19, confirmar=False)
    
    # Depois, se os usuários estiverem corretos, rode com confirmar=True
    excluir_usuarios(167054, 217052, confirmar=True)
