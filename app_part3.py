# Funções auxiliares
def get_relatorio_rede():
    try:
        db = get_db()
        cursor = db.session()
        query = """
            SELECT 
                e.nome_da_escola,
                COUNT(DISTINCT u.id) as total_alunos,
                COUNT(DISTINCT CASE WHEN u.tipo_usuario_id = 3 THEN u.id END) as total_professores,
                COUNT(DISTINCT t.id) as total_turmas
            FROM escolas e
            LEFT JOIN usuarios u ON e.id = u.escola_id
            LEFT JOIN turmas t ON e.id = t.escola_id
            GROUP BY e.id, e.nome_da_escola
        """
        result = cursor.execute(query).fetchall()
        return result
    except Exception as e:
        print(f"Erro ao gerar relatório: {str(e)}")
        return None

def get_escola_alocada(user_id):
    try:
        db = get_db()
        cursor = db.session()
        query = """
            SELECT e.*
            FROM escolas e
            JOIN usuarios u ON e.id = u.escola_id
            WHERE u.id = :user_id
        """
        result = cursor.execute(query, {"user_id": user_id}).fetchone()
        return result
    except Exception as e:
        print(f"Erro ao buscar escola: {str(e)}")
        return None

def gerar_parecer_ia(relatorio):
    openai.api_key = os.getenv('OPENAI_API_KEY')
    return openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=[{"role": "system", "content": relatorio}])

def get_tipos_ensino(escola_id):
    try:
        db = get_db()
        cursor = db.session()
        query = """
            SELECT DISTINCT te.*
            FROM tipos_ensino te
            JOIN escola_tipos_ensino ete ON te.id = ete.tipo_ensino_id
            WHERE ete.escola_id = :escola_id
        """
        result = cursor.execute(query, {"escola_id": escola_id}).fetchall()
        return result
    except Exception as e:
        print(f"Erro ao buscar tipos de ensino: {str(e)}")
        return None

