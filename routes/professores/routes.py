from flask import render_template, jsonify, g, redirect, url_for, flash, make_response, request
from flask_login import login_required, current_user
import sqlite3
import logging
from . import professores_bp
from models import (
    User, Turma, Disciplina, 
    TIPO_USUARIO_PROFESSOR, TIPO_USUARIO_ALUNO,
    professor_turma_escola
)

# Configurar logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def get_db():
    """Conecta ao banco de dados."""
    if 'db' not in g:
        g.db = sqlite3.connect('educacional.db')
        g.db.row_factory = sqlite3.Row
    return g.db

@professores_bp.route('/')
@login_required
def portal_professores():
    """Rota principal do portal de professores."""
    if not current_user.is_authenticated or current_user.tipo_usuario_id != TIPO_USUARIO_PROFESSOR:
        return render_template('error.html', message='Acesso não autorizado'), 403
        
    # Buscar turmas do professor
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute("""
        SELECT 
            t.id,
            t.turma,
            t.tipo_ensino_id,
            t.serie_id,
            e.nome_da_escola as escola_nome,
            s.nome as serie_nome
        FROM turmas t
        JOIN professor_turma_escola pte ON t.id = pte.turma_id
        JOIN escolas e ON e.id = t.escola_id
        JOIN series s ON s.id = t.serie_id
        WHERE pte.professor_id = ?
        ORDER BY t.tipo_ensino_id, t.serie_id, t.turma
    """, (current_user.id,))
    
    turmas = cursor.fetchall()
    
    return render_template('professores/portal.html', 
                         turmas=turmas)

@professores_bp.route('/listar_turmas', methods=['GET'])
@login_required
def listar_turmas():
    """Lista as turmas do professor."""
    if not current_user.is_authenticated or current_user.tipo_usuario_id != TIPO_USUARIO_PROFESSOR:  
        return render_template('error.html', message='Acesso não autorizado'), 403

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT 
            t.id,
            t.serie_id,
            t.turma,
            e.nome_da_escola as escola_nome,
            s.nome as serie_nome
        FROM turmas t
        JOIN professor_turma_escola pte ON t.id = pte.turma_id
        JOIN escolas e ON e.id = pte.escola_id
        JOIN series s ON s.id = t.serie_id
        WHERE pte.professor_id = ?
        ORDER BY t.serie_id, t.turma
    """, (current_user.id,))
    
    turmas = cursor.fetchall()
    return render_template('professores/listar_turmas.html', turmas=turmas)

@professores_bp.route('/api/turmas', methods=['GET'])
@login_required
def api_listar_turmas():
    """API para listar as turmas do professor."""
    if not current_user.is_authenticated or current_user.tipo_usuario_id != TIPO_USUARIO_PROFESSOR:
        return jsonify([])

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT 
            t.id,
            t.serie_id,
            t.turma,
            e.nome_da_escola as escola_nome,
            s.nome as serie_nome
        FROM turmas t
        JOIN professor_turma_escola pte ON t.id = pte.turma_id
        JOIN escolas e ON e.id = pte.escola_id
        JOIN series s ON s.id = t.serie_id
        WHERE pte.professor_id = ?
        ORDER BY t.serie_id, t.turma
    """, (current_user.id,))
    
    turmas = cursor.fetchall()
    return jsonify([{
        'id': turma[0],
        'serie': turma[1],
        'turma': turma[2],
        'escola': turma[3],
        'serie_nome': turma[4]
    } for turma in turmas])

