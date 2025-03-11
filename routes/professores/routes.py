from flask import render_template, jsonify, g, redirect, url_for, flash, make_response, request
from flask_login import login_required, current_user
import logging
import matplotlib
matplotlib.use('Agg')  # Configurar o backend antes de importar pyplot
import matplotlib.pyplot as plt
from . import professores_bp
from extensions import db
from datetime import datetime
from models import (
    Turmas, Disciplinas, Ano_escolar, Escolas, Usuarios, ProfessorTurmaEscola,
    DesempenhoSimulado, SimuladosGerados, SimuladosGeradosProfessor, BancoQuestoes
)

# Configurar logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@professores_bp.route('/')
@login_required
def portal_professores():
    """Rota principal do portal de professores."""
    if not current_user.is_authenticated or current_user.tipo_usuario_id not in [3, 6]:  # Professor ou Admin
        return render_template('error.html', message='Acesso não autorizado'), 403
        
    # Se for admin, busca todas as turmas
    if current_user.tipo_usuario_id == 6:
        turmas = db.session.query(
            Turmas, 
            Ano_escolar,
            Escolas
        ).join(
            Ano_escolar, Turmas.ano_escolar_id == Ano_escolar.id
        ).join(
            Escolas, Turmas.escola_id == Escolas.id
        ).order_by(
            Turmas.turma
        ).all()
    else:
        # Buscar turmas do professor
        turmas = db.session.query(
            Turmas, 
            Ano_escolar,
            Escolas
        ).join(
            ProfessorTurmaEscola, Turmas.id == ProfessorTurmaEscola.turma_id
        ).join(
            Ano_escolar, Turmas.ano_escolar_id == Ano_escolar.id
        ).join(
            Escolas, Turmas.escola_id == Escolas.id
        ).filter(
            ProfessorTurmaEscola.professor_id == current_user.id
        ).order_by(
            Turmas.turma
        ).all()
    
    return render_template('professores/portal.html', turmas=turmas)

@professores_bp.route('/listar_turmas', methods=['GET'])
@login_required
def listar_turmas():
    """Lista as turmas do professor."""
    if not current_user.is_authenticated or current_user.tipo_usuario_id not in [3, 6]:  
        return render_template('error.html', message='Acesso não autorizado'), 403

    if current_user.tipo_usuario_id == 6:
        turmas = db.session.query(Turmas, Ano_escolar, Escolas).join(
            Ano_escolar, Turmas.ano_escolar_id == Ano_escolar.id
        ).join(
            Escolas, Turmas.escola_id == Escolas.id
        ).order_by(Turmas.ano_escolar_id, Turmas.turma).all()
    else:
        turmas = db.session.query(Turmas, Ano_escolar, Escolas).join(
            ProfessorTurmaEscola, Turmas.id == ProfessorTurmaEscola.turma_id
        ).join(
            Ano_escolar, Turmas.ano_escolar_id == Ano_escolar.id
        ).join(
            Escolas, ProfessorTurmaEscola.escola_id == Escolas.id
        ).filter(ProfessorTurmaEscola.professor_id == current_user.id).order_by(Turmas.ano_escolar_id, Turmas.turma).all()
    return render_template('professores/listar_turmas.html', turmas=turmas)

@professores_bp.route('/api/turmas', methods=['GET'])
@login_required
def api_listar_turmas():
    """API para listar as turmas do professor."""
    if not current_user.is_authenticated or current_user.tipo_usuario_id not in [3, 6]:
        return jsonify([])

    if current_user.tipo_usuario_id == 6:
        turmas = db.session.query(Turmas, Ano_escolar, Escolas).join(
            Ano_escolar, Turmas.ano_escolar_id == Ano_escolar.id
        ).join(
            Escolas, Turmas.escola_id == Escolas.id
        ).order_by(Turmas.ano_escolar_id, Turmas.turma).all()
    else:
        turmas = db.session.query(Turmas, Ano_escolar, Escolas).join(
            ProfessorTurmaEscola, Turmas.id == ProfessorTurmaEscola.turma_id
        ).join(
            Ano_escolar, Turmas.ano_escolar_id == Ano_escolar.id
        ).join(
            Escolas, ProfessorTurmaEscola.escola_id == Escolas.id
        ).filter(ProfessorTurmaEscola.professor_id == current_user.id).order_by(Turmas.ano_escolar_id, Turmas.turma).all()
    return jsonify([{
        'id': turma[0].id,
        'Ano_escolar': turma[1].id,
        'turma': turma[0].turma,
        'escola': turma[2].nome_da_escola,
        'Ano_escolar_nome': turma[1].nome
    } for turma in turmas])

