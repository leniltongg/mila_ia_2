from flask import Flask
from urllib.parse import quote_plus
from extensions import db
from models import DesempenhoSimulado, SimuladosGerados, Usuarios
from sqlalchemy import func, and_

app = Flask(__name__)
password = quote_plus('31952814Gg@')
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://mila_user:{password}@127.0.0.1/mila_educacional'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def verificar_dados_desempenho():
    with app.app_context():
        # 1. Total de registros em DesempenhoSimulado
        total_desempenho = db.session.query(DesempenhoSimulado).count()
        print(f"\n1. Total de registros em DesempenhoSimulado: {total_desempenho}")
        
        # Mostrar alguns registros de DesempenhoSimulado e seus alunos
        print("\nAmostra de DesempenhoSimulado com dados do aluno:")
        desempenhos = db.session.query(
            DesempenhoSimulado, 
            Usuarios
        ).join(
            Usuarios,
            Usuarios.id == DesempenhoSimulado.aluno_id
        ).limit(3).all()
        
        for d, u in desempenhos:
            print(f"Desempenho - ID: {d.id}, Aluno ID: {d.aluno_id}, Simulado: {d.simulado_id}, Pontuação: {d.pontuacao}")
            print(f"         - Data: {d.data_resposta}, Tipo usuário (em desempenho): {d.tipo_usuario_id}")
            print(f"Aluno    - ID: {u.id}, Tipo usuário (real): {u.tipo_usuario_id}, Escola: {u.escola_id}")
            print("---")

        # 2. Verificar SimuladosGerados
        print("\nAmostra de SimuladosGerados:")
        simulados = db.session.query(SimuladosGerados).limit(3).all()
        for s in simulados:
            print(f"ID: {s.id}, Status: {s.status}, Mês: {s.mes_id}, Disciplina: {s.disciplina_id}")

        # 3. Verificar total de alunos
        total_alunos = db.session.query(Usuarios).filter(Usuarios.tipo_usuario_id == 4).count()
        print(f"\n3. Total de usuários do tipo aluno (tipo_usuario_id = 4): {total_alunos}")

        # 4. Verificar join completo (usando tipo_usuario_id correto da tabela Usuarios)
        query_base = db.session.query(
            DesempenhoSimulado,
            SimuladosGerados,
            Usuarios
        ).select_from(DesempenhoSimulado).join(
            SimuladosGerados,
            SimuladosGerados.id == DesempenhoSimulado.simulado_id
        ).join(
            Usuarios,
            and_(
                Usuarios.id == DesempenhoSimulado.aluno_id,
                Usuarios.tipo_usuario_id == 4  # Tipo aluno na tabela Usuarios
            )
        )
        
        total_join = query_base.count()
        print(f"\n4. Total de registros com joins (apenas alunos): {total_join}")
        
        # Mostrar exemplo do join
        amostra = query_base.first()
        if amostra:
            d, s, u = amostra
            print(f"\nExemplo de registro:")
            print(f"Desempenho - ID: {d.id}, Pontuação: {d.pontuacao}, Data: {d.data_resposta}")
            print(f"         - Tipo usuário (em desempenho): {d.tipo_usuario_id}")
            print(f"Simulado - ID: {s.id}, Status: {s.status}, Mês: {s.mes_id}, Disciplina: {s.disciplina_id}")
            print(f"Aluno    - ID: {u.id}, Tipo usuário (real): {u.tipo_usuario_id}, Escola: {u.escola_id}")

        # 5. Verificar registros com data_resposta
        query_final = query_base.filter(
            DesempenhoSimulado.data_resposta.isnot(None)
        )
        
        total_final = query_final.count()
        print(f"\n5. Total de registros com data_resposta (apenas alunos): {total_final}")
        
        # Mostrar exemplo final
        amostra_final = query_final.first()
        if amostra_final:
            d, s, u = amostra_final
            print(f"\nExemplo de registro com data_resposta:")
            print(f"Desempenho - ID: {d.id}, Pontuação: {d.pontuacao}, Data: {d.data_resposta}")
            print(f"         - Tipo usuário (em desempenho): {d.tipo_usuario_id}")
            print(f"Simulado - ID: {s.id}, Status: {s.status}, Mês: {s.mes_id}, Disciplina: {s.disciplina_id}")
            print(f"Aluno    - ID: {u.id}, Tipo usuário (real): {u.tipo_usuario_id}, Escola: {u.escola_id}")

if __name__ == '__main__':
    verificar_dados_desempenho()
