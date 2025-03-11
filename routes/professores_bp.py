from flask import Blueprint, render_template, request, current_app, jsonify, redirect, url_for, flash, make_response
from flask_login import login_required, current_user
from models import ProfessorTurmaEscola, Turmas, Ano_escolar, Escolas, SimuladosGerados, Disciplinas, Assuntos, Usuarios, DesempenhoSimulado, SimuladosEnviados, SimuladosGeradosProfessor
from extensions import db
from datetime import datetime

professores_bp = Blueprint('professores', __name__)

@professores_bp.route('/portal_professores', methods=['GET'])
@login_required
def portal_professores():
    # Recuperar as turmas vinculadas ao professor
    turmas = (
        db.session.query(
            Turmas.id,
            Ano_escolar.nome.label('Ano_escolar'),
            Turmas.turma,
            Escolas.nome_da_escola.label('escola')
        )
        .join(ProfessorTurmaEscola, ProfessorTurmaEscola.turma_id == Turmas.id)
        .join(Ano_escolar, Turmas.ano_escolar_id == Ano_escolar.id)
        .join(Escolas, Turmas.escola_id == Escolas.id)
        .filter(ProfessorTurmaEscola.professor_id == current_user.id)
        .distinct()
        .all()
    )

    # Recuperar filtros
    assunto_filtro = request.args.get('assunto', '').strip()
    avaliacao_filtro = request.args.get('avaliacao', '').strip()
    page = int(request.args.get('page', 1))
    per_page = 10

    # Query base para simulados gerados
    query = (
        db.session.query(
            SimuladosGerados.id,
            Assuntos.nome.label('assunto'),
            Disciplinas.nome.label('disciplina'),
            Ano_escolar.nome.label('Ano_escolar'),
            Turmas.id.label('turma_id'),
            Turmas.turma.label('letra_turma'),
            SimuladosGerados.data_envio,
            SimuladosGerados.status
        )
        .join(Ano_escolar, SimuladosGerados.ano_escolar_id == Ano_escolar.id)
        .join(Disciplinas, SimuladosGerados.disciplina_id == Disciplinas.id)
        .join(ProfessorTurmaEscola, ProfessorTurmaEscola.professor_id == current_user.id)
        .join(Turmas, (Turmas.ano_escolar_id == SimuladosGerados.ano_escolar_id) & (Turmas.id == ProfessorTurmaEscola.turma_id))
        .outerjoin(Assuntos, (Assuntos.disciplina_id == SimuladosGerados.disciplina_id) & 
                           (Assuntos.professor_id == ProfessorTurmaEscola.professor_id))
    )

    # Aplicar filtros
    if assunto_filtro:
        query = query.filter(Assuntos.nome.ilike(f'%{assunto_filtro}%'))
    if avaliacao_filtro:
        query = query.filter(SimuladosGerados.status.ilike(f'%{avaliacao_filtro}%'))

    # Adicionar paginação
    total = query.count()
    simulados = query.offset((page - 1) * per_page).limit(per_page).all()
    total_pages = (total + per_page - 1) // per_page

    return render_template(
        'professores/portal_professores.html',
        turmas=turmas,
        simulados=simulados,
        current_page=page,
        total_pages=total_pages,
        assunto_filtro=assunto_filtro,
        avaliacao_filtro=avaliacao_filtro
    )

@professores_bp.route('/listar_turmas')
@login_required
def listar_turmas():
    # Recuperar as turmas vinculadas ao professor
    turmas = (
        db.session.query(
            Turmas.id,
            Ano_escolar.nome.label('Ano_escolar'),
            Turmas.turma,
            Escolas.nome_da_escola.label('escola')
        )
        .join(ProfessorTurmaEscola, ProfessorTurmaEscola.turma_id == Turmas.id)
        .join(Ano_escolar, Turmas.ano_escolar_id == Ano_escolar.id)
        .join(Escolas, Turmas.escola_id == Escolas.id)
        .filter(ProfessorTurmaEscola.professor_id == current_user.id)
        .distinct()
        .all()
    )

    return render_template('professores/listar_turmas.html', turmas=turmas)