@professores_bp.route('/turma/<int:turma_id>/relatorio')
@login_required
def relatorio_turma(turma_id):
    if current_user.tipo_usuario_id not in [3, 6]:  # Verifica se é professor
        flash('Acesso não autorizado.', 'danger')
        return redirect(url_for('home'))
        
    if current_user.tipo_usuario_id == 6:
        turma_info = db.session.query(Turmas, Ano_escolar, Escolas).join(
            Ano_escolar, Turmas.ano_escolar_id == Ano_escolar.id
        ).join(
            Escolas, Turmas.escola_id == Escolas.id
        ).filter(Turmas.id == turma_id).first()
    else:
        turma_info = db.session.query(Turmas, Ano_escolar, Escolas).join(
            ProfessorTurmaEscola, Turmas.id == ProfessorTurmaEscola.turma_id
        ).join(
            Ano_escolar, Turmas.ano_escolar_id == Ano_escolar.id
        ).join(
            Escolas, ProfessorTurmaEscola.escola_id == Escolas.id
        ).filter(Turmas.id == turma_id, ProfessorTurmaEscola.professor_id == current_user.id).first()
    if not turma_info:
        flash('Você não tem acesso a esta turma.', 'danger')
        return redirect(url_for('professores.listar_turmas'))
    
    alunos = db.session.query(Usuarios).filter(Usuarios.turma_id == turma_id, Usuarios.tipo_usuario_id == 4).order_by(Usuarios.nome).all()
    
    # Buscar desempenho do aluno
    desempenhos = []
    for aluno in alunos:
        desempenho_aluno = db.session.query(DesempenhoSimulado, SimuladosGerados, Disciplinas).join(
            SimuladosGerados, DesempenhoSimulado.simulado_id == SimuladosGerados.id
        ).join(
            Disciplinas, SimuladosGerados.disciplina_id == Disciplinas.id
        ).filter(DesempenhoSimulado.aluno_id == aluno.id).order_by(DesempenhoSimulado.data_resposta.desc()).all()
        
        # Calcular média do aluno
        media_aluno = 0
        total_simulados = len(desempenho_aluno)
        if total_simulados > 0:
            media_aluno = sum(float(d[0].desempenho) for d in desempenho_aluno) / total_simulados
        
        desempenhos.append({
            'aluno': aluno,
            'desempenho': desempenho_aluno,
            'media_geral': media_aluno
        })
    
    # Calcular médias por disciplina
    disciplinas_dict = {}
    for d in desempenhos:
        for desempenho in d['desempenho']:
            disciplina = desempenho[2].nome
            if disciplina not in disciplinas_dict:
                disciplinas_dict[disciplina] = {
                    'total': 0,
                    'count': 0
                }
            disciplinas_dict[disciplina]['total'] += float(desempenho[0].desempenho)
            disciplinas_dict[disciplina]['count'] += 1
    
    # Calcular média geral da turma
    total_alunos = len(alunos)
    media_turma = sum(a['media_geral'] for a in desempenhos) / total_alunos if total_alunos > 0 else 0
    
    # Ordenar alunos por média geral
    alunos_ordenados = sorted(desempenhos, key=lambda x: x['media_geral'], reverse=True) if desempenhos else []
    
    # Identificar melhores alunos e alunos que precisam de atenção
    melhores_alunos = alunos_ordenados[:3] if len(alunos_ordenados) >= 3 else alunos_ordenados
    alunos_atencao = sorted(alunos_ordenados[-3:] if len(alunos_ordenados) >= 3 else alunos_ordenados, key=lambda x: x['media_geral'])
    
    # Calcular distribuição de notas
    faixas_notas = {
        'Excelente (90-100)': len([a for a in desempenhos if a['media_geral'] >= 90]),
        'Ótimo (80-89)': len([a for a in desempenhos if 80 <= a['media_geral'] < 90]),
        'Bom (70-79)': len([a for a in desempenhos if 70 <= a['media_geral'] < 80]),
        'Regular (60-69)': len([a for a in desempenhos if 60 <= a['media_geral'] < 70]),
        'Precisa Melhorar (<60)': len([a for a in desempenhos if a['media_geral'] < 60])
    }
    
    # Gerar gráficos com Plotly
    import plotly
    import plotly.graph_objs as go
    import json

    # Gráfico 1: Distribuição de notas
    fig_dist = go.Figure()
    fig_dist.add_trace(go.Bar(
        x=['0-20%', '21-40%', '41-60%', '61-80%', '81-100%'],
        y=[faixas_notas['Precisa Melhorar (<60)'], faixas_notas['Regular (60-69)'], faixas_notas['Bom (70-79)'], faixas_notas['Ótimo (80-89)'], faixas_notas['Excelente (90-100)']],
        marker_color='rgb(55, 83, 109)',
        text=[faixas_notas['Precisa Melhorar (<60)'], faixas_notas['Regular (60-69)'], faixas_notas['Bom (70-79)'], faixas_notas['Ótimo (80-89)'], faixas_notas['Excelente (90-100)']],
        textposition='auto',
    ))
    fig_dist.update_layout(
        title='Distribuição de Notas da Turma',
        xaxis_title='Faixa de Notas',
        yaxis_title='Número de Alunos',
        template='plotly_white',
        showlegend=False,
        margin=dict(t=50, l=50, r=50, b=50)
    )
    grafico_distribuicao = json.dumps(fig_dist, cls=plotly.utils.PlotlyJSONEncoder)

    # Gráfico 2: Desempenho por disciplina
    fig_disc = go.Figure()
    fig_disc.add_trace(go.Bar(
        x=list(disciplinas_dict.keys()),
        y=[disciplinas_dict[d]['total'] / disciplinas_dict[d]['count'] for d in disciplinas_dict],
        marker_color='rgb(26, 118, 255)',
        text=[f'{disciplinas_dict[d]["total"] / disciplinas_dict[d]["count"]:.1f}%' for d in disciplinas_dict],
        textposition='auto',
    ))
    fig_disc.update_layout(
        title='Média por Disciplina',
        xaxis_title='Disciplinas',
        yaxis_title='Média (%)',
        template='plotly_white',
        showlegend=False,
        margin=dict(t=50, l=50, r=50, b=50),
        yaxis=dict(range=[0, 100])
    )
    grafico_disciplinas = json.dumps(fig_disc, cls=plotly.utils.PlotlyJSONEncoder)

    # Gráfico 3: Radar chart de competências
    fig_radar = go.Figure()
    fig_radar.add_trace(go.Scatterpolar(
        r=[disciplinas_dict[d]['total'] / disciplinas_dict[d]['count'] for d in disciplinas_dict],
        theta=list(disciplinas_dict.keys()),
        fill='toself',
        name='Média da Turma'
    ))
    fig_radar.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100]
            )),
        showlegend=False,
        title='Radar de Competências',
        template='plotly_white',
        margin=dict(t=50, l=50, r=50, b=50)
    )
    grafico_radar = json.dumps(fig_radar, cls=plotly.utils.PlotlyJSONEncoder)

    # Gráfico 4: Gauge chart da média geral
    fig_gauge = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = media_turma,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Média Geral da Turma"},
        gauge = {
            'axis': {'range': [0, 100]},
            'bar': {'color': "rgb(26, 118, 255)"},
            'steps': [
                {'range': [0, 60], 'color': "rgb(255, 99, 132)"},
                {'range': [60, 80], 'color': "rgb(255, 205, 86)"},
                {'range': [80, 100], 'color': "rgb(75, 192, 192)"}
            ],
        }
    ))
    fig_gauge.update_layout(
        template='plotly_white',
        margin=dict(t=50, l=25, r=25, b=25)
    )
    grafico_gauge = json.dumps(fig_gauge, cls=plotly.utils.PlotlyJSONEncoder)

    # Calcular estatísticas por disciplina
    disciplinas = list(disciplinas_dict.keys())
    medias_disciplinas = []
    for disciplina in disciplinas:
        media = disciplinas_dict[disciplina]['total'] / disciplinas_dict[disciplina]['count']
        medias_disciplinas.append(media)

    # Calcular grupos de desempenho
    grupos = {
        'alto_desempenho': len([a for a in desempenhos if a['media_geral'] > 80]),
        'medio_desempenho': len([a for a in desempenhos if 60 <= a['media_geral'] <= 80]),
        'baixo_desempenho': len([a for a in desempenhos if a['media_geral'] < 60])
    }

    # Calcular taxa de participação (alunos que fizeram pelo menos um simulado)
    alunos_participantes = len([a for a in desempenhos if a['desempenho']])
    taxa_participacao = (alunos_participantes / total_alunos * 100) if total_alunos > 0 else 0

    # Gerar parecer pedagógico
    parecer = {
        'engajamento': gerar_parecer_engajamento(taxa_participacao),
        'desempenho': gerar_parecer_desempenho(media_turma),
        'pontos_atencao': gerar_pontos_atencao(grupos),
        'recomendacoes': gerar_recomendacoes(grupos, media_turma)
    }

    # Calcular distribuição de notas em 5 faixas
    distribuicao_notas = [
        len([a for a in desempenhos if 0 <= a['media_geral'] <= 20]),
        len([a for a in desempenhos if 20 < a['media_geral'] <= 40]),
        len([a for a in desempenhos if 40 < a['media_geral'] <= 60]),
        len([a for a in desempenhos if 60 < a['media_geral'] <= 80]),
        len([a for a in desempenhos if 80 < a['media_geral'] <= 100])
    ]

    return render_template('professores/relatorio_turma.html',
                         turma={
                             'id': turma_info[0].id,
                             'turma': turma_info[0].turma,
                             'Ano_escolar': turma_info[1].nome,
                             'escola': turma_info[2].nome_da_escola
                         },
                         alunos=alunos_ordenados,
                         total_alunos=total_alunos,
                         media_geral=media_turma,
                         taxa_participacao=taxa_participacao,
                         disciplinas=disciplinas,
                         medias_disciplinas=medias_disciplinas,
                         grupos=grupos,
                         parecer=parecer,
                         distribuicao_notas=distribuicao_notas,
                         grafico_distribuicao=grafico_distribuicao,
                         grafico_disciplinas=grafico_disciplinas,
                         grafico_radar=grafico_radar,
                         grafico_gauge=grafico_gauge,
                         now=datetime.now())

