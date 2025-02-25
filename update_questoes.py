from app_db import db, Usuarios, BancoQuestoes, app

def update_questoes_codigo_ibge():
    try:
        # Buscar o código IBGE do usuário
        usuario = Usuarios.query.filter_by(email='seduc@email.com').first()
        if not usuario or not usuario.codigo_ibge:
            print("Usuário não encontrado ou sem código IBGE")
            return
        
        # Atualizar todas as questões com o código IBGE do usuário
        questoes = BancoQuestoes.query.all()
        for questao in questoes:
            questao.codigo_ibge = usuario.codigo_ibge
        
        # Salvar as alterações
        db.session.commit()
        print(f"Atualizado {len(questoes)} questões com o código IBGE {usuario.codigo_ibge}")
        
    except Exception as e:
        print(f"Erro ao atualizar questões: {str(e)}")
        db.session.rollback()

if __name__ == '__main__':
    with app.app_context():
        update_questoes_codigo_ibge()