@professores_bp.route('/api/turma/<int:turma_id>/alunos')
@login_required
def api_alunos_turma(turma_id):
    print(f"\n>>> Buscando alunos da turma {turma_id}")
    
    # Verificar se o professor tem acesso à turma
    turma_acesso = (
        db.session.query(ProfessorTurmaEscola)
        .filter(
            ProfessorTurmaEscola.professor_id == current_user.id,
            ProfessorTurmaEscola.turma_id == turma_id
        )
        .first()
    )
    
    print(f">>> Acesso do professor à turma: {turma_acesso}")
    
    if not turma_acesso:
        print(">>> Professor não tem acesso à turma")
        return jsonify({'error': 'Acesso negado'}), 403
    
    # Buscar alunos da turma
    alunos = (
        db.session.query(
            Usuarios.id,
            Usuarios.nome,
            Usuarios.email
        )
        .distinct()  # Remove duplicatas
        .filter(
            Usuarios.turma_id == turma_id,
            Usuarios.tipo_usuario_id == 4,  # TIPO_USUARIO_ALUNO
            Usuarios.nome.isnot(None),  # Garante que nome não é nulo
            Usuarios.email.isnot(None)  # Garante que email não é nulo
        )
        .order_by(Usuarios.nome)
        .all()
    )
    
    print(f">>> Alunos encontrados: {len(alunos) if alunos else 0}")
    if alunos:
        print(f">>> Primeiro aluno: {alunos[0]}")
    
    # Formata os dados dos alunos
    alunos_data = [{
        'id': aluno.id,
        'nome': aluno.nome,
        'email': aluno.email
    } for aluno in alunos]
    
    print(f">>> Dados formatados: {alunos_data}")
    
    return jsonify({
        'success': True,
        'data': alunos_data
    })