def gerar_parecer_engajamento(taxa_participacao):
    if taxa_participacao >= 90:
        return "A turma demonstra excelente engajamento, com alta taxa de participação nos simulados."
    elif taxa_participacao >= 70:
        return "A turma apresenta bom engajamento, mas há espaço para melhorar a participação."
    else:
        return "É necessário trabalhar o engajamento da turma para aumentar a participação nos simulados."

def gerar_parecer_desempenho(media_geral):
    if media_geral >= 80:
        return "O desempenho geral da turma é excelente, demonstrando forte domínio do conteúdo."
    elif media_geral >= 60:
        return "A turma apresenta desempenho satisfatório, mas há oportunidades de melhoria."
    else:
        return "O desempenho geral da turma está abaixo do esperado, necessitando atenção especial."

def gerar_pontos_atencao(grupos):
    pontos = []
    if grupos['baixo_desempenho'] > 0:
        pontos.append(f"{grupos['baixo_desempenho']} alunos com desempenho abaixo de 60%")
    if grupos['medio_desempenho'] > grupos['alto_desempenho']:
        pontos.append("Maior concentração de alunos com desempenho médio")
    if len(pontos) == 0:
        return "Não há pontos críticos de atenção no momento."
    return " | ".join(pontos)

def gerar_recomendacoes(grupos, media_geral):
    recomendacoes = []
    if grupos['baixo_desempenho'] > 0:
        recomendacoes.append("Implementar programa de reforço para alunos com baixo desempenho")
    if media_geral < 70:
        recomendacoes.append("Revisar metodologia de ensino e identificar pontos de melhoria")
    if grupos['alto_desempenho'] < grupos['medio_desempenho']:
        recomendacoes.append("Desenvolver estratégias para elevar o desempenho dos alunos médios")
    if len(recomendacoes) == 0:
        return "Manter o trabalho atual e continuar monitorando o progresso da turma."
    return " | ".join(recomendacoes)

