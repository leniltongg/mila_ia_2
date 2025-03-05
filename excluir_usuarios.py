from extensions import db
from models import Usuarios
from flask import Flask
from urllib.parse import quote_plus

app = Flask(__name__)
password = quote_plus('31952814Gg@')
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://mila_user:{password}@127.0.0.1/mila_educacional'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def excluir_usuarios(id_inicio, id_fim, confirmar=False):
    with app.app_context():
        # Primeiro, vamos verificar quantos usuários serão afetados
        usuarios = db.session.query(Usuarios).filter(
            Usuarios.id >= id_inicio,
            Usuarios.id <= id_fim
        ).all()
        
        print(f"\nTotal de usuários no intervalo: {len(usuarios)}")
        print("\nPrimeiros 5 usuários que serão excluídos:")
        for i, usuario in enumerate(usuarios[:5]):
            print(f"{i+1}. ID: {usuario.id}")
            print(f"   Nome: {usuario.nome}")
            print(f"   CPF: {usuario.cpf}")
            print(f"   Email: {usuario.email}")
            print(f"   Escola ID: {usuario.escola_id}")
            print()
            
        if len(usuarios) > 5:
            print("...")
            
        if not confirmar:
            print("\nEste é um teste seguro. Para realmente excluir os usuários, execute novamente com confirmar=True")
            return
            
        try:
            # Excluir em lotes de 1000 para não sobrecarregar o banco
            lote_size = 1000
            total_excluidos = 0
            
            for i in range(0, len(usuarios), lote_size):
                lote = usuarios[i:i + lote_size]
                ids_lote = [u.id for u in lote]
                
                db.session.query(Usuarios).filter(
                    Usuarios.id.in_(ids_lote)
                ).delete(synchronize_session=False)
                
                total_excluidos += len(lote)
                print(f"Excluídos {total_excluidos} de {len(usuarios)} usuários...")
                
                # Commit a cada lote
                db.session.commit()
                
            print(f"\nOperação concluída! {total_excluidos} usuários foram excluídos com sucesso.")
            
        except Exception as e:
            db.session.rollback()
            print(f"Erro ao excluir usuários: {str(e)}")
            raise

if __name__ == '__main__':
    # Exemplo de uso:
    # Primeiro rode sem confirmar para ver quais usuários serão afetados
    # excluir_usuarios(24212, 107405, confirmar=False)
    
    # Depois, se os usuários estiverem corretos, rode com confirmar=True
    excluir_usuarios(24212, 107405, confirmar=True)