@professores_bp.route('/relatorio_turma/<int:turma_id>')
@login_required
def relatorio_turma(turma_id):
    # Verificar se o professor tem acesso à turma
    turma_acesso = (
        db.session.query(ProfessorTurmaEscola)
        .filter(
            ProfessorTurmaEscola.professor_id == current_user.id,
            ProfessorTurmaEscola.turma_id == turma_id
        )
        .first()
    )
    
    if not turma_acesso:
        return redirect(url_for('professores.portal_professores'))
    
    # Buscar informações da turma
    turma = (
        db.session.query(
            Turmas.id,
            Ano_escolar.nome.label('Ano_escolar'),
            Turmas.turma,
            Escolas.nome_da_escola.label('escola')
        )
        .join(Ano_escolar, Ano_escolar.id == Turmas.ano_escolar_id)
        .join(Escolas, Escolas.id == Turmas.escola_id)
        .filter(Turmas.id == turma_id)
        .first()
    )
    
    # Get total alunos
    total_alunos = db.session.query(Usuarios).filter(
        Usuarios.turma_id == turma_id,
        Usuarios.tipo_usuario_id == 4  # Tipo aluno
    ).count()

    # Initialize default values
    media_geral = 0
    taxa_participacao = 0
    disciplinas = []
    medias_disciplinas = []
    distribuicao_notas = [0, 0, 0, 0, 0]  # 0-20, 21-40, 41-60, 61-80, 81-100
    grupos = {
        'alto_desempenho': 0,
        'medio_desempenho': 0,
        'baixo_desempenho': 0
    }
    
    # Get disciplinas and calculate médias
    disciplina_results = db.session.query(
        Disciplinas.nome,
        Disciplinas.id,
        db.func.count(DesempenhoSimulado.id).label('total_alunos'),
        db.func.count(DesempenhoSimulado.respostas_aluno).label('total_respostas')
    ).join(
        SimuladosGeradosProfessor,
        SimuladosGeradosProfessor.disciplina_id == Disciplinas.id
    ).join(
        SimuladosEnviados,
        SimuladosEnviados.simulado_id == SimuladosGeradosProfessor.id
    ).join(
        DesempenhoSimulado,
        DesempenhoSimulado.simulado_id == SimuladosEnviados.id
    ).join(
        Usuarios,
        Usuarios.id == DesempenhoSimulado.aluno_id
    ).filter(
        Usuarios.turma_id == turma_id
    ).group_by(
        Disciplinas.id,
        Disciplinas.nome
    ).all()

    if disciplina_results:
        for disc, _, total_alunos, total_respostas in disciplina_results:
            disciplinas.append(disc)
            # Assuming 10 questions per test for now
            media = (total_respostas / (total_alunos * 10) * 100) if total_alunos > 0 else 0
            medias_disciplinas.append(media)
        
        # Calculate média geral
        media_geral = sum(medias_disciplinas) / len(medias_disciplinas) if medias_disciplinas else 0
        
        # Get all notas for distribution
        notas_query = db.session.query(
            DesempenhoSimulado.id,
            db.func.count(DesempenhoSimulado.respostas_aluno).label('total_respostas')
        ).join(
            Usuarios,
            Usuarios.id == DesempenhoSimulado.aluno_id
        ).join(
            SimuladosEnviados,
            SimuladosEnviados.id == DesempenhoSimulado.simulado_id
        ).filter(
            Usuarios.turma_id == turma_id
        ).group_by(
            DesempenhoSimulado.id
        ).all()
        
        notas = []
        for _, total_respostas in notas_query:
            # Assuming 10 questions per test for now
            nota = (total_respostas / 10) * 100
            notas.append(nota)
        
        if notas:
            for nota in notas:
                if nota >= 81:
                    distribuicao_notas[4] += 1
                elif nota >= 61:
                    distribuicao_notas[3] += 1
                elif nota >= 41:
                    distribuicao_notas[2] += 1
                elif nota >= 21:
                    distribuicao_notas[1] += 1
                else:
                    distribuicao_notas[0] += 1

            # Calculate grupos
            grupos = {
                'baixo_desempenho': distribuicao_notas[0] + distribuicao_notas[1] + distribuicao_notas[2],
                'medio_desempenho': distribuicao_notas[3],
                'alto_desempenho': distribuicao_notas[4]
            }
            
            # Calculate taxa de participação
            total_possiveis = total_alunos * len(disciplinas)
            taxa_participacao = (len(notas) / total_possiveis * 100) if total_possiveis > 0 else 0

    # Generate parecer
    parecer = {
        'engajamento': gerar_parecer_engajamento(taxa_participacao),
        'desempenho': gerar_parecer_desempenho(media_geral, grupos),
        'pontos_atencao': gerar_pontos_atencao(grupos, taxa_participacao),
        'recomendacoes': gerar_recomendacoes(grupos, taxa_participacao, media_geral)
    }

    return render_template('professores/relatorio_turma.html',
                         turma=turma,
                         total_alunos=total_alunos,
                         media_geral=media_geral,
                         taxa_participacao=taxa_participacao,
                         disciplinas=disciplinas,
                         medias_disciplinas=medias_disciplinas,
                         distribuicao_notas=distribuicao_notas,
                         grupos=grupos,
                         parecer=parecer,
                         now=datetime.now())

def gerar_parecer_engajamento(taxa_participacao):
    if taxa_participacao >= 90:
        return "A turma demonstra excelente nível de engajamento, com participação muito acima da média."
    elif taxa_participacao >= 70:
        return "O engajamento da turma é satisfatório, com boa participação nas atividades."
    else:
        return "Há necessidade de maior engajamento da turma. A participação está abaixo do esperado."