@professores_bp.route('/turma/<int:turma_id>/relatorio')
@login_required
def relatorio_turma(turma_id):
    if current_user.tipo_usuario_id != 3:  # Verifica se é professor
        flash('Acesso não autorizado.', 'danger')
        return redirect(url_for('home'))
        
    db = get_db()
    cursor = db.cursor()
    
    # Verificar se o professor tem acesso a esta turma
    cursor.execute("""
        SELECT t.id, t.turma, s.nome as serie, e.nome_da_escola as escola
        FROM turmas t
        JOIN professor_turma_escola pte ON t.id = pte.turma_id
        JOIN series s ON t.serie_id = s.id
        JOIN escolas e ON e.id = pte.escola_id
        WHERE t.id = ? AND pte.professor_id = ?
    """, (turma_id, current_user.id))
    
    turma_info = cursor.fetchone()
    if not turma_info:
        flash('Você não tem acesso a esta turma.', 'danger')
        return redirect(url_for('professores.listar_turmas'))
    
    # Buscar alunos da turma
    cursor.execute("""
        SELECT u.id, u.nome, u.email
        FROM usuarios u
        WHERE u.turma_id = ? AND u.tipo_usuario_id = 4
        ORDER BY u.nome
    """, (turma_id,))
    
    alunos = []
    for aluno in cursor.fetchall():
        # Buscar desempenho do aluno
        cursor.execute("""
            SELECT ds.desempenho, ds.data_resposta,
                   d.nome as disciplina
            FROM desempenho_simulado ds
            JOIN simulados_gerados sg ON ds.simulado_id = sg.id
            JOIN disciplinas d ON sg.disciplina_id = d.id
            WHERE ds.aluno_id = ?
            ORDER BY ds.data_resposta DESC
        """, (aluno[0],))
        
        desempenhos = cursor.fetchall()
        
        # Calcular médias por disciplina
        disciplinas_dict = {}
        for d in desempenhos:
            disciplina = d[2]
            if disciplina not in disciplinas_dict:
                disciplinas_dict[disciplina] = {
                    'total': 0,
                    'count': 0
                }
            disciplinas_dict[disciplina]['total'] += float(d[0])
            disciplinas_dict[disciplina]['count'] += 1
        
        # Calcular média geral do aluno
        media_geral = 0
        if disciplinas_dict:
            total_medias = sum(d['total']/d['count'] for d in disciplinas_dict.values())
            media_geral = total_medias / len(disciplinas_dict)
        
        alunos.append({
            'id': aluno[0],
            'nome': aluno[1],
            'email': aluno[2],
            'media_geral': media_geral,
            'total_simulados': len(desempenhos),
            'disciplinas': disciplinas_dict
        })
    
    # Calcular estatísticas da turma
    total_alunos = len(alunos)
    media_turma = sum(a['media_geral'] for a in alunos) / total_alunos if total_alunos > 0 else 0
    
    # Ordenar alunos por média geral
    alunos_ordenados = sorted(alunos, key=lambda x: x['media_geral'], reverse=True) if alunos else []
    
    # Identificar melhores alunos e alunos que precisam de atenção
    melhores_alunos = alunos_ordenados[:3] if len(alunos_ordenados) >= 3 else alunos_ordenados
    alunos_atencao = sorted(alunos_ordenados[-3:] if len(alunos_ordenados) >= 3 else alunos_ordenados, key=lambda x: x['media_geral'])
    
    # Calcular distribuição de notas
    faixas_notas = {
        'Excelente (90-100)': len([a for a in alunos if a['media_geral'] >= 90]),
        'Ótimo (80-89)': len([a for a in alunos if 80 <= a['media_geral'] < 90]),
        'Bom (70-79)': len([a for a in alunos if 70 <= a['media_geral'] < 80]),
        'Regular (60-69)': len([a for a in alunos if 60 <= a['media_geral'] < 70]),
        'Precisa Melhorar (<60)': len([a for a in alunos if a['media_geral'] < 60])
    }
    
    # Gerar gráficos apenas se houver dados
    grafico_distribuicao = ''
    grafico_medias = ''
    
    if alunos:
        import matplotlib
        matplotlib.use('Agg')  # Usar backend não-interativo
        import matplotlib.pyplot as plt
        import io
        import base64
        from datetime import datetime
        
        # Configuração do estilo dos gráficos
        plt.style.use('bmh')
        plt.rcParams['figure.facecolor'] = 'white'
        plt.rcParams['axes.facecolor'] = 'white'
        plt.rcParams['axes.grid'] = True
        plt.rcParams['grid.alpha'] = 0.3
        plt.rcParams['axes.labelcolor'] = '#333333'
        plt.rcParams['xtick.color'] = '#333333'
        plt.rcParams['ytick.color'] = '#333333'
        
        try:
            # Gráfico de distribuição de notas
            fig, ax = plt.subplots(figsize=(10, 6))
            bars = ax.bar(list(faixas_notas.keys()), list(faixas_notas.values()), color='#0d6efd', alpha=0.7)
            ax.set_title('Distribuição de Notas da Turma', pad=20, color='#333333', fontsize=14)
            ax.set_xlabel('Faixas de Notas', color='#333333')
            ax.set_ylabel('Número de Alunos', color='#333333')
            plt.xticks(rotation=45, ha='right', color='#333333')
            
            # Adicionar valores sobre as barras
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                        f'{int(height)}',
                        ha='center', va='bottom', color='#333333')
            
            # Salvar gráfico como base64
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', bbox_inches='tight', dpi=300, facecolor='white')
            buffer.seek(0)
            grafico_distribuicao = base64.b64encode(buffer.getvalue()).decode()
            plt.close()
            
            # Gráfico de médias individuais
            fig, ax = plt.subplots(figsize=(12, 6))
            
            # Tratar nomes vazios e pegar apenas o primeiro nome
            nomes = []
            for aluno in alunos_ordenados:
                nome_completo = aluno['nome'].strip()
                if nome_completo:
                    partes_nome = nome_completo.split()
                    if partes_nome:
                        nomes.append(partes_nome[0])
                    else:
                        nomes.append('Aluno')
                else:
                    nomes.append('Aluno')
            
            medias = [a['media_geral'] for a in alunos_ordenados]
            
            bars = ax.bar(nomes, medias, color='#0d6efd', alpha=0.7)
            ax.axhline(y=media_turma, color='red', linestyle='--', label=f'Média da Turma: {media_turma:.1f}%')
            
            ax.set_title('Médias Individuais dos Alunos', pad=20, color='#333333', fontsize=14)
            ax.set_xlabel('Alunos', color='#333333')
            ax.set_ylabel('Média Geral (%)', color='#333333')
            plt.xticks(rotation=45, ha='right', color='#333333')
            ax.set_ylim(0, 100)
            ax.legend()
            
            # Adicionar valores sobre as barras
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height:.1f}%',
                        ha='center', va='bottom', color='#333333')
            
            # Salvar gráfico como base64
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', bbox_inches='tight', dpi=300, facecolor='white')
            buffer.seek(0)
            grafico_medias = base64.b64encode(buffer.getvalue()).decode()
            plt.close()
            
        except Exception as e:
            print(f"Erro ao gerar gráficos: {str(e)}")
            grafico_distribuicao = ''
            grafico_medias = ''
    
    return render_template('professores/relatorio_turma.html',
                         turma={'id': turma_info[0], 
                               'nome': turma_info[1],
                               'serie': turma_info[2],
                               'escola': turma_info[3]},
                         alunos=alunos_ordenados,
                         total_alunos=total_alunos,
                         media_turma=media_turma,
                         melhores_alunos=melhores_alunos,
                         alunos_atencao=alunos_atencao,
                         faixas_notas=faixas_notas,
                         grafico_distribuicao=grafico_distribuicao,
                         grafico_medias=grafico_medias,
                         now=datetime.now())

