from extensions import db
from models import Usuarios, Escolas, Turmas, TiposEnsino, Ano_escolar
from flask import Flask
from urllib.parse import quote_plus

app = Flask(__name__)
password = quote_plus('31952814Gg@')
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://mila_user:{password}@127.0.0.1/mila_educacional'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def verificar_turmas():
    with app.app_context():
        print("\nEstatísticas das Turmas:")
        print("=======================")
        
        total_turmas = db.session.query(Turmas).count()
        print(f"\nTotal de turmas: {total_turmas}")
        
        # Mostrar algumas turmas de exemplo
        print("\nExemplo de 5 turmas:")
        print("===================")
        
        turmas = db.session.query(Turmas).limit(5).all()
        for t in turmas:
            print(f"\nID: {t.id}")
            print(f"Turma: {t.turma}")
            print(f"Código INEP: {t.codigo_inep}")
            print(f"Escola ID: {t.escola_id}")
            print(f"Ano Escolar ID: {t.ano_escolar_id}")
            
            # Buscar nome do ano escolar
            ano = db.session.query(Ano_escolar).filter_by(id=t.ano_escolar_id).first()
            if ano:
                print(f"Ano Escolar: {ano.nome}")
            
            # Buscar tipo de ensino
            tipo = db.session.query(TiposEnsino).filter_by(id=t.tipo_ensino_id).first()
            if tipo:
                print(f"Tipo de Ensino: {tipo.nome}")
            
            # Contar alunos nesta turma
            alunos = db.session.query(Usuarios).filter_by(
                turma_id=t.id,
                tipo_usuario_id=4  # Alunos
            ).count()
            print(f"Total de alunos: {alunos}")
            
            # Mostrar alguns alunos desta turma
            print("Exemplo de alunos:")
            alguns_alunos = db.session.query(Usuarios).filter_by(
                turma_id=t.id,
                tipo_usuario_id=4  # Alunos
            ).limit(3).all()
            for aluno in alguns_alunos:
                print(f"  - {aluno.nome}")
            
        # Verificar turmas sem alunos
        turmas_sem_alunos = db.session.query(Turmas).filter(
            ~Turmas.id.in_(
                db.session.query(Usuarios.turma_id).filter(
                    Usuarios.turma_id.isnot(None),
                    Usuarios.tipo_usuario_id == 4  # Alunos
                )
            )
        ).count()
        print(f"\nTurmas sem alunos: {turmas_sem_alunos}")
        
        # Verificar alunos sem turma
        alunos_sem_turma = db.session.query(Usuarios).filter(
            Usuarios.tipo_usuario_id == 4,  # Alunos
            Usuarios.turma_id.is_(None)
        ).count()
        print(f"Alunos sem turma: {alunos_sem_turma}")

if __name__ == '__main__':
    verificar_turmas()