def gerar_parecer_desempenho(media_geral, grupos):
    if media_geral >= 80:
        return "O desempenho geral da turma é excelente, demonstrando domínio dos conteúdos."
    elif media_geral >= 60:
        return "A turma apresenta desempenho satisfatório, mas há espaço para melhorias."
    else:
        return "O desempenho geral da turma está abaixo do esperado, necessitando atenção especial."

def gerar_pontos_atencao(grupos, taxa_participacao):
    pontos = []
    if grupos['baixo_desempenho'] > 0:
        pontos.append(f"Há {grupos['baixo_desempenho']} alunos com desempenho abaixo de 60%.")
    if taxa_participacao < 70:
        pontos.append("A taxa de participação está abaixo do ideal.")
    
    return " ".join(pontos) if pontos else "Não há pontos críticos de atenção no momento."

def gerar_recomendacoes(grupos, taxa_participacao, media_geral):
    recomendacoes = []
    
    if grupos['baixo_desempenho'] > 0:
        recomendacoes.append("Implementar programa de reforço para alunos com baixo desempenho.")
    if taxa_participacao < 70:
        recomendacoes.append("Desenvolver estratégias para aumentar o engajamento dos alunos.")
    if media_geral < 60:
        recomendacoes.append("Revisar metodologias de ensino e avaliar necessidade de adaptações.")
    
    return " ".join(recomendacoes) if recomendacoes else "Manter as estratégias atuais e continuar monitorando o progresso."

def gerar_parecer_aluno(desempenho, media_geral):
    """Gera um parecer sobre o desempenho do aluno baseado em suas notas."""
    if not desempenho:
        return {
            'comportamento': "Ainda não há dados suficientes para avaliar o comportamento.",
            'desempenho': "Ainda não há dados suficientes para avaliar o desempenho.",
            'destaques': "Ainda não há dados suficientes para identificar destaques.",
            'recomendacoes': "Aguardando mais dados para fornecer recomendações específicas."
        }
    
    parecer = {}
    
    # Análise do comportamento
    parecer['comportamento'] = "O aluno tem demonstrado comprometimento com os estudos, realizando as avaliações propostas."
    
    # Análise do desempenho
    if media_geral >= 90:
        parecer['desempenho'] = "O aluno demonstra excelente desempenho, com domínio consistente do conteúdo."
    elif media_geral >= 80:
        parecer['desempenho'] = "O aluno apresenta um bom desempenho, com compreensão sólida dos conceitos."
    elif media_geral >= 70:
        parecer['desempenho'] = "O aluno mostra um desempenho satisfatório, mas há espaço para melhorias."
    elif media_geral >= 60:
        parecer['desempenho'] = "O aluno atinge o mínimo esperado, mas necessita de atenção em alguns pontos."
    else:
        parecer['desempenho'] = "O aluno apresenta dificuldades significativas que precisam ser endereçadas."
    
    # Análise dos destaques
    if len(desempenho) > 1:
        notas = [d['desempenho'] for d in desempenho]
        primeira_nota = notas[-1]  # mais antiga
        ultima_nota = notas[0]     # mais recente
        
        if ultima_nota > primeira_nota + 10:
            parecer['destaques'] = "Demonstra evolução significativa ao longo do período, com melhoria expressiva nas notas."
        elif ultima_nota > primeira_nota:
            parecer['destaques'] = "Mostra uma tendência de melhoria gradual no desempenho."
        elif ultima_nota < primeira_nota - 10:
            parecer['destaques'] = "Apresenta queda significativa no desempenho que requer atenção especial."
        elif ultima_nota < primeira_nota:
            parecer['destaques'] = "Mostra uma leve diminuição no desempenho que deve ser monitorada."
        else:
            parecer['destaques'] = "Mantém um desempenho consistente ao longo do período."
    else:
        parecer['destaques'] = "Possui apenas uma avaliação, necessitando de mais dados para análise de evolução."
    
    # Recomendações
    recomendacoes = []
    if media_geral < 70:
        if media_geral < 60:
            recomendacoes.extend([
                "Realizar acompanhamento individualizado com o professor.",
                "Participar de atividades de reforço escolar.",
            ])
        recomendacoes.extend([
            "Identificar áreas específicas de dificuldade para focar os estudos.",
            "Desenvolver um plano de estudos personalizado.",
            "Aumentar a frequência de exercícios práticos."
        ])
    else:
        recomendacoes.extend([
            "Manter o ritmo atual de estudos.",
            "Buscar aprofundamento em tópicos de interesse.",
            "Auxiliar colegas com dificuldades quando possível."
        ])
    
    parecer['recomendacoes'] = " ".join(recomendacoes)
    
    return parecer