@professores_bp.route('/aluno/<int:aluno_id>/relatorio')
@login_required
def relatorio_aluno(aluno_id):
    """Exibe o relatório do aluno."""
    try:
        if not current_user.is_authenticated or current_user.tipo_usuario_id != TIPO_USUARIO_PROFESSOR:  
            return render_template('error.html', message='Acesso não autorizado'), 403

        db = get_db()
        cursor = db.cursor()

        # Busca informações do aluno
        cursor.execute("""
            SELECT 
                u.id, u.nome, u.email, u.turma_id, u.serie_id,
                t.nome as turma_nome,
                s.nome as serie_nome,
                e.nome as escola_nome
            FROM usuarios u
            LEFT JOIN turmas t ON u.turma_id = t.id
            LEFT JOIN series s ON u.serie_id = s.id
            LEFT JOIN escolas e ON u.escola_id = e.id
            WHERE u.id = ? AND u.tipo_usuario_id = 4
        """, (aluno_id,))
        
        aluno = cursor.fetchone()
        if not aluno:
            return render_template('error.html', message='Aluno não encontrado'), 404

        # Busca notas do aluno
        cursor.execute("""
            SELECT 
                d.nome as disciplina,
                n.nota,
                n.bimestre
            FROM notas n
            JOIN disciplinas d ON n.disciplina_id = d.id
            WHERE n.aluno_id = ?
            ORDER BY d.nome, n.bimestre
        """, (aluno_id,))
        notas = cursor.fetchall()

        # Busca frequência do aluno
        cursor.execute("""
            SELECT 
                d.nome as disciplina,
                f.data,
                f.presente
            FROM frequencia f
            JOIN disciplinas d ON f.disciplina_id = d.id
            WHERE f.aluno_id = ?
            ORDER BY d.nome, f.data
        """, (aluno_id,))
        frequencia = cursor.fetchall()

        # Busca parecer do aluno
        cursor.execute("""
            SELECT 
                p.texto,
                p.data,
                d.nome as disciplina
            FROM pareceres p
            JOIN disciplinas d ON p.disciplina_id = d.id
            WHERE p.aluno_id = ?
            ORDER BY p.data DESC
        """, (aluno_id,))
        pareceres = cursor.fetchall()

        return render_template(
            'professores/relatorio_aluno.html',
            aluno=aluno,
            notas=notas,
            frequencia=frequencia,
            pareceres=pareceres
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
            
        if current_user.tipo_usuario_id != TIPO_USUARIO_PROFESSOR:
            return jsonify({'error': 'Usuário não é professor'}), 403

        db = get_db()
        cursor = db.cursor()

        cursor.execute("""
            SELECT t.escola_id, t.tipo_ensino_id, t.serie_id
            FROM turmas t
            JOIN professor_turma_escola pte ON t.id = pte.turma_id
            WHERE pte.professor_id = ? AND t.id = ?
            LIMIT 1
        """, (current_user.id, turma_id))
        turma_prof = cursor.fetchone()
        
        if not turma_prof:
            return jsonify({'error': 'Acesso não autorizado'}), 403

        cursor.execute("""
            SELECT DISTINCT u.id, u.nome, u.email
            FROM usuarios u
            WHERE u.escola_id = ?
            AND u.tipo_ensino_id = ?
            AND u.serie_id = ?
            AND u.turma_id = ?
            AND u.tipo_usuario_id = ?
            AND u.nome IS NOT NULL
            AND u.nome != ''
            GROUP BY u.nome
            ORDER BY u.nome
        """, (turma_prof[0], turma_prof[1], turma_prof[2], turma_id, TIPO_USUARIO_ALUNO))
        alunos = cursor.fetchall()
        
        return jsonify([{
            'id': aluno[0],
            'nome': aluno[1],
            'email': aluno[2]
        } for aluno in alunos])
    except Exception as e:
        print(f"Erro: {str(e)}")
        return jsonify({'error': str(e)}), 500

@professores_bp.route('/relatorio_aluno/<int:aluno_id>')
@login_required
def relatorio_aluno_novo(aluno_id):
    if current_user.tipo_usuario_id != 3:  # Verifica se é professor
        flash('Acesso não autorizado.', 'danger')
        return redirect(url_for('home'))
        
    db = get_db()
    cursor = db.cursor()
    
    # Buscar informações do aluno
    cursor.execute("""
        SELECT u.id, u.nome, u.email, t.id as turma_id, 
               s.nome as serie, t.turma, e.nome_da_escola as escola
        FROM usuarios u
        JOIN turmas t ON u.turma_id = t.id
        JOIN series s ON t.serie_id = s.id
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
    
    # Gerar gráficos como imagens
    import matplotlib.pyplot as plt
    import io
    import base64
    from datetime import datetime
    
    # Configuração do estilo dos gráficos
    plt.style.use('bmh')  # Usando um estilo padrão do matplotlib
    
    # Configurações comuns para os gráficos
    plt.rcParams['figure.facecolor'] = 'white'
    plt.rcParams['axes.facecolor'] = 'white'
    plt.rcParams['axes.grid'] = True
    plt.rcParams['grid.alpha'] = 0.3
    plt.rcParams['axes.labelcolor'] = '#333333'
    plt.rcParams['xtick.color'] = '#333333'
    plt.rcParams['ytick.color'] = '#333333'
    
    # Gráfico de Desempenho por Disciplina
    plt.figure(figsize=(10, 6))
    bars = plt.bar(disciplinas, medias_disciplinas, color='#0d6efd', alpha=0.7)
    plt.title('Desempenho por Disciplina', pad=20, color='#333333', fontsize=14)
    plt.xlabel('Disciplinas', color='#333333')
    plt.ylabel('Média (%)', color='#333333')
    plt.xticks(rotation=45, ha='right', color='#333333')
    plt.ylim(0, 100)
    
    # Adicionar valores sobre as barras
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}%',
                ha='center', va='bottom', color='#333333')
    
    # Salvar gráfico como base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight', dpi=300, facecolor='white')
    buffer.seek(0)
    grafico_desempenho = base64.b64encode(buffer.getvalue()).decode()
    plt.close()
    
    # Gráfico de Evolução
    plt.figure(figsize=(10, 6))
    plt.plot(datas_simulados, notas_simulados, marker='o', color='#0d6efd', linewidth=2, markersize=8)
    plt.title('Evolução do Desempenho', pad=20, color='#333333', fontsize=14)
    plt.xlabel('Data do Simulado', color='#333333')
    plt.ylabel('Desempenho (%)', color='#333333')
    plt.xticks(rotation=45, ha='right', color='#333333')
    plt.ylim(0, 100)
    plt.grid(True, linestyle='--', alpha=0.3)
    
    # Adicionar valores sobre os pontos
    for i, txt in enumerate(notas_simulados):
        plt.annotate(f'{txt:.1f}%', 
                    (datas_simulados[i], notas_simulados[i]),
                    textcoords="offset points",
                    xytext=(0,10),
                    ha='center',
                    color='#333333')
    
    # Salvar gráfico como base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight', dpi=300, facecolor='white')
    buffer.seek(0)
    grafico_evolucao = base64.b64encode(buffer.getvalue()).decode()
    plt.close()
    
    return render_template('professores/relatorio_aluno.html',
                         aluno={'id': aluno_info[0], 'nome': aluno_info[1], 'email': aluno_info[2]},
                         turma={'serie': aluno_info[4], 'turma': aluno_info[5], 'escola': aluno_info[6]},
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
    if current_user.tipo_usuario_id != 3:  # Verifica se é professor
        flash('Acesso não autorizado.', 'danger')
        return redirect(url_for('home'))
        
    db = get_db()
    cursor = db.cursor()
    
    # Buscar informações do aluno
    cursor.execute("""
        SELECT u.id, u.nome, u.email, t.id as turma_id, 
               s.nome as serie, t.turma, e.nome_da_escola as escola
        FROM usuarios u
        JOIN turmas t ON u.turma_id = t.id
        JOIN series s ON t.serie_id = s.id
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
    
    # Gerar gráficos como imagens
    import matplotlib.pyplot as plt
    import io
    import base64
    from datetime import datetime
    
    # Configuração do estilo dos gráficos
    plt.style.use('bmh')  # Usando um estilo padrão do matplotlib
    
    # Configurações comuns para os gráficos
    plt.rcParams['figure.facecolor'] = 'white'
    plt.rcParams['axes.facecolor'] = 'white'
    plt.rcParams['axes.grid'] = True
    plt.rcParams['grid.alpha'] = 0.3
    plt.rcParams['axes.labelcolor'] = '#333333'
    plt.rcParams['xtick.color'] = '#333333'
    plt.rcParams['ytick.color'] = '#333333'
    
    # Gráfico de Desempenho por Disciplina
    plt.figure(figsize=(10, 6))
    bars = plt.bar(disciplinas, medias_disciplinas, color='#0d6efd', alpha=0.7)
    plt.title('Desempenho por Disciplina', pad=20, color='#333333', fontsize=14)
    plt.xlabel('Disciplinas', color='#333333')
    plt.ylabel('Média (%)', color='#333333')
    plt.xticks(rotation=45, ha='right', color='#333333')
    plt.ylim(0, 100)
    
    # Adicionar valores sobre as barras
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}%',
                ha='center', va='bottom', color='#333333')
    
    # Salvar gráfico como base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight', dpi=300, facecolor='white')
    buffer.seek(0)
    grafico_desempenho = base64.b64encode(buffer.getvalue()).decode()
    plt.close()
    
    # Gráfico de Evolução
    plt.figure(figsize=(10, 6))
    plt.plot(datas_simulados, notas_simulados, marker='o', color='#0d6efd', linewidth=2, markersize=8)
    plt.title('Evolução do Desempenho', pad=20, color='#333333', fontsize=14)
    plt.xlabel('Data do Simulado', color='#333333')
    plt.ylabel('Desempenho (%)', color='#333333')
    plt.xticks(rotation=45, ha='right', color='#333333')
    plt.ylim(0, 100)
    plt.grid(True, linestyle='--', alpha=0.3)
    
    # Adicionar valores sobre os pontos
    for i, txt in enumerate(notas_simulados):
        plt.annotate(f'{txt:.1f}%', 
                    (datas_simulados[i], notas_simulados[i]),
                    textcoords="offset points",
                    xytext=(0,10),
                    ha='center',
                    color='#333333')
    
    # Salvar gráfico como base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight', dpi=300, facecolor='white')
    buffer.seek(0)
    grafico_evolucao = base64.b64encode(buffer.getvalue()).decode()
    plt.close()
    
    # Renderizar o template com os dados
    html = render_template('professores/relatorio_aluno_pdf.html',
                         aluno={'id': aluno_info[0], 'nome': aluno_info[1], 'email': aluno_info[2]},
                         turma={'serie': aluno_info[4], 'turma': aluno_info[5], 'escola': aluno_info[6]},
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
    response.headers['Content-Disposition'] = f'inline; filename=relatorio_{aluno_info[1].lower().replace(" ", "_")}.pdf'
    
    return response

@professores_bp.route('/api/questoes/<int:disciplina_id>')
@login_required
def api_questoes_por_disciplina(disciplina_id):
    if current_user.tipo_usuario_id != 3:  # Verifica se é professor
        return jsonify({'error': 'Acesso não autorizado'}), 403
        
    db = get_db()
    cursor = db.cursor()
    
    # Verificar se a disciplina existe
    cursor.execute("SELECT id FROM disciplinas WHERE id = ?", (disciplina_id,))
    if not cursor.fetchone():
        return jsonify({'error': 'Disciplina não encontrada'}), 404
    
    # Buscar questões da disciplina
    cursor.execute("""
        SELECT q.id, q.enunciado, q.nivel
        FROM banco_questoes q
        WHERE q.disciplina_id = ?
        ORDER BY q.id DESC
    """, (disciplina_id,))
    
    questoes = []
    for q in cursor.fetchall():
        questoes.append({
            'id': q[0],
            'enunciado': q[1],
            'nivel': q[2]
        })
    
    return jsonify({'questoes': questoes})