def gerar_perguntas(disciplina, assunto, quantidade, nivel, alternativas):
    openai.api_key = os.getenv('OPENAI_API_KEY')
    
    prompt = f"""Gere {quantidade} questões de múltipla escolha sobre {disciplina}, especificamente sobre {assunto}.
    Nível: {nivel}
    Cada questão deve ter {alternativas} alternativas (A, B, C, D, E).
    Use o seguinte formato JSON:
    {{
        "questoes": [
            {{
                "pergunta": "texto da pergunta",
                "alternativas": {{
                    "A": "texto da alternativa A",
                    "B": "texto da alternativa B",
                    "C": "texto da alternativa C",
                    "D": "texto da alternativa D",
                    "E": "texto da alternativa E"
                }},
                "resposta_correta": "letra da alternativa correta"
            }}
        ]
    }}"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um professor especialista em criar questões de múltipla escolha."},
                {"role": "user", "content": prompt}
            ]
        )
        
        questoes_json = response.choices[0].message.content
        questoes = json.loads(questoes_json)
        return questoes
    except Exception as e:
        print(f"Erro ao gerar questões: {str(e)}")
        return None

def enviar_questoes_automaticamente(Ano_escolar_id, codigo_ibge):
    try:
        db = get_db()
        
        # Buscar questões disponíveis para a série
        questoes = BancoQuestoes.query.filter_by(Ano_escolar_id=Ano_escolar_id).all()
        if not questoes:
            return False, "Nenhuma questão disponível para esta série"
        
        # Buscar turmas da série na cidade
        turmas = (Turmas.query
                 .join(Escolas)
                 .filter(Turmas.Ano_escolar_id == Ano_escolar_id)
                 .filter(Escolas.codigo_ibge == codigo_ibge)
                 .all())
        
        if not turmas:
            return False, "Nenhuma turma encontrada para esta série nesta cidade"
        
        # Criar simulado
        simulado = SimuladosGerados(
            Ano_escolar_id=Ano_escolar_id,
            mes_id=datetime.now().month,
            status='enviado',
            data_envio=datetime.now()
        )
        db.session.add(simulado)
        db.session.flush()
        
        # Adicionar questões ao simulado
        for questao in questoes:
            simulado_questao = SimuladoQuestoes(
                simulado_id=simulado.id,
                questao_id=questao.id
            )
            db.session.add(simulado_questao)
        
        # Enviar para cada turma
        for turma in turmas:
            # Buscar alunos da turma
            alunos = Usuarios.query.filter_by(
                turma_id=turma.id,
                tipo_usuario_id=5  # Tipo aluno
            ).all()
            
            for aluno in alunos:
                aluno_simulado = AlunoSimulado(
                    aluno_id=aluno.id,
                    simulado_id=simulado.id,
                    status='pendente'
                )
                db.session.add(aluno_simulado)
        
        db.session.commit()
        return True, "Simulado enviado com sucesso"
    
    except Exception as e:
        db.session.rollback()
        return False, f"Erro ao enviar simulado: {str(e)}"

def init_db():
    with app.app_context():
        # Criar todas as tabelas
        db.create_all()
        
        # Verificar se já existem tipos de usuários
        if not TiposUsuarios.query.first():
            tipos = [
                TiposUsuarios(id=1, descricao='Administrador'),
                TiposUsuarios(id=2, descricao='Secretaria'),
                TiposUsuarios(id=3, descricao='Professor'),
                TiposUsuarios(id=4, descricao='Coordenador'),
                TiposUsuarios(id=5, descricao='Aluno')
            ]
            db.session.bulk_save_objects(tipos)
            
        # Verificar se já existem tipos de ensino
        if not TiposEnsino.query.first():
            tipos = [
                TiposEnsino(id=1, nome='Fundamental I'),
                TiposEnsino(id=2, nome='Fundamental II'),
                TiposEnsino(id=3, nome='Médio')
            ]
            db.session.bulk_save_objects(tipos)
            
        # Verificar se já existem séries
        if not Ano_escolar.query.first():
            Ano_escolar = [
                Ano_escolar(id=1, nome='1º ano'),
                Ano_escolar(id=2, nome='2º ano'),
                Ano_escolar(id=3, nome='3º ano'),
                Ano_escolar(id=4, nome='4º ano'),
                Ano_escolar(id=5, nome='5º ano'),
                Ano_escolar(id=6, nome='6º ano'),
                Ano_escolar(id=7, nome='7º ano'),
                Ano_escolar(id=8, nome='8º ano'),
                Ano_escolar(id=9, nome='9º ano')
            ]
            db.session.bulk_save_objects(Ano_escolar)
            
        # Verificar se já existem meses
        if not MESES.query.first():
            meses = [
                MESES_NOMES[int(mes)]id=1, nome='Janeiro'),
                MESES_NOMES[int(mes)]id=2, nome='Fevereiro'),
                MESES_NOMES[int(mes)]id=3, nome='Março'),
                MESES_NOMES[int(mes)]id=4, nome='Abril'),
                MESES_NOMES[int(mes)]id=5, nome='Maio'),
                MESES_NOMES[int(mes)]id=6, nome='Junho'),
                MESES_NOMES[int(mes)]id=7, nome='Julho'),
                MESES_NOMES[int(mes)]id=8, nome='Agosto'),
                MESES_NOMES[int(mes)]id=9, nome='Setembro'),
                MESES_NOMES[int(mes)]id=10, nome='Outubro'),
                MESES_NOMES[int(mes)]id=11, nome='Novembro'),
                MESES_NOMES[int(mes)]id=12, nome='Dezembro')
            ]
            db.session.bulk_save_objects(meses)
        
        db.session.commit()

def validar_resposta(pergunta, resposta_ia, assunto):
    openai.api_key = os.getenv('OPENAI_API_KEY')
    
    prompt = f"""Valide se a resposta da IA para a seguinte pergunta está correta:
    Pergunta: {pergunta}
    Resposta da IA: {resposta_ia}
    Assunto: {assunto}
    
    Por favor, forneça uma análise detalhada e indique se a resposta está:
    1. Totalmente correta
    2. Parcialmente correta
    3. Incorreta
    
    Explique o motivo da sua avaliação."""
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um professor especialista em validar respostas."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Erro ao validar resposta: {str(e)}")
        return None

def gerar_perguntas_conhecimentos_gerais(quantidade=10, nivel="Médio"):
    openai.api_key = os.getenv('OPENAI_API_KEY')
    
    prompt = f"""Gere {quantidade} questões de múltipla escolha sobre conhecimentos gerais.
    Nível: {nivel}
    Cada questão deve ter 5 alternativas (A, B, C, D, E).
    
    Use o seguinte formato JSON:
    {{
        "questoes": [
            {{
                "pergunta": "texto da pergunta",
                "alternativas": {{
                    "A": "texto da alternativa A",
                    "B": "texto da alternativa B",
                    "C": "texto da alternativa C",
                    "D": "texto da alternativa D",
                    "E": "texto da alternativa E"
                }},
                "resposta_correta": "letra da alternativa correta",
                "explicacao": "explicação da resposta correta"
            }}
        ]
    }}"""
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um professor especialista em criar questões de conhecimentos gerais."},
                {"role": "user", "content": prompt}
            ]
        )
        
        questoes_json = response.choices[0].message.content
        questoes = json.loads(questoes_json)
        return questoes
    except Exception as e:
        print(f"Erro ao gerar questões: {str(e)}")
        return None

def criar_simulado_diario():
    try:
        # Gerar questões
        questoes = gerar_perguntas_conhecimentos_gerais()
        if not questoes:
            return False, "Erro ao gerar questões"
        
        # Criar simulado
        simulado = SimuladosGerados(
            Ano_escolar_id=1,  # Definir série apropriada
            mes_id=datetime.now().month,
            status='gerado',
            data_envio=datetime.now()
        )
        db.session.add(simulado)
        db.session.flush()
        
        # Adicionar questões ao banco e ao simulado
        for q in questoes['questoes']:
            questao = BancoQuestoes(
                questao=q['pergunta'],
                alternativa_a=q['alternativas']['A'],
                alternativa_b=q['alternativas']['B'],
                alternativa_c=q['alternativas']['C'],
                alternativa_d=q['alternativas']['D'],
                alternativa_e=q['alternativas']['E'],
                questao_correta=q['resposta_correta'],
                disciplina_id=1,  # Definir disciplina apropriada
                assunto='Conhecimentos Gerais',
                Ano_escolar_id=1,  # Definir série apropriada
                mes_id=datetime.now().month
            )
            db.session.add(questao)
            db.session.flush()
            
            simulado_questao = SimuladoQuestoes(
                simulado_id=simulado.id,
                questao_id=questao.id
            )
            db.session.add(simulado_questao)
        
        db.session.commit()
        return True, "Simulado criado com sucesso"
    
    except Exception as e:
        db.session.rollback()
        return False, f"Erro ao criar simulado: {str(e)}"