@professores_bp.route('/aluno/<int:aluno_id>/relatorio')
@login_required
def relatorio_aluno(aluno_id):
    """Exibe o relatório do aluno."""
    try:
        if not current_user.is_authenticated or current_user.tipo_usuario_id not in [3, 6]:  
            return render_template('error.html', message='Acesso não autorizado'), 403

        aluno = db.session.query(Usuarios, Turmas, Ano_escolar, Escolas).join(
            Turmas, Usuarios.turma_id == Turmas.id
        ).join(
            Ano_escolar, Turmas.ano_escolar_id == Ano_escolar.id
        ).join(
            Escolas, Turmas.escola_id == Escolas.id
        ).filter(Usuarios.id == aluno_id, Usuarios.tipo_usuario_id == 4).first()
        
        if not aluno:
            return render_template('error.html', message='Aluno não encontrado'), 404

        # Busca desempenho nos simulados
        desempenhos = db.session.query(
            DesempenhoSimulado, 
            SimuladosGeradosProfessor,
            Disciplinas
        ).join(
            SimuladosGeradosProfessor, DesempenhoSimulado.simulado_id == SimuladosGeradosProfessor.id
        ).join(
            Disciplinas, SimuladosGeradosProfessor.disciplina_id == Disciplinas.id
        ).filter(
            DesempenhoSimulado.aluno_id == aluno_id
        ).order_by(
            Disciplinas.nome, 
            SimuladosGeradosProfessor.data_criacao.desc()
        ).all()

        return render_template(
            'professores/relatorio_aluno.html',
            aluno=aluno,
            desempenhos=desempenhos
        )
    except Exception as e:
        print(f"Erro: {str(e)}")
        return render_template('error.html', message=str(e)), 500

@professores_bp.route('/api/turma/<int:turma_id>/alunos', methods=['GET'])
@login_required
def api_alunos_turma(turma_id):
    """API para listar os alunos de uma turma."""
    try:
        if not current_user.is_authenticated:
            return jsonify({'error': 'Usuário não autenticado'}), 401
            
        if current_user.tipo_usuario_id not in [3, 6]:
            return jsonify({'error': 'Usuário não é professor'}), 403

        if current_user.tipo_usuario_id == 6:
            alunos = db.session.query(Usuarios).filter(Usuarios.turma_id == turma_id, Usuarios.tipo_usuario_id == 4).order_by(Usuarios.nome).all()
        else:
            turma_prof = db.session.query(Turmas, ProfessorTurmaEscola).join(
                ProfessorTurmaEscola, Turmas.id == ProfessorTurmaEscola.turma_id
            ).filter(ProfessorTurmaEscola.professor_id == current_user.id, Turmas.id == turma_id).first()
            
            if not turma_prof:
                return jsonify({'error': 'Acesso não autorizado'}), 403

            alunos = db.session.query(Usuarios).filter(Usuarios.escola_id == turma_prof[0].escola_id,
                                                       Usuarios.tipo_ensino_id == turma_prof[0].tipo_ensino_id,
                                                       Usuarios.ano_escolar_id == turma_prof[0].ano_escolar_id,
                                                       Usuarios.turma_id == turma_id,
                                                       Usuarios.tipo_usuario_id == 4,
                                                       Usuarios.nome.isnot(None),
                                                       Usuarios.nome != '').group_by(Usuarios.nome).order_by(Usuarios.nome).all()
        
        return jsonify([{
            'id': aluno.id,
            'nome': aluno.nome,
            'email': aluno.email
        } for aluno in alunos])
    except Exception as e:
        print(f"Erro: {str(e)}")
        return jsonify({'error': str(e)}), 500