@professores_bp.route('/professores/relatorio_aluno/<int:aluno_id>')
@login_required
def relatorio_aluno(aluno_id):
    # Buscar informações do aluno
    aluno = Usuarios.query.get_or_404(aluno_id)
    
    # Buscar informações da turma e escola
    turma = (
        db.session.query(
            Turmas.id,
            Turmas.turma,
            Ano_escolar.nome.label('Ano_escolar'),
            Escolas.nome_da_escola.label('escola')
        )
        .join(Escolas, Turmas.escola_id == Escolas.id)
        .join(Ano_escolar, Turmas.ano_escolar_id == Ano_escolar.id)
        .filter(Turmas.id == aluno.turma_id)
        .first()
    )
    
    if not turma:
        flash('Turma não encontrada.', 'error')
        return redirect(url_for('professores.listar_turmas'))
    
    # Verificar se o professor tem acesso à turma do aluno
    turma_acesso = (
        db.session.query(ProfessorTurmaEscola)
        .filter(
            ProfessorTurmaEscola.professor_id == current_user.id,
            ProfessorTurmaEscola.turma_id == aluno.turma_id
        )
        .first()
    )
    
    if not turma_acesso:
        flash('Você não tem acesso a este aluno.', 'error')
        return redirect(url_for('professores.listar_turmas'))
    
    # Buscar desempenho do aluno
    desempenho_query = (
        db.session.query(
            DesempenhoSimulado.id,
            DesempenhoSimulado.aluno_id,
            DesempenhoSimulado.simulado_id,
            DesempenhoSimulado.respostas_aluno,
            DesempenhoSimulado.respostas_corretas,
            DesempenhoSimulado.desempenho,
            DesempenhoSimulado.data_resposta,
            SimuladosEnviados.simulado_id.label('simulado_gerado_id'),
            SimuladosGeradosProfessor.disciplina_id
        )
        .join(
            SimuladosEnviados,
            DesempenhoSimulado.simulado_id == SimuladosEnviados.id
        )
        .join(
            SimuladosGeradosProfessor,
            SimuladosEnviados.simulado_id == SimuladosGeradosProfessor.id
        )
        .filter(
            DesempenhoSimulado.aluno_id == aluno_id
        )
        .order_by(DesempenhoSimulado.data_resposta.desc())
        .all()
    )
    
    # Formatar dados do desempenho
    desempenho = []
    disciplinas = set()
    datas_simulados = set()
    desempenho_por_disciplina = {}
    
    for d in desempenho_query:
        # Adicionar ao desempenho geral
        desempenho.append({
            'id': d.id,
            'aluno_id': d.aluno_id,
            'simulado_id': d.simulado_id,
            'respostas_aluno': d.respostas_aluno,
            'respostas_corretas': d.respostas_corretas,
            'desempenho': float(d.desempenho) if d.desempenho else 0,
            'data_resposta': d.data_resposta.strftime('%d/%m/%Y %H:%M') if d.data_resposta else None,
            'disciplina_id': d.disciplina_id
        })
        
        # Coletar disciplinas únicas
        if d.disciplina_id:
            disciplinas.add(d.disciplina_id)
            
            # Adicionar ao desempenho por disciplina
            if d.disciplina_id not in desempenho_por_disciplina:
                desempenho_por_disciplina[d.disciplina_id] = []
            desempenho_por_disciplina[d.disciplina_id].append(
                float(d.desempenho) if d.desempenho else 0
            )
        
        # Coletar datas únicas
        if d.data_resposta:
            datas_simulados.add(d.data_resposta.strftime('%d/%m/%Y'))
    
    # Buscar nomes das disciplinas
    disciplinas_info = (
        db.session.query(Disciplinas)
        .filter(Disciplinas.id.in_(disciplinas))
        .all()
    )
    
    # Preparar dados para os gráficos
    disciplinas = [d.nome for d in disciplinas_info]
    medias_disciplinas = []
    notas_simulados = []
    datas_formatadas = []
    
    for d in disciplinas_info:
        notas = desempenho_por_disciplina.get(d.id, [])
        if notas:
            media = sum(notas) / len(notas)
            medias_disciplinas.append(round(media, 1))
        else:
            medias_disciplinas.append(0)
    
    # Preparar dados para o gráfico de evolução
    for d in sorted(desempenho, key=lambda x: x['data_resposta']):
        if d['data_resposta']:
            notas_simulados.append(d['desempenho'])
            datas_formatadas.append(d['data_resposta'])
    
    # Calcular média geral
    media_geral = 0
    if desempenho:
        media_geral = sum(d['desempenho'] for d in desempenho) / len(desempenho)
    
    # Gerar parecer
    parecer = gerar_parecer_aluno(desempenho, media_geral)
    
    return render_template(
        'professores/relatorio_aluno.html',
        aluno=aluno,
        turma=turma,
        desempenho=desempenho,
        media_geral=media_geral,
        parecer=parecer,
        disciplinas=disciplinas,
        medias_disciplinas=medias_disciplinas,
        datas_simulados=list(datas_simulados),
        notas_simulados=notas_simulados,
        datas_formatadas=datas_formatadas
    )

