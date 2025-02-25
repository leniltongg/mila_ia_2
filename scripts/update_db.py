import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_factory import create_app
from models import db
from populate_Ano_escolar import populate_Ano_escolar

def update_database():
    """Atualiza o banco de dados com as novas tabelas e popula os dados iniciais."""
    app = create_app()
    
    with app.app_context():
        # Criar todas as tabelas
        db.create_all()
        
        # Popular tabela de séries
        populate_Ano_escolar()
        
        print("Banco de dados atualizado com sucesso!")

if __name__ == '__main__':
    update_database()