@professores_bp.route('/relatorio_aluno/<int:aluno_id>')
@login_required
def relatorio_aluno_novo(aluno_id):
    if current_user.tipo_usuario_id not in [3, 6]:  # Verifica se é professor
        flash('Acesso não autorizado.', 'danger')
        return redirect(url_for('home'))
        
    aluno_info = db.session.query(Usuarios, Turmas, Ano_escolar, Escolas).join(
        Turmas, Usuarios.turma_id == Turmas.id
    ).join(
        Ano_escolar, Turmas.ano_escolar_id == Ano_escolar.id
    ).join(
        Escolas, Turmas.escola_id == Escolas.id
    ).filter(Usuarios.id == aluno_id, Usuarios.tipo_usuario_id == 4).first()
    if not aluno_info:
        flash('Aluno não encontrado.', 'danger')
        return redirect(url_for('professores.listar_turmas'))
        
    # Verificar se o professor tem acesso a esta turma
    if current_user.tipo_usuario_id == 6:
        turma_prof = db.session.query(Turmas).filter(Turmas.id == aluno_info[1].id).first()
    else:
        turma_prof = db.session.query(Turmas, ProfessorTurmaEscola).join(
            ProfessorTurmaEscola, Turmas.id == ProfessorTurmaEscola.turma_id
        ).filter(ProfessorTurmaEscola.professor_id == current_user.id, Turmas.id == aluno_info[1].id).first()
    
    if not turma_prof:
        flash('Você não tem acesso a este aluno.', 'danger')
        return redirect(url_for('professores.listar_turmas'))
    
    # Buscar desempenho nos simulados com disciplinas
    desempenhos = db.session.query(DesempenhoSimulado, SimuladosGerados, Disciplinas).join(
        SimuladosGerados, DesempenhoSimulado.simulado_id == SimuladosGerados.id
    ).join(
        Disciplinas, SimuladosGerados.disciplina_id == Disciplinas.id
    ).filter(DesempenhoSimulado.aluno_id == aluno_id).order_by(DesempenhoSimulado.data_resposta.desc()).all()
    
    # Converter para dicionário para acessar por nome da coluna
    desempenhos_dict = []
    for row in desempenhos:
        desempenhos_dict.append({
            'id': row[0].id,
            'simulado_id': row[0].simulado_id,
            'desempenho': float(row[0].desempenho),  # Converter DECIMAL para float
            'data_resposta': row[0].data_resposta,
            'disciplina_id': row[2].id,
            'disciplina': row[2].nome
        })
    
    # Calcular médias por disciplina
    disciplinas_dict = {}
    for d in desempenhos_dict:
        if d['disciplina'] not in disciplinas_dict:
            disciplinas_dict[d['disciplina']] = {
                'total': 0,
                'count': 0,
                'max': 0,
                'simulados': []
            }
        
        disciplinas_dict[d['disciplina']]['total'] += d['desempenho']
        disciplinas_dict[d['disciplina']]['count'] += 1
        disciplinas_dict[d['disciplina']]['max'] = max(
            disciplinas_dict[d['disciplina']]['max'], 
            d['desempenho']
        )
        disciplinas_dict[d['disciplina']]['simulados'].append(d['desempenho'])
    
    # Preparar listas para os gráficos
    disciplinas = []
    medias_disciplinas = []
    for disciplina, dados in disciplinas_dict.items():
        disciplinas.append(disciplina)
        medias_disciplinas.append(dados['total'] / dados['count'])
    
    # Calcular média geral
    media_geral = sum(medias_disciplinas) / len(medias_disciplinas) if medias_disciplinas else 0
    
    # Preparar dados para o gráfico de evolução temporal
    datas_simulados = []
    notas_simulados = []
    for d in desempenhos_dict:
        data = d['data_resposta'].split(' ')[0] if ' ' in d['data_resposta'] else d['data_resposta']
        datas_simulados.append(data)
        notas_simulados.append(d['desempenho'])
    
    # Identificar disciplinas com melhor e pior desempenho
    disciplinas_ordenadas = sorted(
        disciplinas_dict.items(),
        key=lambda x: x[1]['total'] / x[1]['count'],
        reverse=True
    )
    
    melhores_disciplinas = [d[0] for d in disciplinas_ordenadas[:2]] if len(disciplinas_ordenadas) >= 2 else []
    disciplinas_atencao = [d[0] for d in disciplinas_ordenadas[-2:]] if len(disciplinas_ordenadas) >= 2 else []
    
    # Gerar parecer
    parecer = {
        'comportamento': f"""
            O aluno realizou {len(desempenhos_dict)} simulados até o momento, distribuídos em {len(disciplinas_dict)} disciplinas diferentes.
            {'Demonstra comprometimento com os estudos.' if len(desempenhos_dict) > 5 else 'Está começando a participar das atividades.'}
        """,
        'desempenho': f"""
            A média geral do aluno é {media_geral:.1f}%.
            {'Apresenta um ótimo desempenho!' if media_geral >= 80 
             else 'Está progredindo bem.' if media_geral >= 70 
             else 'Precisa de atenção em algumas áreas.' if media_geral >= 60 
             else 'Necessita de acompanhamento mais próximo.'}
            
            {'Observa-se uma evolução positiva no desempenho.' if len(desempenhos_dict) > 1 and notas_simulados[0] > notas_simulados[-1]
             else 'Mantenha o incentivo para melhorar o desempenho.' if len(desempenhos_dict) > 1
             else 'Continue incentivando a participação nos simulados.'}
        """,
        'destaques': f"""
            {f"Melhor desempenho em: {', '.join(melhores_disciplinas)}" if melhores_disciplinas else ""}
            {f"Disciplinas que precisam de atenção: {', '.join(disciplinas_atencao)}" if disciplinas_atencao else ""}
            
            {'Sua participação regular permite um acompanhamento mais preciso do progresso.' if len(desempenhos_dict) > 3
             else 'Incentive a participação em mais simulados para uma análise mais completa.'}
        """,
        'recomendacoes': f"""
            Recomendações:
            1. Continue incentivando a participação regular nos simulados
            2. {'Mantenha o bom desempenho em ' + ', '.join(melhores_disciplinas) if melhores_disciplinas else 'Participe de mais simulados para identificar pontos fortes'}
            3. {'Dedique atenção extra a ' + ', '.join(disciplinas_atencao) if disciplinas_atencao else 'Continue praticando em todas as disciplinas'}
            4. Estabeleça metas de desempenho para os próximos simulados
        """
    }
    
    # Gerar gráficos com Plotly
    import plotly
    import plotly.graph_objs as go
    import json

    # Gráfico 1: Desempenho por Disciplina
    fig_disc = go.Figure()
    fig_disc.add_trace(go.Bar(
        x=disciplinas,
        y=medias_disciplinas,
        marker_color='rgb(26, 118, 255)',
        text=[f'{m:.1f}%' for m in medias_disciplinas],
        textposition='auto',
    ))
    fig_disc.update_layout(
        title='Desempenho por Disciplina',
        xaxis_title='Disciplinas',
        yaxis_title='Média (%)',
        template='plotly_white',
        showlegend=False,
        margin=dict(t=50, l=50, r=50, b=50),
        yaxis=dict(range=[0, 100])
    )
    grafico_desempenho = json.dumps(fig_disc, cls=plotly.utils.PlotlyJSONEncoder)

    # Gráfico 2: Evolução do Desempenho
    fig_evol = go.Figure()
    fig_evol.add_trace(go.Scatter(
        x=datas_simulados,
        y=notas_simulados,
        mode='lines+markers',
        marker=dict(color='rgb(26, 118, 255)'),
        line=dict(color='rgb(26, 118, 255)'),
    ))
    fig_evol.update_layout(
        title='Evolução do Desempenho',
        xaxis_title='Data do Simulado',
        yaxis_title='Desempenho (%)',
        template='plotly_white',
        showlegend=False,
        margin=dict(t=50, l=50, r=50, b=50),
        yaxis=dict(range=[0, 100])
    )
    grafico_evolucao = json.dumps(fig_evol, cls=plotly.utils.PlotlyJSONEncoder)

    return render_template('professores/relatorio_aluno.html',
                         aluno={'id': aluno_info[0].id, 'nome': aluno_info[0].nome, 'email': aluno_info[0].email},
                         turma={'Ano_escolar': aluno_info[2].nome, 'turma': aluno_info[1].nome, 'escola': aluno_info[3].nome_da_escola},
                         media_geral=media_geral,
                         disciplinas=disciplinas,
                         medias_disciplinas=medias_disciplinas,
                         datas_simulados=datas_simulados,
                         notas_simulados=notas_simulados,
                         parecer=parecer,
                         grafico_desempenho=grafico_desempenho,
                         grafico_evolucao=grafico_evolucao,
                         now=datetime.now())

