from flask import Blueprint, render_template, request, jsonify, g, redirect, url_for, flash, make_response
from flask_login import login_required, current_user
import sqlite3
import json
from datetime import datetime
from functools import wraps

professores_bp = Blueprint('professores', __name__, url_prefix='/professores')

def professor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.tipo_usuario_id not in [2, 6]:  # 2=Professor, 6=Admin
            flash("Acesso não autorizado.", "danger")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated_function

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect('educacional.db')
        g.db.row_factory = sqlite3.Row
    return g.db

@professores_bp.route('/')
@login_required
@professor_required
def index():
    return redirect(url_for('professores.portal'))

@professores_bp.route('/portal')
@login_required
@professor_required
def portal():
    db = get_db()
    cursor = db.cursor()
    
    # Se for admin, busca todas as turmas
    if current_user.tipo_usuario_id == 6:
        cursor.execute("""
            SELECT t.id, t.nome, d.nome as disciplina, s.nome Ano_escolar
            FROM turmas t
            JOIN disciplinas d ON t.disciplina_id = d.id
            JOIN Ano_escolar s ON t.Ano_escolar_id = s.id
            ORDER BY t.nome
        """)
    else:
        # Buscar turmas do professor
        cursor.execute("""
            SELECT t.id, t.nome, d.nome as disciplina, s.nome Ano_escolar
            FROM turmas t
            JOIN disciplinas d ON t.disciplina_id = d.id
            JOIN Ano_escolar s ON t.Ano_escolar_id = s.id
            WHERE t.professor_id = ?
            ORDER BY t.nome
        """, (current_user.id,))
    
    turmas = cursor.fetchall()
    return render_template('portal_professores.html', turmas=turmas)

@professores_bp.route('/ver_alunos/<int:turma_id>')
@login_required
@professor_required
def ver_alunos(turma_id):
    db = get_db()
    cursor = db.cursor()
    
    # Verificar se o professor tem acesso a esta turma
    cursor.execute("""
        SELECT * FROM turmas 
        WHERE id = ? AND professor_id = ?
    """, (turma_id, current_user.id))
    turma = cursor.fetchone()
    
    if not turma:
        return "Acesso não autorizado", 403
    
    # Buscar alunos da turma
    cursor.execute("""
        SELECT a.id, a.nome, a.email
        FROM alunos a
        JOIN alunos_turmas at ON a.id = at.aluno_id
        WHERE at.turma_id = ?
        ORDER BY a.nome
    """, (turma_id,))
    alunos = cursor.fetchall()
    
    return render_template('professores/alunos_turma.html', 
                         alunos=alunos, 
                         turma=turma)

@professores_bp.route('/listar_turmas')
@login_required
@professor_required
def listar_turmas():
    db = get_db()
    cursor = db.cursor()

    # Se for admin, busca todas as turmas
    if current_user.tipo_usuario_id == 6:
        cursor.execute("""
            SELECT DISTINCT t.id, se.nome Ano_escolar, t.turma, e.nome_da_escola AS escola
            FROM professor_turma_escola pte
            JOIN turmas t ON pte.turma_id = t.id
            JOIN Ano_escolar se ON t.Ano_escolar_id = se.id
            JOIN escolas e ON t.escola_id = e.id
            ORDER BY se.nome, t.turma
        """)
    else:
        # Recuperar as turmas vinculadas ao professor
        cursor.execute("""
            SELECT DISTINCT t.id, se.nome Ano_escolar, t.turma, e.nome_da_escola AS escola
            FROM professor_turma_escola pte
            JOIN turmas t ON pte.turma_id = t.id
            JOIN Ano_escolar se ON t.Ano_escolar_id = se.id
            JOIN escolas e ON t.escola_id = e.id
            WHERE pte.professor_id = ?
            ORDER BY se.nome, t.turma
        """, (current_user.id,))
    turmas = cursor.fetchall()

    return render_template('professores/listar_turmas.html', turmas=turmas)

@professores_bp.route('/get_alunos_turma/<int:turma_id>')
@login_required
@professor_required
def get_alunos_turma(turma_id):
    print(f"Buscando alunos para turma {turma_id}")
        
    db = get_db()
    cursor = db.cursor()
    
    # Verificar se o professor tem acesso a esta turma
    cursor.execute("""
        SELECT 1 FROM professor_turma_escola 
        WHERE professor_id = ? AND turma_id = ?
    """, (current_user.id, turma_id))
    
    acesso = cursor.fetchone()
    print(f"Acesso do professor {current_user.id} à turma {turma_id}: {acesso}")
    
    if not acesso:
        return jsonify({'error': 'Turma não encontrada'}), 404
    
    # Buscar alunos da turma
    cursor.execute("""
        SELECT u.id, u.nome, u.email
        FROM usuarios u
        WHERE u.tipo_usuario_id = 4  -- Tipo aluno é 4
        AND u.turma_id = ?
        ORDER BY u.nome
    """, (turma_id,))
    
    alunos = [{'id': row[0], 'nome': row[1], 'email': row[2]} for row in cursor.fetchall()]
    print(f"Alunos encontrados: {len(alunos)}")
    
    return jsonify({'alunos': alunos})

