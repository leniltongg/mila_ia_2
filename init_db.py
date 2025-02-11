from create_app import create_app
from models import db, User, Cidade, Escola

def create_initial_data():
    # Criando cidades
    recife = Cidade(
        nome='Recife',
        codigo_ibge='2611606',
        uf='PE'
    )
    olinda = Cidade(
        nome='Olinda',
        codigo_ibge='2609600',
        uf='PE'
    )
    db.session.add(recife)
    db.session.add(olinda)
    db.session.commit()

    # Criando usuário admin
    admin = User(
        nome='Administrador',
        email='admin@example.com',
        senha='admin123',
        tipo_usuario_id=1
    )
    db.session.add(admin)
    db.session.commit()

    # Criando escolas
    escola1 = Escola(
        nome='Escola Municipal João da Silva',
        codigo_inep='26123456',
        cep='50000000',
        logradouro='Rua das Flores',
        numero='123',
        bairro='Centro',
        cidade_id=1,
        tem_fundamental_1=True,
        tem_fundamental_2=True,
        tem_medio=False,
        tem_eja=False,
        tem_tecnico=False
    )
    escola2 = Escola(
        nome='Escola Municipal Maria dos Santos',
        codigo_inep='26123457',
        cep='50100000',
        logradouro='Av Principal',
        numero='456',
        complemento='Bloco A',
        bairro='Boa Vista',
        cidade_id=2,
        tem_fundamental_1=True,
        tem_fundamental_2=True,
        tem_medio=True,
        tem_eja=True,
        tem_tecnico=False
    )
    db.session.add(escola1)
    db.session.add(escola2)
    db.session.commit()

    # Criando usuário secretaria
    secretaria = User(
        nome='Secretaria de Educação',
        email='secretaria@example.com',
        senha='secretaria123',
        tipo_usuario_id=5,
        cidade_id=1
    )
    db.session.add(secretaria)
    db.session.commit()

    # Criando usuário escola
    escola_user = User(
        nome='Diretor João da Silva',
        email='escola@example.com',
        senha='escola123',
        tipo_usuario_id=2,
        escola_id=1
    )
    db.session.add(escola_user)
    db.session.commit()

    # Criando usuário professor
    professor = User(
        nome='Professor José Santos',
        email='professor@example.com',
        senha='professor123',
        tipo_usuario_id=3,
        escola_id=1
    )
    db.session.add(professor)
    db.session.commit()

    # Criando usuário aluno
    aluno = User(
        nome='Aluno Pedro Silva',
        email='aluno@example.com',
        senha='aluno123',
        tipo_usuario_id=4,
        escola_id=1
    )
    db.session.add(aluno)
    db.session.commit()

def init_db():
    app = create_app()
    with app.app_context():
        db.drop_all()
        db.create_all()
        create_initial_data()

if __name__ == '__main__':
    init_db()
