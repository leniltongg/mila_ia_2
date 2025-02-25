from app_new import app, db
from models import MESES

def update_meses():
    with app.app_context():
        # Criar um dicionário com o mapeamento de mês para ID
        mes_para_id = {
            'Janeiro': 1,
            'Fevereiro': 2,
            'Março': 3,
            'Abril': 4,
            'Maio': 5,
            'Junho': 6,
            'Julho': 7,
            'Agosto': 8,
            'Setembro': 9,
            'Outubro': 10,
            'Novembro': 11,
            'Dezembro': 12
        }
        
        # Buscar todos os meses
        meses = MESES.query.all()
        
        # Atualizar os IDs
        for mes in meses:
            novo_id = mes_para_id.get(mes.nome)
            if novo_id:
                mes.id = novo_id
        
        # Salvar as alterações
        try:
            db.session.commit()
            print("Meses atualizados com sucesso!")
        except Exception as e:
            db.session.rollback()
            print(f"Erro ao atualizar meses: {e}")

if __name__ == '__main__':
    update_meses()