@professores_bp.route('/professores/relatorio_aluno/<int:aluno_id>/pdf')
@login_required
def relatorio_aluno_pdf(aluno_id):
    # Buscar informações do aluno
    aluno = Usuarios.query.get_or_404(aluno_id)
    
    # Buscar informações da turma e escola
    turma = (
        db.session.query(
            Turmas.id,
            Turmas.turma,
            Ano_escolar.nome.label('Ano_escolar'),
            Escolas.nome_da_escola.label('escola')
        )
        .join(Escolas, Turmas.escola_id == Escolas.id)
        .join(Ano_escolar, Turmas.ano_escolar_id == Ano_escolar.id)
        .filter(Turmas.id == aluno.turma_id)
        .first()
    )
    
    if not turma:
        flash('Turma não encontrada.', 'error')
        return redirect(url_for('professores.listar_turmas'))
    
    # Verificar se o professor tem acesso à turma do aluno
    turma_acesso = (
        db.session.query(ProfessorTurmaEscola)
        .filter(
            ProfessorTurmaEscola.professor_id == current_user.id,
            ProfessorTurmaEscola.turma_id == aluno.turma_id
        )
        .first()
    )
    
    if not turma_acesso:
        flash('Você não tem acesso a este aluno.', 'error')
        return redirect(url_for('professores.listar_turmas'))
    
    # Buscar desempenho do aluno
    desempenho_query = (
        db.session.query(
            DesempenhoSimulado.id,
            DesempenhoSimulado.aluno_id,
            DesempenhoSimulado.simulado_id,
            DesempenhoSimulado.respostas_aluno,
            DesempenhoSimulado.respostas_corretas,
            DesempenhoSimulado.desempenho,
            DesempenhoSimulado.data_resposta,
            SimuladosEnviados.simulado_id.label('simulado_gerado_id'),
            SimuladosGeradosProfessor.disciplina_id
        )
        .join(
            SimuladosEnviados,
            DesempenhoSimulado.simulado_id == SimuladosEnviados.id
        )
        .join(
            SimuladosGeradosProfessor,
            SimuladosEnviados.simulado_id == SimuladosGeradosProfessor.id
        )
        .filter(
            DesempenhoSimulado.aluno_id == aluno_id
        )
        .order_by(DesempenhoSimulado.data_resposta.desc())
        .all()
    )
    
    # Formatar dados do desempenho
    desempenho = []
    disciplinas = set()
    datas_simulados = set()
    desempenho_por_disciplina = {}
    
    for d in desempenho_query:
        # Adicionar ao desempenho geral
        desempenho.append({
            'id': d.id,
            'aluno_id': d.aluno_id,
            'simulado_id': d.simulado_id,
            'respostas_aluno': d.respostas_aluno,
            'respostas_corretas': d.respostas_corretas,
            'desempenho': float(d.desempenho) if d.desempenho else 0,
            'data_resposta': d.data_resposta.strftime('%d/%m/%Y %H:%M') if d.data_resposta else None,
            'disciplina_id': d.disciplina_id
        })
        
        # Coletar disciplinas únicas
        if d.disciplina_id:
            disciplinas.add(d.disciplina_id)
            
            # Adicionar ao desempenho por disciplina
            if d.disciplina_id not in desempenho_por_disciplina:
                desempenho_por_disciplina[d.disciplina_id] = []
            desempenho_por_disciplina[d.disciplina_id].append(
                float(d.desempenho) if d.desempenho else 0
            )
        
        # Coletar datas únicas
        if d.data_resposta:
            datas_simulados.add(d.data_resposta.strftime('%d/%m/%Y'))
    
    # Buscar nomes das disciplinas
    disciplinas_info = (
        db.session.query(Disciplinas)
        .filter(Disciplinas.id.in_(disciplinas))
        .all()
    )
    
    # Preparar dados para os gráficos
    disciplinas = [d.nome for d in disciplinas_info]
    medias_disciplinas = []
    notas_simulados = []
    datas_formatadas = []
    
    for d in disciplinas_info:
        notas = desempenho_por_disciplina.get(d.id, [])
        if notas:
            media = sum(notas) / len(notas)
            medias_disciplinas.append(round(media, 1))
        else:
            medias_disciplinas.append(0)
    
    # Preparar dados para o gráfico de evolução
    for d in sorted(desempenho, key=lambda x: x['data_resposta']):
        if d['data_resposta']:
            notas_simulados.append(d['desempenho'])
            datas_formatadas.append(d['data_resposta'])
    
    # Calcular média geral
    media_geral = 0
    if desempenho:
        media_geral = sum(d['desempenho'] for d in desempenho) / len(desempenho)
    
    # Gerar parecer
    parecer = gerar_parecer_aluno(desempenho, media_geral)
    
    # Obter data atual
    from datetime import datetime
    data_atual = datetime.now().strftime('%d/%m/%Y')
    data_hora_atual = datetime.now().strftime('%d/%m/%Y às %H:%M')
    
    # Renderizar o template HTML
    html = render_template(
        'professores/relatorio_aluno_pdf.html',
        aluno=aluno,
        turma=turma,
        desempenho=desempenho,
        media_geral=media_geral,
        parecer=parecer,
        disciplinas=disciplinas,
        medias_disciplinas=medias_disciplinas,
        datas_simulados=list(datas_simulados),
        notas_simulados=notas_simulados,
        datas_formatadas=datas_formatadas,
        data_atual=data_atual,
        data_hora_atual=data_hora_atual
    )
    
    # Criar o PDF
    from weasyprint import HTML
    pdf = HTML(string=html).write_pdf()
    
    # Retornar o PDF como download
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=relatorio_{aluno.nome}.pdf'
    
    return response