@professores_bp.route('/relatorio_aluno/<int:aluno_id>/pdf')
@login_required
def relatorio_aluno_pdf(aluno_id):
    if current_user.tipo_usuario_id not in [3, 6]:  # Verifica se é professor
        flash('Acesso não autorizado.', 'danger')
        return redirect(url_for('home'))
        
    aluno_info = db.session.query(Usuarios, Turmas, Ano_escolar, Escolas).join(
        Turmas, Usuarios.turma_id == Turmas.id
    ).join(
        Ano_escolar, Turmas.ano_escolar_id == Ano_escolar.id
    ).join(
        Escolas, Turmas.escola_id == Escolas.id
    ).filter(Usuarios.id == aluno_id, Usuarios.tipo_usuario_id == 4).first()
    if not aluno_info:
        flash('Aluno não encontrado.', 'danger')
        return redirect(url_for('professores.listar_turmas'))
        
    # Verificar se o professor tem acesso a esta turma
    if current_user.tipo_usuario_id == 6:
        turma_prof = db.session.query(Turmas).filter(Turmas.id == aluno_info[1].id).first()
    else:
        turma_prof = db.session.query(Turmas, ProfessorTurmaEscola).join(
            ProfessorTurmaEscola, Turmas.id == ProfessorTurmaEscola.turma_id
        ).filter(ProfessorTurmaEscola.professor_id == current_user.id, Turmas.id == aluno_info[1].id).first()
    
    if not turma_prof:
        flash('Você não tem acesso a este aluno.', 'danger')
        return redirect(url_for('professores.listar_turmas'))
    
    # Buscar desempenho nos simulados com disciplinas
    desempenhos = db.session.query(DesempenhoSimulado, SimuladosGerados, Disciplinas).join(
        SimuladosGerados, DesempenhoSimulado.simulado_id == SimuladosGerados.id
    ).join(
        Disciplinas, SimuladosGerados.disciplina_id == Disciplinas.id
    ).filter(DesempenhoSimulado.aluno_id == aluno_id).order_by(DesempenhoSimulado.data_resposta.desc()).all()
    
    # Converter para dicionário para acessar por nome da coluna
    desempenhos_dict = []
    for row in desempenhos:
        desempenhos_dict.append({
            'id': row[0].id,
            'simulado_id': row[0].simulado_id,
            'desempenho': float(row[0].desempenho),  # Converter DECIMAL para float
            'data_resposta': row[0].data_resposta,
            'disciplina_id': row[2].id,
            'disciplina': row[2].nome
        })
    
    # Calcular médias por disciplina
    disciplinas_dict = {}
    for d in desempenhos_dict:
        if d['disciplina'] not in disciplinas_dict:
            disciplinas_dict[d['disciplina']] = {
                'total': 0,
                'count': 0,
                'max': 0,
                'simulados': []
            }
        
        disciplinas_dict[d['disciplina']]['total'] += d['desempenho']
        disciplinas_dict[d['disciplina']]['count'] += 1
        disciplinas_dict[d['disciplina']]['max'] = max(
            disciplinas_dict[d['disciplina']]['max'], 
            d['desempenho']
        )
        disciplinas_dict[d['disciplina']]['simulados'].append(d['desempenho'])
    
    # Preparar listas para os gráficos
    disciplinas = []
    medias_disciplinas = []
    for disciplina, dados in disciplinas_dict.items():
        disciplinas.append(disciplina)
        medias_disciplinas.append(dados['total'] / dados['count'])
    
    # Calcular média geral
    media_geral = sum(medias_disciplinas) / len(medias_disciplinas) if medias_disciplinas else 0
    
    # Preparar dados para o gráfico de evolução temporal
    datas_simulados = []
    notas_simulados = []
    for d in desempenhos_dict:
        data = d['data_resposta'].split(' ')[0] if ' ' in d['data_resposta'] else d['data_resposta']
        datas_simulados.append(data)
        notas_simulados.append(d['desempenho'])
    
    # Identificar disciplinas com melhor e pior desempenho
    disciplinas_ordenadas = sorted(
        disciplinas_dict.items(),
        key=lambda x: x[1]['total'] / x[1]['count'],
        reverse=True
    )
    
    melhores_disciplinas = [d[0] for d in disciplinas_ordenadas[:2]] if len(disciplinas_ordenadas) >= 2 else []
    disciplinas_atencao = [d[0] for d in disciplinas_ordenadas[-2:]] if len(disciplinas_ordenadas) >= 2 else []
    
    # Gerar parecer
    parecer = {
        'comportamento': f"""
            O aluno realizou {len(desempenhos_dict)} simulados até o momento, distribuídos em {len(disciplinas_dict)} disciplinas diferentes.
            {'Demonstra comprometimento com os estudos.' if len(desempenhos_dict) > 5 else 'Está começando a participar das atividades.'}
        """,
        'desempenho': f"""
            A média geral do aluno é {media_geral:.1f}%.
            {'Apresenta um ótimo desempenho!' if media_geral >= 80 
             else 'Está progredindo bem.' if media_geral >= 70 
             else 'Precisa de atenção em algumas áreas.' if media_geral >= 60 
             else 'Necessita de acompanhamento mais próximo.'}
            
            {'Observa-se uma evolução positiva no desempenho.' if len(desempenhos_dict) > 1 and notas_simulados[0] > notas_simulados[-1]
             else 'Mantenha o incentivo para melhorar o desempenho.' if len(desempenhos_dict) > 1
             else 'Continue incentivando a participação nos simulados.'}
        """,
        'destaques': f"""
            {f"Melhor desempenho em: {', '.join(melhores_disciplinas)}" if melhores_disciplinas else ""}
            {f"Disciplinas que precisam de atenção: {', '.join(disciplinas_atencao)}" if disciplinas_atencao else ""}
            
            {'Sua participação regular permite um acompanhamento mais preciso do progresso.' if len(desempenhos_dict) > 3
             else 'Incentive a participação em mais simulados para uma análise mais completa.'}
        """,
        'recomendacoes': f"""
            Recomendações:
            1. Continue incentivando a participação regular nos simulados
            2. {'Mantenha o bom desempenho em ' + ', '.join(melhores_disciplinas) if melhores_disciplinas else 'Participe de mais simulados para identificar pontos fortes'}
            3. {'Dedique atenção extra a ' + ', '.join(disciplinas_atencao) if disciplinas_atencao else 'Continue praticando em todas as disciplinas'}
            4. Estabeleça metas de desempenho para os próximos simulados
        """
    }
    
    # Gerar gráficos com Plotly
    import plotly
    import plotly.graph_objs as go
    import json

    # Gráfico 1: Desempenho por Disciplina
    fig_disc = go.Figure()
    fig_disc.add_trace(go.Bar(
        x=disciplinas,
        y=medias_disciplinas,
        marker_color='rgb(26, 118, 255)',
        text=[f'{m:.1f}%' for m in medias_disciplinas],
        textposition='auto',
    ))
    fig_disc.update_layout(
        title='Desempenho por Disciplina',
        xaxis_title='Disciplinas',
        yaxis_title='Média (%)',
        template='plotly_white',
        showlegend=False,
        margin=dict(t=50, l=50, r=50, b=50),
        yaxis=dict(range=[0, 100])
    )
    grafico_desempenho = json.dumps(fig_disc, cls=plotly.utils.PlotlyJSONEncoder)

    # Gráfico 2: Evolução do Desempenho
    fig_evol = go.Figure()
    fig_evol.add_trace(go.Scatter(
        x=datas_simulados,
        y=notas_simulados,
        mode='lines+markers',
        marker=dict(color='rgb(26, 118, 255)'),
        line=dict(color='rgb(26, 118, 255)'),
    ))
    fig_evol.update_layout(
        title='Evolução do Desempenho',
        xaxis_title='Data do Simulado',
        yaxis_title='Desempenho (%)',
        template='plotly_white',
        showlegend=False,
        margin=dict(t=50, l=50, r=50, b=50),
        yaxis=dict(range=[0, 100])
    )
    grafico_evolucao = json.dumps(fig_evol, cls=plotly.utils.PlotlyJSONEncoder)

    # Renderizar o template com os dados
    html = render_template('professores/relatorio_aluno_pdf.html',
                         aluno={'id': aluno_info[0].id, 'nome': aluno_info[0].nome, 'email': aluno_info[0].email},
                         turma={'Ano_escolar': aluno_info[2].nome, 'turma': aluno_info[1].turma, 'escola': aluno_info[3].nome_da_escola},
                         media_geral=media_geral,
                         disciplinas=disciplinas,
                         medias_disciplinas=medias_disciplinas,
                         datas_simulados=datas_simulados,
                         notas_simulados=notas_simulados,
                         parecer=parecer,
                         grafico_desempenho=grafico_desempenho,
                         grafico_evolucao=grafico_evolucao,
                         now=datetime.now())
    
    # Gerar PDF
    from weasyprint import HTML
    pdf = HTML(string=html, base_url=request.base_url).write_pdf()
    
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=relatorio_{aluno_info[0].nome.lower().replace(" ", "_")}.pdf'
    
    return response