@professores_bp.route('/relatorio_aluno/<int:aluno_id>')
@login_required
@professor_required
def relatorio_aluno(aluno_id):
    db = get_db()
    cursor = db.cursor()
    
    # Buscar informações do aluno
    cursor.execute("""
        SELECT u.id, u.nome, u.email, t.id as turma_id, 
               s.nome Ano_escolar, t.turma, e.nome_da_escola as escola
        FROM usuarios u
        JOIN turmas t ON u.turma_id = t.id
        JOIN Ano_escolar s ON t.Ano_escolar_id = s.id
        JOIN escolas e ON t.escola_id = e.id
        WHERE u.id = ? AND u.tipo_usuario_id = 4
    """, (aluno_id,))
    
    aluno_info = cursor.fetchone()
    if not aluno_info:
        flash('Aluno não encontrado.', 'danger')
        return redirect(url_for('professores.listar_turmas'))
        
    # Verificar se o professor tem acesso a esta turma
    cursor.execute("""
        SELECT 1 FROM professor_turma_escola 
        WHERE professor_id = ? AND turma_id = ?
    """, (current_user.id, aluno_info[3]))
    
    if not cursor.fetchone():
        flash('Você não tem acesso a este aluno.', 'danger')
        return redirect(url_for('professores.listar_turmas'))
    
    # Buscar desempenho nos simulados com disciplinas
    cursor.execute("""
        SELECT ds.id, ds.simulado_id, ds.desempenho, ds.data_resposta,
               d.id as disciplina_id, d.nome as disciplina_nome
        FROM desempenho_simulado ds
        JOIN simulados_gerados sg ON ds.simulado_id = sg.id
        JOIN disciplinas d ON sg.disciplina_id = d.id
        WHERE ds.aluno_id = ?
        ORDER BY ds.data_resposta DESC
    """, (aluno_id,))
    
    # Converter para dicionário para acessar por nome da coluna
    desempenhos = []
    for row in cursor.fetchall():
        desempenhos.append({
            'id': row[0],
            'simulado_id': row[1],
            'desempenho': float(row[2]),  # Converter DECIMAL para float
            'data_resposta': row[3],
            'disciplina_id': row[4],
            'disciplina': row[5]
        })
    
    # Calcular médias por disciplina
    disciplinas_dict = {}
    for d in desempenhos:
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
    for d in desempenhos:
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
            O aluno realizou {len(desempenhos)} simulados até o momento, distribuídos em {len(disciplinas_dict)} disciplinas diferentes.
            {'Demonstra comprometimento com os estudos.' if len(desempenhos) > 5 else 'Está começando a participar das atividades.'}
        """,
        'desempenho': f"""
            A média geral do aluno é {media_geral:.1f}%.
            {'Apresenta um ótimo desempenho!' if media_geral >= 80 
             else 'Está progredindo bem.' if media_geral >= 70 
             else 'Precisa de atenção em algumas áreas.' if media_geral >= 60 
             else 'Necessita de acompanhamento mais próximo.'}
            
            {'Observa-se uma evolução positiva no desempenho.' if len(desempenhos) > 1 and notas_simulados[0] > notas_simulados[-1]
             else 'Mantenha o incentivo para melhorar o desempenho.' if len(desempenhos) > 1
             else 'Continue incentivando a participação nos simulados.'}
        """,
        'destaques': f"""
            {f"Melhor desempenho em: {', '.join(melhores_disciplinas)}" if melhores_disciplinas else ""}
            {f"Disciplinas que precisam de atenção: {', '.join(disciplinas_atencao)}" if disciplinas_atencao else ""}
            
            {'Sua participação regular permite um acompanhamento mais preciso do progresso.' if len(desempenhos) > 3
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
    
    return render_template('professores/relatorio_aluno.html',
                         aluno={'id': aluno_info[0], 'nome': aluno_info[1], 'email': aluno_info[2]},
                         turma={'Ano_escolar': aluno_info[4], 'turma': aluno_info[5], 'escola': aluno_info[6]},
                         media_geral=media_geral,
                         disciplinas=disciplinas,
                         medias_disciplinas=medias_disciplinas,
                         datas_simulados=datas_simulados,
                         notas_simulados=notas_simulados,
                         parecer=parecer)

@professores_bp.route('/relatorio_aluno_pdf/<int:aluno_id>')
@login_required
@professor_required
def relatorio_aluno_pdf(aluno_id):
    db = get_db()
    cursor = db.cursor()
    
    # Buscar informações do aluno
    cursor.execute("""
        SELECT u.id, u.nome, u.email, t.id as turma_id, 
               s.nome Ano_escolar, t.turma, e.nome_da_escola as escola
        FROM usuarios u
        JOIN turmas t ON u.turma_id = t.id
        JOIN Ano_escolar s ON t.Ano_escolar_id = s.id
        JOIN escolas e ON t.escola_id = e.id
        WHERE u.id = ? AND u.tipo_usuario_id = 4
    """, (aluno_id,))
    
    aluno_info = cursor.fetchone()
    if not aluno_info:
        flash('Aluno não encontrado.', 'danger')
        return redirect(url_for('professores.listar_turmas'))
        
    # Verificar se o professor tem acesso a esta turma
    cursor.execute("""
        SELECT 1 FROM professor_turma_escola 
        WHERE professor_id = ? AND turma_id = ?
    """, (current_user.id, aluno_info[3]))
    
    if not cursor.fetchone():
        flash('Você não tem acesso a este aluno.', 'danger')
        return redirect(url_for('professores.listar_turmas'))
    
    # Buscar desempenho nos simulados com disciplinas
    cursor.execute("""
        SELECT ds.id, ds.simulado_id, ds.desempenho, ds.data_resposta,
               d.id as disciplina_id, d.nome as disciplina_nome
        FROM desempenho_simulado ds
        JOIN simulados_gerados sg ON ds.simulado_id = sg.id
        JOIN disciplinas d ON sg.disciplina_id = d.id
        WHERE ds.aluno_id = ?
        ORDER BY ds.data_resposta DESC
    """, (aluno_id,))
    
    # Converter para dicionário para acessar por nome da coluna
    desempenhos = []
    for row in cursor.fetchall():
        desempenhos.append({
            'id': row[0],
            'simulado_id': row[1],
            'desempenho': float(row[2]),  # Converter DECIMAL para float
            'data_resposta': row[3],
            'disciplina_id': row[4],
            'disciplina': row[5]
        })
    
    # Calcular médias por disciplina
    disciplinas_dict = {}
    for d in desempenhos:
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
    for d in desempenhos:
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
            O aluno realizou {len(desempenhos)} simulados até o momento, distribuídos em {len(disciplinas_dict)} disciplinas diferentes.
            {'Demonstra comprometimento com os estudos.' if len(desempenhos) > 5 else 'Está começando a participar das atividades.'}
        """,
        'desempenho': f"""
            A média geral do aluno é {media_geral:.1f}%.
            {'Apresenta um ótimo desempenho!' if media_geral >= 80 
             else 'Está progredindo bem.' if media_geral >= 70 
             else 'Precisa de atenção em algumas áreas.' if media_geral >= 60 
             else 'Necessita de acompanhamento mais próximo.'}
            
            {'Observa-se uma evolução positiva no desempenho.' if len(desempenhos) > 1 and notas_simulados[0] > notas_simulados[-1]
             else 'Mantenha o incentivo para melhorar o desempenho.' if len(desempenhos) > 1
             else 'Continue incentivando a participação nos simulados.'}
        """,
        'destaques': f"""
            {f"Melhor desempenho em: {', '.join(melhores_disciplinas)}" if melhores_disciplinas else ""}
            {f"Disciplinas que precisam de atenção: {', '.join(disciplinas_atencao)}" if disciplinas_atencao else ""}
            
            {'Sua participação regular permite um acompanhamento mais preciso do progresso.' if len(desempenhos) > 3
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
    
    # Renderizar o HTML
    html = render_template('professores/relatorio_aluno_pdf.html',
                         aluno={'id': aluno_info[0], 'nome': aluno_info[1], 'email': aluno_info[2]},
                         turma={'Ano_escolar': aluno_info[4], 'turma': aluno_info[5], 'escola': aluno_info[6]},
                         media_geral=media_geral,
                         disciplinas=disciplinas,
                         medias_disciplinas=medias_disciplinas,
                         datas_simulados=datas_simulados,
                         notas_simulados=notas_simulados,
                         parecer=parecer,
                         data_geracao=datetime.now().strftime('%d/%m/%Y %H:%M'))
    
    # Verificar se o usuário quer baixar como PDF
    if request.args.get('download') == 'pdf':
        try:
            import pdfkit
            pdf = pdfkit.from_string(html, False)
            response = make_response(pdf)
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = f'attachment; filename=relatorio_{aluno_info[1].lower().replace(" ", "_")}.pdf'
            return response
        except Exception as e:
            flash('Erro ao gerar PDF. Por favor, use a opção de impressão do navegador.', 'warning')
            return html
    
    # Se não for download, retorna o HTML para visualização
    return html

@professores_bp.route('/relatorio_turma/<int:turma_id>')
@login_required
@professor_required
def relatorio_turma(turma_id):
    db = get_db()
    cursor = db.cursor()
    
    # Verificar se o professor tem acesso a esta turma
    cursor.execute("""
        SELECT 1 FROM professor_turma_escola 
        WHERE professor_id = ? AND turma_id = ?
    """, (current_user.id, turma_id))
    
    if not cursor.fetchone():
        flash('Você não tem acesso a esta turma.', 'danger')
        return redirect(url_for('professores.listar_turmas'))
    
    # Buscar informações da turma
    cursor.execute("""
        SELECT t.id, s.nome Ano_escolar, t.turma, e.nome_da_escola as escola
        FROM turmas t
        JOIN Ano_escolar s ON t.Ano_escolar_id = s.id
        JOIN escolas e ON t.escola_id = e.id
        WHERE t.id = ?
    """, (turma_id,))
    
    turma_info = cursor.fetchone()
    if not turma_info:
        flash('Turma não encontrada.', 'danger')
        return redirect(url_for('professores.listar_turmas'))
        
    # Inicializar variáveis com valores padrão
    total_alunos = 0
    media_geral = 0
    taxa_participacao = 0
    disciplinas = []
    medias_disciplinas = []
    distribuicao_notas = [0] * 5  # 0-20, 21-40, 41-60, 61-80, 81-100
    grupos = {
        'alto_desempenho': 0,
        'medio_desempenho': 0,
        'baixo_desempenho': 0
    }
    disciplinas_criticas = []
    
    # Buscar todos os alunos da turma
    cursor.execute("""
        SELECT id FROM usuarios
        WHERE turma_id = ? AND tipo_usuario_id = 4
    """, (turma_id,))
    
    alunos = cursor.fetchall()
    total_alunos = len(alunos)
    
    if total_alunos > 0:
        # Buscar desempenho de todos os alunos nos simulados
        cursor.execute("""
            SELECT ds.aluno_id, ds.desempenho, ds.data_resposta,
                   sg.disciplina_id, d.nome as disciplina
            FROM desempenho_simulado ds
            JOIN simulados_gerados sg ON ds.simulado_id = sg.id
            JOIN disciplinas d ON sg.disciplina_id = d.id
            WHERE ds.aluno_id IN (
                SELECT id FROM usuarios 
                WHERE turma_id = ? AND tipo_usuario_id = 4
            )
            ORDER BY ds.data_resposta DESC
        """, (turma_id,))
        
        desempenhos = cursor.fetchall()
        
        if desempenhos:
            # Calcular médias por disciplina
            disciplinas_dict = {}
            alunos_notas = {}  # Para calcular média por aluno
            
            for d in desempenhos:
                aluno_id = d[0]
                desempenho = float(d[1])
                disciplina = d[4]
                
                # Médias por disciplina
                if disciplina not in disciplinas_dict:
                    disciplinas_dict[disciplina] = {'total': 0, 'count': 0}
                disciplinas_dict[disciplina]['total'] += desempenho
                disciplinas_dict[disciplina]['count'] += 1
                
                # Médias por aluno
                if aluno_id not in alunos_notas:
                    alunos_notas[aluno_id] = {'total': 0, 'count': 0}
                alunos_notas[aluno_id]['total'] += desempenho
                alunos_notas[aluno_id]['count'] += 1
            
            # Preparar dados para os gráficos
            for disciplina, dados in disciplinas_dict.items():
                disciplinas.append(disciplina)
                medias_disciplinas.append(dados['total'] / dados['count'])
            
            # Calcular média geral e distribuição de notas
            medias_alunos = []
            for aluno_id, dados in alunos_notas.items():
                if dados['count'] > 0:
                    media = dados['total'] / dados['count']
                    medias_alunos.append(media)
            
            if medias_alunos:
                media_geral = sum(medias_alunos) / len(medias_alunos)
                
                # Calcular distribuição de notas
                for media in medias_alunos:
                    if media <= 20:
                        distribuicao_notas[0] += 1
                    elif media <= 40:
                        distribuicao_notas[1] += 1
                    elif media <= 60:
                        distribuicao_notas[2] += 1
                    elif media <= 80:
                        distribuicao_notas[3] += 1
                    else:
                        distribuicao_notas[4] += 1
                
                # Calcular grupos de desempenho
                grupos = {
                    'alto_desempenho': len([m for m in medias_alunos if m > 80]),
                    'medio_desempenho': len([m for m in medias_alunos if 60 <= m <= 80]),
                    'baixo_desempenho': len([m for m in medias_alunos if m < 60])
                }
            
            # Calcular taxa de participação
            alunos_participantes = len(alunos_notas)
            taxa_participacao = (alunos_participantes / total_alunos * 100) if total_alunos > 0 else 0
            
            # Identificar disciplinas com desempenho crítico
            for disciplina, dados in disciplinas_dict.items():
                media = dados['total'] / dados['count']
                if media < 60:
                    disciplinas_criticas.append(disciplina)
    
    # Gerar parecer pedagógico
    parecer = {
        'engajamento': f"""
            A turma possui {total_alunos} alunos, dos quais {len(alunos_notas) if 'alunos_notas' in locals() else 0} ({taxa_participacao:.1f}%) 
            participaram dos simulados até o momento.
            {'A participação está excelente!' if taxa_participacao >= 90
             else 'A participação está boa, mas pode melhorar.' if taxa_participacao >= 70
             else 'É necessário incentivar mais a participação nos simulados.'}
        """,
        'desempenho': f"""
            A média geral da turma é {media_geral:.1f}%.
            {'O desempenho geral está muito bom!' if media_geral >= 80
             else 'O desempenho está satisfatório.' if media_geral >= 70
             else 'O desempenho precisa de atenção.' if media_geral >= 60
             else 'O desempenho está crítico e requer intervenção imediata.'}
            
            {f"As disciplinas que se destacam positivamente são: {', '.join([d for d, dados in disciplinas_dict.items() if dados['total']/dados['count'] >= 80])}" if 'disciplinas_dict' in locals() and any(dados['total']/dados['count'] >= 80 for dados in disciplinas_dict.values()) else ''}
        """,
        'pontos_atencao': f"""
            {'Não foram identificadas disciplinas com desempenho crítico.' if not disciplinas_criticas else
             f"As seguintes disciplinas requerem atenção especial: {', '.join(disciplinas_criticas)}"}
            
            {'Há um número significativo de alunos com baixo desempenho (' + str(grupos['baixo_desempenho']) + ' alunos).' if grupos['baixo_desempenho'] > total_alunos * 0.3 else
             'A distribuição de notas está relativamente equilibrada.'}
        """,
        'recomendacoes': f"""
            Recomendações para melhorar o desempenho da turma:
            
            1. {'Focar em aumentar a participação nos simulados.' if taxa_participacao < 70 else
                'Manter o bom nível de participação nos simulados.'}
            
            2. {'Realizar uma revisão completa dos conteúdos nas disciplinas críticas: ' + ', '.join(disciplinas_criticas) if disciplinas_criticas else
                'Continuar com a metodologia atual que está trazendo bons resultados.'}
            
            3. {'Considerar uma mudança na abordagem metodológica, pois muitos alunos estão com dificuldades.' if grupos['baixo_desempenho'] > total_alunos * 0.3 else
                'Dar atenção individualizada aos alunos com baixo desempenho.' if grupos['baixo_desempenho'] > 0 else
                'Propor desafios adicionais para manter o alto nível de engajamento.'}
            
            4. {'Implementar atividades de reforço em pequenos grupos.' if grupos['baixo_desempenho'] > 5 else
                'Manter o acompanhamento próximo do progresso individual.'}
            
            5. {'Considerar uma reunião com os responsáveis para discutir estratégias de apoio.' if media_geral < 60 else
                'Compartilhar as boas práticas com outras turmas.'}
        """
    }
    
    return render_template('professores/relatorio_turma.html',
                         turma={'id': turma_info[0], 'Ano_escolar': turma_info[1], 
                               'turma': turma_info[2], 'escola': turma_info[3]},
                         total_alunos=total_alunos,
                         media_geral=media_geral,
                         taxa_participacao=taxa_participacao,
                         disciplinas=disciplinas,
                         medias_disciplinas=medias_disciplinas,
                         distribuicao_notas=distribuicao_notas,
                         grupos=grupos,
                         parecer=parecer,
                         now=datetime.now(),
                         zip=zip)

@professores_bp.route('/relatorio_turma_pdf/<int:turma_id>')
@login_required
@professor_required
def relatorio_turma_pdf(turma_id):
    db = get_db()
    cursor = db.cursor()
    
    # Verificar se o professor tem acesso a esta turma
    cursor.execute("""
        SELECT 1 FROM professor_turma_escola 
        WHERE professor_id = ? AND turma_id = ?
    """, (current_user.id, turma_id))
    
    if not cursor.fetchone():
        flash('Você não tem acesso a esta turma.', 'danger')
        return redirect(url_for('professores.listar_turmas'))
    
    # Buscar informações da turma
    cursor.execute("""
        SELECT t.id, s.nome Ano_escolar, t.turma, e.nome_da_escola as escola
        FROM turmas t
        JOIN Ano_escolar s ON t.Ano_escolar_id = s.id
        JOIN escolas e ON t.escola_id = e.id
        WHERE t.id = ?
    """, (turma_id,))
    
    turma_info = cursor.fetchone()
    
    # Buscar todos os alunos da turma
    cursor.execute("""
        SELECT id FROM usuarios
        WHERE turma_id = ? AND tipo_usuario_id = 4
    """, (turma_id,))
    
    alunos = cursor.fetchall()
    total_alunos = len(alunos)
    
    # Buscar desempenho de todos os alunos nos simulados
    cursor.execute("""
        SELECT ds.aluno_id, ds.desempenho, ds.data_resposta,
               sg.disciplina_id, d.nome as disciplina
        FROM desempenho_simulado ds
        JOIN simulados_gerados sg ON ds.simulado_id = sg.id
        JOIN disciplinas d ON sg.disciplina_id = d.id
        WHERE ds.aluno_id IN (
            SELECT id FROM usuarios 
            WHERE turma_id = ? AND tipo_usuario_id = 4
        )
        ORDER BY ds.data_resposta DESC
    """, (turma_id,))
    
    desempenhos = cursor.fetchall()
    
    # Calcular médias por disciplina
    disciplinas_dict = {}
    alunos_notas = {}  # Para calcular média por aluno
    
    for d in desempenhos:
        aluno_id = d[0]
        desempenho = float(d[1])
        disciplina = d[4]
        
        # Médias por disciplina
        if disciplina not in disciplinas_dict:
            disciplinas_dict[disciplina] = {'total': 0, 'count': 0}
        disciplinas_dict[disciplina]['total'] += desempenho
        disciplinas_dict[disciplina]['count'] += 1
        
        # Médias por aluno
        if aluno_id not in alunos_notas:
            alunos_notas[aluno_id] = {'total': 0, 'count': 0}
        alunos_notas[aluno_id]['total'] += desempenho
        alunos_notas[aluno_id]['count'] += 1
    
    # Preparar dados para os gráficos
    disciplinas = []
    medias_disciplinas = []
    for disciplina, dados in disciplinas_dict.items():
        disciplinas.append(disciplina)
        medias_disciplinas.append(dados['total'] / dados['count'])
    
    # Calcular média geral e distribuição de notas
    medias_alunos = []
    for aluno_id, dados in alunos_notas.items():
        if dados['count'] > 0:
            media = dados['total'] / dados['count']
            medias_alunos.append(media)
    
    media_geral = sum(medias_alunos) / len(medias_alunos) if medias_alunos else 0
    
    # Calcular distribuição de notas
    distribuicao_notas = [0] * 5  # 0-20, 21-40, 41-60, 61-80, 81-100
    for media in medias_alunos:
        if media <= 20:
            distribuicao_notas[0] += 1
        elif media <= 40:
            distribuicao_notas[1] += 1
        elif media <= 60:
            distribuicao_notas[2] += 1
        elif media <= 80:
            distribuicao_notas[3] += 1
        else:
            distribuicao_notas[4] += 1
    
    # Calcular grupos de desempenho
    grupos = {
        'alto_desempenho': len([m for m in medias_alunos if m > 80]),
        'medio_desempenho': len([m for m in medias_alunos if 60 <= m <= 80]),
        'baixo_desempenho': len([m for m in medias_alunos if m < 60])
    }
    
    # Calcular taxa de participação
    alunos_participantes = len(alunos_notas)
    taxa_participacao = (alunos_participantes / total_alunos * 100) if total_alunos > 0 else 0
    
    # Identificar disciplinas com desempenho crítico
    disciplinas_criticas = []
    for disciplina, dados in disciplinas_dict.items():
        media = dados['total'] / dados['count']
        if media < 60:
            disciplinas_criticas.append(disciplina)
    
    # Gerar parecer pedagógico
    parecer = {
        'engajamento': f"""
            A turma possui {total_alunos} alunos, dos quais {alunos_participantes} ({taxa_participacao:.1f}%) 
            participaram dos simulados até o momento.
            {'A participação está excelente!' if taxa_participacao >= 90
             else 'A participação está boa, mas pode melhorar.' if taxa_participacao >= 70
             else 'É necessário incentivar mais a participação nos simulados.'}
        """,
        'desempenho': f"""
            A média geral da turma é {media_geral:.1f}%.
            {'O desempenho geral está muito bom!' if media_geral >= 80
             else 'O desempenho está satisfatório.' if media_geral >= 70
             else 'O desempenho precisa de atenção.' if media_geral >= 60
             else 'O desempenho está crítico e requer intervenção imediata.'}
            
            {f"As disciplinas que se destacam positivamente são: {', '.join([d for d, dados in disciplinas_dict.items() if dados['total']/dados['count'] >= 80])}" if any(dados['total']/dados['count'] >= 80 for dados in disciplinas_dict.values()) else ''}
        """,
        'pontos_atencao': f"""
            {'Não foram identificadas disciplinas com desempenho crítico.' if not disciplinas_criticas else
             f"As seguintes disciplinas requerem atenção especial: {', '.join(disciplinas_criticas)}"}
            
            {'Há um número significativo de alunos com baixo desempenho (' + str(grupos['baixo_desempenho']) + ' alunos).' if grupos['baixo_desempenho'] > total_alunos * 0.3 else
             'A distribuição de notas está relativamente equilibrada.'}
        """,
        'recomendacoes': f"""
            Recomendações para melhorar o desempenho da turma:
            
            1. {'Focar em aumentar a participação nos simulados.' if taxa_participacao < 70 else
                'Manter o bom nível de participação nos simulados.'}
            
            2. {'Realizar uma revisão completa dos conteúdos nas disciplinas críticas: ' + ', '.join(disciplinas_criticas) if disciplinas_criticas else
                'Continuar com a metodologia atual que está trazendo bons resultados.'}
            
            3. {'Considerar uma mudança na abordagem metodológica, pois muitos alunos estão com dificuldades.' if grupos['baixo_desempenho'] > total_alunos * 0.3 else
                'Dar atenção individualizada aos alunos com baixo desempenho.' if grupos['baixo_desempenho'] > 0 else
                'Propor desafios adicionais para manter o alto nível de engajamento.'}
            
            4. {'Implementar atividades de reforço em pequenos grupos.' if grupos['baixo_desempenho'] > 5 else
                'Manter o acompanhamento próximo do progresso individual.'}
            
            5. {'Considerar uma reunião com os responsáveis para discutir estratégias de apoio.' if media_geral < 60 else
                'Compartilhar as boas práticas com outras turmas.'}
        """
    }
    
    # Renderizar o HTML
    html = render_template('professores/relatorio_turma_pdf.html',
                         turma={'id': turma_info[0], 'Ano_escolar': turma_info[1], 
                               'turma': turma_info[2], 'escola': turma_info[3]},
                         total_alunos=total_alunos,
                         media_geral=media_geral,
                         taxa_participacao=taxa_participacao,
                         disciplinas=disciplinas,
                         medias_disciplinas=medias_disciplinas,
                         distribuicao_notas=distribuicao_notas,
                         grupos=grupos,
                         parecer=parecer,
                         data_geracao=datetime.now().strftime('%d/%m/%Y %H:%M'))
    
    # Verificar se o usuário quer baixar como PDF
    if request.args.get('download') == 'pdf':
        try:
            import pdfkit
            pdf = pdfkit.from_string(html, False)
            response = make_response(pdf)
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = f'attachment; filename=relatorio_turma_{turma_info[2].lower()}.pdf'
            return response
        except Exception as e:
            flash('Erro ao gerar PDF. Por favor, use a opção de impressão do navegador.', 'warning')
            return html
    
    # Se não for download, retorna o HTML para visualização
    return html

def analisar_comportamento(cursor, aluno_id):
    # Buscar informações de comportamento e engajamento
    cursor.execute("""
        SELECT COUNT(*) as total_simulados,
               COUNT(DISTINCT DATE(data_realizacao)) as dias_ativos
        FROM resultados_simulados
        WHERE aluno_id = ?
    """, (aluno_id,))
    
    comportamento = cursor.fetchone()
    if not comportamento:
        return "O aluno ainda não realizou nenhum simulado no portal."
        
    total_simulados = comportamento[0]
    dias_ativos = comportamento[1]
    
    # Análise personalizada baseada nos dados
    if total_simulados == 0:
        return "O aluno ainda não realizou nenhum simulado no portal."
    
    # Buscar média geral do aluno
    cursor.execute("""
        SELECT AVG(nota) as media_geral
        FROM resultados_simulados
        WHERE aluno_id = ?
    """, (aluno_id,))
    
    media_result = cursor.fetchone()
    media_geral = media_result[0] if media_result and media_result[0] else 0
    
    analise = f"""
    O aluno demonstra um nível de engajamento {'alto' if total_simulados > 10 else 'moderado' if total_simulados > 5 else 'inicial'} 
    com o portal, tendo completado {total_simulados} simulados em {dias_ativos} dias diferentes. 
    {'Isso demonstra consistência nos estudos.' if dias_ativos > 5 else 'Há espaço para maior regularidade nos estudos.'}
    
    A média geral atual é de {media_geral:.1f}%, o que indica um desempenho {'excelente' if media_geral >= 90 
        else 'muito bom' if media_geral >= 80 
        else 'bom' if media_geral >= 70 
        else 'regular' if media_geral >= 60 
        else 'que precisa de atenção'}.
    """
    
    return analise

def analisar_desempenho(notas_disciplinas, evolucao):
    if not notas_disciplinas:
        return "Ainda não há dados suficientes para análise de desempenho."
    
    # Análise das médias por disciplina
    medias = [(nota[1], nota[2]) for nota in notas_disciplinas]
    melhor_disciplina = max(medias, key=lambda x: x[1])
    pior_disciplina = min(medias, key=lambda x: x[1])
    
    # Análise da evolução
    if evolucao and len(evolucao) > 1:
        primeira_nota = evolucao[0][1]
        ultima_nota = evolucao[-1][1]
        tendencia = "crescente" if ultima_nota > primeira_nota else "decrescente" if ultima_nota < primeira_nota else "estável"
    else:
        tendencia = "ainda não estabelecida"
    
    analise = f"""
    O aluno apresenta melhor desempenho em {melhor_disciplina[0]} (média {melhor_disciplina[1]:.1f}%) 
    e maior dificuldade em {pior_disciplina[0]} (média {pior_disciplina[1]:.1f}%). 
    A tendência de desempenho é {tendencia}.
    """
    
    return analise

def identificar_destaques(notas_disciplinas):
    if not notas_disciplinas:
        return "Ainda não há dados suficientes para identificar áreas de destaque."
    
    destaques = []
    for disciplina, media in [(nota[1], nota[2]) for nota in notas_disciplinas]:
        if media >= 80:
            destaques.append(f"{disciplina} ({media:.1f}%)")
    
    if destaques:
        return f"""
        O aluno demonstra excelência nas seguintes disciplinas: {', '.join(destaques)}. 
        Estas áreas representam pontos fortes que podem ser aproveitados para potencializar o aprendizado em outras disciplinas.
        """
    else:
        return "O aluno ainda não atingiu níveis de excelência (acima de 80%) em nenhuma disciplina, mas mostra potencial para desenvolvimento."

def gerar_recomendacoes(notas_disciplinas, evolucao):
    if not notas_disciplinas:
        return "Recomenda-se começar a realizar os simulados disponíveis para obter uma avaliação mais precisa."
    
    recomendacoes = []
    
    # Identificar disciplinas que precisam de atenção
    for disciplina, media in [(nota[1], nota[2]) for nota in notas_disciplinas]:
        if media < 60:
            recomendacoes.append(f"Dedicar mais tempo aos estudos de {disciplina}")
    
    # Analisar regularidade
    if evolucao:
        datas = [ev[0] for ev in evolucao]
        if len(datas) < 5:
            recomendacoes.append("Aumentar a frequência de realização dos simulados para um acompanhamento mais efetivo")
    
    if recomendacoes:
        return "Recomendações para melhorar o desempenho:\n- " + "\n- ".join(recomendacoes)
    else:
        return "O aluno está no caminho certo. Recomenda-se manter a dedicação atual aos estudos."

def analisar_desempenho(notas_disciplinas, evolucao):
    if not notas_disciplinas:
        return "Ainda não há dados suficientes para análise de desempenho."
    
    # Análise das médias por disciplina
    medias = [(nota[1], nota[2]) for nota in notas_disciplinas]
    melhor_disciplina = max(medias, key=lambda x: x[1])
    pior_disciplina = min(medias, key=lambda x: x[1])
    
    # Análise da evolução
    if evolucao and len(evolucao) > 1:
        primeira_nota = evolucao[0][1]
        ultima_nota = evolucao[-1][1]
        tendencia = "crescente" if ultima_nota > primeira_nota else "decrescente" if ultima_nota < primeira_nota else "estável"
    else:
        tendencia = "ainda não estabelecida"
    
    analise = f"""
    O aluno apresenta melhor desempenho em {melhor_disciplina[0]} (média {melhor_disciplina[1]:.1f}%) 
    e maior dificuldade em {pior_disciplina[0]} (média {pior_disciplina[1]:.1f}%). 
    A tendência de desempenho é {tendencia}.
    """
    
    return analise

def identificar_destaques(notas_disciplinas):
    if not notas_disciplinas:
        return "Ainda não há dados suficientes para identificar áreas de destaque."
    
    destaques = []
    for disciplina, media in [(nota[1], nota[2]) for nota in notas_disciplinas]:
        if media >= 80:
            destaques.append(f"{disciplina} ({media:.1f}%)")
    
    if destaques:
        return f"""
        O aluno demonstra excelência nas seguintes disciplinas: {', '.join(destaques)}. 
        Estas áreas representam pontos fortes que podem ser aproveitados para potencializar o aprendizado em outras disciplinas.
        """
    else:
        return "O aluno ainda não atingiu níveis de excelência (acima de 80%) em nenhuma disciplina, mas mostra potencial para desenvolvimento."

def gerar_recomendacoes(notas_disciplinas, evolucao):
    if not notas_disciplinas:
        return "Recomenda-se começar a realizar os simulados disponíveis para obter uma avaliação mais precisa."
    
    recomendacoes = []
    
    # Identificar disciplinas que precisam de atenção
    for disciplina, media in [(nota[1], nota[2]) for nota in notas_disciplinas]:
        if media < 60:
            recomendacoes.append(f"Dedicar mais tempo aos estudos de {disciplina}")
    
    # Analisar regularidade
    if evolucao:
        datas = [ev[0] for ev in evolucao]
        if len(datas) < 5:
            recomendacoes.append("Aumentar a frequência de realização dos simulados para um acompanhamento mais efetivo")
    
    if recomendacoes:
        return "Recomendações para melhorar o desempenho:\n- " + "\n- ".join(recomendacoes)
    else:
        return "O aluno está no caminho certo. Recomenda-se manter a dedicação atual aos estudos."
    .first())
    
    media_geral = media_result[0] if media_result and media_result[0] else 0
    
    analise = f"""
    O aluno demonstra um nível de engajamento {'alto' if total_simulados > 10 else 'moderado' if total_simulados > 5 else 'inicial'} 
    com o portal, tendo completado {total_simulados} simulados em {dias_ativos} dias diferentes. 
    {'Isso demonstra consistência nos estudos.' if dias_ativos > 5 else 'Há espaço para maior regularidade nos estudos.'}
    
    A média geral atual é de {media_geral:.1f}%, o que indica um desempenho {'excelente' if media_geral >= 90 
        else 'muito bom' if media_geral >= 80 
        else 'bom' if media_geral >= 70 
        else 'regular' if media_geral >= 60 
        else 'que precisa de atenção'}.
    """
    
    return analise

def analisar_desempenho(notas_disciplinas, evolucao):
    if not notas_disciplinas:
        return "Ainda não há dados suficientes para análise de desempenho."
    
    # Análise das médias por disciplina
    medias = [(nota[1], nota[2]) for nota in notas_disciplinas]
    melhor_disciplina = max(medias, key=lambda x: x[1])
    pior_disciplina = min(medias, key=lambda x: x[1])
    
    # Análise da evolução
    if evolucao and len(evolucao) > 1:
        primeira_nota = evolucao[0][1]
        ultima_nota = evolucao[-1][1]
        tendencia = "crescente" if ultima_nota > primeira_nota else "decrescente" if ultima_nota < primeira_nota else "estável"
    else:
        tendencia = "ainda não estabelecida"
    
    analise = f"""
    O aluno apresenta melhor desempenho em {melhor_disciplina[0]} (média {melhor_disciplina[1]:.1f}%) 
    e maior dificuldade em {pior_disciplina[0]} (média {pior_disciplina[1]:.1f}%). 
    A tendência de desempenho é {tendencia}.
    """
    
    return analise

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
