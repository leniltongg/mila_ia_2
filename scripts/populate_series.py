from models import db, Ano_escolar

def populate_Ano_escolar():
    """Popula a tabela de séries com os dados iniciais."""
    Ano_escolar_data = [
        # Ensino Fundamental 1
        {'nome': '1º Ano', 'nivel_ensino': 'fundamental_1', 'ordem': 1},
        {'nome': '2º Ano', 'nivel_ensino': 'fundamental_1', 'ordem': 2},
        {'nome': '3º Ano', 'nivel_ensino': 'fundamental_1', 'ordem': 3},
        {'nome': '4º Ano', 'nivel_ensino': 'fundamental_1', 'ordem': 4},
        {'nome': '5º Ano', 'nivel_ensino': 'fundamental_1', 'ordem': 5},
        
        # Ensino Fundamental 2
        {'nome': '6º Ano', 'nivel_ensino': 'fundamental_2', 'ordem': 6},
        {'nome': '7º Ano', 'nivel_ensino': 'fundamental_2', 'ordem': 7},
        {'nome': '8º Ano', 'nivel_ensino': 'fundamental_2', 'ordem': 8},
        {'nome': '9º Ano', 'nivel_ensino': 'fundamental_2', 'ordem': 9},
        
        # Ensino Médio
        {'nome': '1º Ano', 'nivel_ensino': 'medio', 'ordem': 10},
        {'nome': '2º Ano', 'nivel_ensino': 'medio', 'ordem': 11},
        {'nome': '3º Ano', 'nivel_ensino': 'medio', 'ordem': 12},
        
        # EJA
        {'nome': 'EJA - Fase 1', 'nivel_ensino': 'eja', 'ordem': 13},
        {'nome': 'EJA - Fase 2', 'nivel_ensino': 'eja', 'ordem': 14},
        {'nome': 'EJA - Fase 3', 'nivel_ensino': 'eja', 'ordem': 15},
        {'nome': 'EJA - Fase 4', 'nivel_ensino': 'eja', 'ordem': 16},
    ]
    
    for Ano_escolar_info in Ano_escolar_data:
        Ano_escolar = Ano_escolar(**Ano_escolar_info)
        db.session.add(Ano_escolar)
    
    try:
        db.session.commit()
        print("Ano Escolars populadas com sucesso!")
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao popular séries: {str(e)}")

if __name__ == '__main__':
    populate_Ano_escolar()