@professores_bp.route('/api/questoes/<int:disciplina_id>')
@login_required
def api_questoes_por_disciplina(disciplina_id):
    if current_user.tipo_usuario_id not in [3, 6]:  # Verifica se é professor
        return jsonify({'error': 'Acesso não autorizado'}), 403
        
    disciplina = db.session.query(Disciplinas).filter(Disciplinas.id == disciplina_id).first()
    if not disciplina:
        return jsonify({'error': 'Disciplina não encontrada'}), 404
    
    questoes = db.session.query(BancoQuestoes).filter(BancoQuestoes.disciplina_id == disciplina_id).order_by(BancoQuestoes.id.desc()).all()
    
    return jsonify({'questoes': [{'id': q.id, 'enunciado': q.enunciado, 'nivel': q.nivel} for q in questoes]})

@professores_bp.route('/simulados')
@login_required
def listar_simulados():
    # Se for super admin ou professor
    if not current_user.is_authenticated or current_user.tipo_usuario_id not in [3, 6]:
        return render_template('error.html', message='Acesso não autorizado'), 403
        
    # Se for super admin, mostra todos os simulados
    if current_user.tipo_usuario_id == 6:
        simulados = db.session.query(
            SimuladosGeradosProfessor, 
            Disciplinas,
            Usuarios
        ).join(
            Disciplinas, SimuladosGeradosProfessor.disciplina_id == Disciplinas.id
        ).join(
            Usuarios, SimuladosGeradosProfessor.professor_id == Usuarios.id
        ).order_by(SimuladosGeradosProfessor.data_criacao.desc()).all()
    else:
        # Se for professor, mostra apenas seus simulados
        simulados = db.session.query(
            SimuladosGeradosProfessor, 
            Disciplinas,
            Usuarios
        ).join(
            Disciplinas, SimuladosGeradosProfessor.disciplina_id == Disciplinas.id
        ).join(
            Usuarios, SimuladosGeradosProfessor.professor_id == Usuarios.id
        ).filter(
            SimuladosGeradosProfessor.professor_id == current_user.id
        ).order_by(SimuladosGeradosProfessor.data_criacao.desc()).all()

    # Calcula as estatísticas de cada simulado
    desempenhos = {}
    for simulado, _, _ in simulados:
        # Busca as respostas dos alunos para este simulado
        respostas = db.session.query(DesempenhoSimulado).filter(
            DesempenhoSimulado.simulado_id == simulado.id
        ).all()
        
        if respostas:
            notas = [r.desempenho for r in respostas if r.desempenho is not None]
            if notas:
                media = float(sum(notas) / len(notas))
                max_nota = float(max(notas))
                min_nota = float(min(notas))
            else:
                media = max_nota = min_nota = 0
            total_alunos = len(notas)
        else:
            media = max_nota = min_nota = 0
            total_alunos = 0
            
        desempenhos[simulado.id] = {
            'total_alunos': total_alunos,
            'media': media,
            'max_nota': max_nota,
            'min_nota': min_nota
        }

    return render_template('professores/simulados.html', 
                         simulados=simulados,
                         desempenhos=desempenhos)
