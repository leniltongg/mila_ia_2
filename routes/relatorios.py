from flask import Blueprint, render_template, request, jsonify, send_file
from flask_login import login_required, current_user
from extensions import db
from models import *
import pandas as pd
from datetime import datetime
from utils import get_nome_mes  # se você tiver funções utilitárias
from sqlalchemy import func, and_, extract, case, desc, cast
from sqlalchemy import text, exists, or_, literal, literal_column


relatorios_bp = Blueprint('relatorios', __name__)

@relatorios_bp.route('/relatorios_dashboard', methods=['GET'])
@login_required
def relatorios_dashboard():
    if current_user.tipo_usuario_id not in [5, 6]:  # Apenas para Secretaria de Educação
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))

    codigo_ibge = current_user.codigo_ibge

    desempenho_geral = db.session.query(
        func.avg(DesempenhoSimulado.desempenho).label('desempenho_geral')
    ).join(
        Usuarios, DesempenhoSimulado.aluno_id == Usuarios.id
    ).filter(
        Usuarios.codigo_ibge == codigo_ibge,
        Usuarios.tipo_usuario_id == 4
    ).scalar() or 0

    # Melhor escola
    melhor_escola = db.session.query(
        Escolas.nome_da_escola,
        func.avg(DesempenhoSimulado.desempenho).label('media_escola')
    ).join(
        Usuarios, DesempenhoSimulado.aluno_id == Usuarios.id
    ).join(
        Escolas, Usuarios.escola_id == Escolas.id
    ).filter(
        Usuarios.codigo_ibge == codigo_ibge,
        Usuarios.tipo_usuario_id == 4,
        Escolas.codigo_ibge == codigo_ibge
    ).group_by(
        Escolas.id, Escolas.nome_da_escola
    ).order_by(
        desc('media_escola')
    ).first() or ("Nenhuma escola", 0)

    # Desempenho mensal
    desempenho_mensal = db.session.query(
        literal_column('MONTH(desempenho_simulado.data_resposta)').label('mes'),
        func.avg(DesempenhoSimulado.desempenho).label('media_desempenho')
    ).join(
        Usuarios, DesempenhoSimulado.aluno_id == Usuarios.id
    ).filter(
        Usuarios.codigo_ibge == codigo_ibge,
        Usuarios.tipo_usuario_id == 4
    ).group_by(
        literal_column('mes')
    ).order_by(
        'mes'
    ).all()

    # Converter números dos meses para nomes
    desempenho_mensal = [(get_nome_mes(int(mes)), media) for mes, media in desempenho_mensal]

    # Ranking de escolas
    ranking_escolas = db.session.query(
        Escolas.nome_da_escola,
        func.avg(DesempenhoSimulado.desempenho).label('media_escola')
    ).join(
        Usuarios, DesempenhoSimulado.aluno_id == Usuarios.id
    ).join(
        Escolas, Usuarios.escola_id == Escolas.id
    ).filter(
        Usuarios.codigo_ibge == codigo_ibge,
        Usuarios.tipo_usuario_id == 4,
        Escolas.codigo_ibge == codigo_ibge
    ).group_by(
        Escolas.id, Escolas.nome_da_escola
    ).order_by(
        desc('media_escola')
    ).all()

    # Ranking dos 5 melhores alunos por ano escolar
    ranking_alunos = db.session.query(
        Ano_escolar.nome.label('ano_escolar'),
        Usuarios.nome.label('aluno'),
        func.avg(DesempenhoSimulado.desempenho).label('media_aluno')
    ).join(
        Usuarios, DesempenhoSimulado.aluno_id == Usuarios.id
    ).join(
        Ano_escolar, Usuarios.ano_escolar_id == Ano_escolar.id
    ).filter(
        Usuarios.codigo_ibge == codigo_ibge,
        Usuarios.tipo_usuario_id == 4
    ).group_by(
        Ano_escolar.id, Ano_escolar.nome, Usuarios.id, Usuarios.nome
    ).order_by(
        Ano_escolar.id,
        desc('media_aluno')
    ).limit(5).all()

    # Contagem de alunos por faixa de desempenho
    faixas = db.session.query(
        func.sum(case([(DesempenhoSimulado.desempenho <= 20, 1)], else_=0)).label('faixa_0_20'),
        func.sum(case([(and_(DesempenhoSimulado.desempenho > 20, DesempenhoSimulado.desempenho <= 40), 1)], else_=0)).label('faixa_21_40'),
        func.sum(case([(and_(DesempenhoSimulado.desempenho > 40, DesempenhoSimulado.desempenho <= 60), 1)], else_=0)).label('faixa_41_60'),
        func.sum(case([(and_(DesempenhoSimulado.desempenho > 60, DesempenhoSimulado.desempenho <= 80), 1)], else_=0)).label('faixa_61_80'),
        func.sum(case([(and_(DesempenhoSimulado.desempenho > 80, DesempenhoSimulado.desempenho <= 100), 1)], else_=0)).label('faixa_81_100')
    ).join(
        Usuarios, DesempenhoSimulado.aluno_id == Usuarios.id
    ).filter(
        Usuarios.codigo_ibge == codigo_ibge,
        Usuarios.tipo_usuario_id == 4
    ).first()

    # Garantir que todas as variáveis tenham valores padrão
    faixa_0_20 = faixas[0] if faixas and faixas[0] is not None else 0
    faixa_21_40 = faixas[1] if faixas and faixas[1] is not None else 0
    faixa_41_60 = faixas[2] if faixas and faixas[2] is not None else 0
    faixa_61_80 = faixas[3] if faixas and faixas[3] is not None else 0
    faixa_81_100 = faixas[4] if faixas and faixas[4] is not None else 0

    return render_template(
        'secretaria_educacao/relatorios_dashboard.html',
        desempenho_geral=desempenho_geral,
        melhor_escola=melhor_escola,
        desempenho_mensal=desempenho_mensal,
        ranking_escolas=ranking_escolas,
        ranking_alunos=ranking_alunos,
        faixa_0_20=faixa_0_20,
        faixa_21_40=faixa_21_40,
        faixa_41_60=faixa_41_60,
        faixa_61_80=faixa_61_80,
        faixa_81_100=faixa_81_100
    )

@relatorios_bp.route('/relatorios_gerenciais')
@login_required
def relatorios_gerenciais():
    """Página de relatórios gerenciais."""
    if current_user.tipo_usuario_id not in [5, 6]:  # Verifica se é secretaria
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))
    
    return render_template('secretaria_educacao/relatorios_gerenciais.html')

@relatorios_bp.route('/relatorio_rede_municipal')
@login_required
def relatorio_rede_municipal():
    mes = request.args.get('mes', type=int)
    
    # Condição de data para filtrar por mês
    data_condition = []
    if mes:
        data_condition = [extract('month', DesempenhoSimulado.data_resposta) == mes]
    
    # Consulta escolas
    escolas_query = db.session.query(
        Escolas.id,
        Escolas.nome_da_escola.label('nome'),  # Mudado para nome_da_escola
        func.count(func.distinct(Usuarios.id)).label('total_alunos'),
        func.count(func.distinct(DesempenhoSimulado.aluno_id)).label('alunos_ativos'),
        func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media')
    ).outerjoin(
        Usuarios, and_(
            Usuarios.escola_id == Escolas.id,  # Mudado para Escolas
            Usuarios.tipo_usuario_id == 4  # Alunos
        )
    ).outerjoin(
        DesempenhoSimulado, and_(
            DesempenhoSimulado.aluno_id == Usuarios.id,
            *data_condition
        )
    ).group_by(
        Escolas.id, Escolas.nome_da_escola  # Mudado para nome_da_escola
    ).order_by(
        Escolas.nome_da_escola  # Mudado para nome_da_escola
    ).all()

    # Consulta anos escolares
    anos_query = db.session.query(
        Ano_escolar.id,
        Ano_escolar.nome.label('Ano_escolar_nome'),
        func.count(func.distinct(Usuarios.id)).label('total_alunos'),
        func.count(func.distinct(DesempenhoSimulado.aluno_id)).label('alunos_ativos'),
        func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media')
    ).outerjoin(
        Usuarios, and_(
            Usuarios.ano_escolar_id == Ano_escolar.id,
            Usuarios.tipo_usuario_id == 4
        )
    ).outerjoin(
        DesempenhoSimulado, and_(
            DesempenhoSimulado.aluno_id == Usuarios.id,
            *data_condition
        )
    ).group_by(
        Ano_escolar.id, Ano_escolar.nome
    ).order_by(
        Ano_escolar.id
    ).all()

    # Consulta disciplinas
    disciplinas_query = db.session.query(
        Disciplinas.id,
        Disciplinas.nome,
        func.count(func.distinct(DesempenhoSimulado.aluno_id)).label('alunos_ativos'),
        func.count(func.distinct(DesempenhoSimulado.simulado_id)).label('total_questoes'),
        func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media')
    ).outerjoin(
        SimuladosGerados, SimuladosGerados.disciplina_id == Disciplinas.id
    ).outerjoin(
        DesempenhoSimulado, and_(
            DesempenhoSimulado.simulado_id == SimuladosGerados.id,
            *data_condition
        )
    ).group_by(
        Disciplinas.id, Disciplinas.nome
    ).order_by(
        Disciplinas.nome
    ).all()

    # Dados para os gráficos
    escolas_nomes = [escola.nome for escola in escolas_query]
    escolas_medias = [float(escola.media) for escola in escolas_query]
    participacao_escolas = [float(escola.alunos_ativos / escola.total_alunos * 100) if escola.total_alunos > 0 else 0 for escola in escolas_query]
    
    anos_nomes = [ano.Ano_escolar_nome for ano in anos_query]
    anos_medias = [float(ano.media) for ano in anos_query]
    
    disciplinas_nomes = [disc.nome for disc in disciplinas_query]
    disciplinas_medias = [float(disc.media) for disc in disciplinas_query]

    # Debug dos dados
    print("Dados dos gráficos:")
    print("Escolas:", escolas_nomes, escolas_medias)
    print("Anos:", anos_nomes, anos_medias)
    print("Disciplinas:", disciplinas_nomes, disciplinas_medias)
    print("Participação:", participacao_escolas)

    # Calcular totais
    total_escolas = len(escolas_query)
    total_alunos = sum(escola.total_alunos for escola in escolas_query)
    total_simulados = db.session.query(func.count(DesempenhoSimulado.id)).filter(*data_condition).scalar() or 0
    media_geral = sum(escola.media * escola.alunos_ativos for escola in escolas_query) / sum(escola.alunos_ativos for escola in escolas_query) if sum(escola.alunos_ativos for escola in escolas_query) > 0 else 0

    return render_template('secretaria_educacao/relatorio_rede_municipal.html',
                         mes=mes,
                         escolas=escolas_query,
                         total_escolas=total_escolas,
                         total_alunos=total_alunos,
                         total_simulados=total_simulados,
                         media_geral=round(media_geral, 1),
                         escolas_nomes=escolas_nomes,
                         escolas_medias=escolas_medias,
                         participacao_escolas=participacao_escolas,
                         anos_nomes=anos_nomes,
                         anos_medias=anos_medias,
                         disciplinas_nomes=disciplinas_nomes,
                         disciplinas_medias=disciplinas_medias,
                         anos_query=anos_query)

@relatorios_bp.route('/relatorio_rede_municipal/export_pdf')
@login_required
def export_pdf_relatorio():
    """Exportar relatório em PDF."""
    if current_user.tipo_usuario_id not in [5, 6]:
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))
    
    codigo_ibge = current_user.codigo_ibge
    
    # Obter mês da query string
    mes = request.args.get('mes', type=int)
    ano = 2025  # Fixado em 2025
    
    from sqlalchemy import func, and_, extract, case
    
    # Construir a condição de data
    data_condition = [extract('year', DesempenhoSimulado.data_resposta) == ano]
    if mes:
        data_condition.append(extract('month', DesempenhoSimulado.data_resposta) == mes)
    
    # Buscar dados gerais
    total_escolas = db.session.query(
        func.count(Escolas.id)
    ).filter(
        Escolas.codigo_ibge == codigo_ibge
    ).scalar()

    total_alunos = db.session.query(
        func.count(Usuarios.id)
    ).filter(
        Usuarios.codigo_ibge == codigo_ibge,
        Usuarios.tipo_usuario_id == 4
    ).scalar()
    
    # Total de simulados com filtro de data
    total_simulados = db.session.query(
        func.count(func.distinct(DesempenhoSimulado.simulado_id))
    ).filter(
        DesempenhoSimulado.codigo_ibge == codigo_ibge,
        *data_condition
    ).scalar()
    
    # Buscar dados das escolas
    escolas_query = db.session.query(
        Escolas.id,
        Escolas.nome_da_escola.label('nome'),
        func.count(func.distinct(Usuarios.id)).label('total_alunos'),
        func.count(func.distinct(DesempenhoSimulado.aluno_id)).label('alunos_ativos'),
        func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media')
    ).outerjoin(
        Usuarios, and_(
            Usuarios.escola_id == Escolas.id,
            Usuarios.tipo_usuario_id == 4,
            Usuarios.codigo_ibge == codigo_ibge
        )
    ).outerjoin(
        DesempenhoSimulado, and_(
            DesempenhoSimulado.aluno_id == Usuarios.id,
            DesempenhoSimulado.codigo_ibge == codigo_ibge,
            *data_condition
        )
    ).filter(
        Escolas.codigo_ibge == codigo_ibge
    ).group_by(
        Escolas.id, Escolas.nome_da_escola
    ).order_by(
        db.desc('media')
    )
    
    escolas = [dict(zip(['id', 'nome', 'total_alunos', 'alunos_ativos', 'media'], escola))
               for escola in escolas_query.all()]
    
    # Calcular média geral ponderada
    total_alunos_ativos = sum(escola['alunos_ativos'] for escola in escolas)
    soma_medias_ponderadas = sum(escola['media'] * escola['alunos_ativos'] for escola in escolas)
    media_geral = soma_medias_ponderadas / total_alunos_ativos if total_alunos_ativos > 0 else 0.0
    
    # Buscar desempenho por disciplina
    disciplinas_query = db.session.query(
        Disciplinas.id,
        Disciplinas.nome.label('disciplina'),
        func.count(func.distinct(DesempenhoSimulado.aluno_id)).label('total_alunos'),
        func.count(func.distinct(DesempenhoSimulado.simulado_id)).label('total_questoes'),
        func.round(func.avg(DesempenhoSimulado.desempenho), 1).label('media_acertos')
    ).outerjoin(
        SimuladosGerados, SimuladosGerados.disciplina_id == Disciplinas.id
    ).outerjoin(
        DesempenhoSimulado, and_(
            DesempenhoSimulado.simulado_id == SimuladosGerados.id,
            DesempenhoSimulado.codigo_ibge == codigo_ibge,
            *data_condition
        )
    ).group_by(
        Disciplinas.id, Disciplinas.nome
    ).having(
        func.count(func.distinct(DesempenhoSimulado.aluno_id)) > 0
    ).order_by(
        db.desc('media_acertos')
    )
    
    disciplinas = [dict(zip(['id', 'disciplina', 'total_alunos', 'total_questoes', 'media_acertos'], disc))
                  for disc in disciplinas_query.all()]
    
    # Preparar dados para o gráfico de disciplinas
    disciplinas_nomes = [d['disciplina'] for d in disciplinas]
    disciplinas_medias = [float(d['media_acertos']) for d in disciplinas]
    
    # Renderizar o template HTML para PDF
    html_content = render_template(
        'secretaria_educacao/relatorio_rede_municipal_pdf.html',  # Template específico para PDF
        escolas=escolas,
        total_escolas=total_escolas,
        total_alunos=total_alunos,
        total_simulados=total_simulados,
        media_geral=f"{media_geral:.1f}",
        disciplinas=disciplinas,
        disciplinas_nomes=disciplinas_nomes,
        disciplinas_medias=disciplinas_medias,
        escolas_nomes=[e['nome'] for e in escolas],
        escolas_medias=[float(e['media']) for e in escolas],
        mes=mes,
        ano=ano
    )
    
    # Criar PDF usando WeasyPrint
    pdf = HTML(string=html_content).write_pdf()
    
    # Retornar o PDF como download
    return send_file(
        BytesIO(pdf),
        download_name='relatorio_rede_municipal.pdf',
        mimetype='application/pdf'
    )

@relatorios_bp.route('/relatorio_rede_municipal/export_excel')
@login_required
def export_excel_relatorio():
    """Exportar relatório em Excel."""
    if current_user.tipo_usuario_id not in [5, 6]:
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))
    
    codigo_ibge = current_user.codigo_ibge
    
    # Obter mês da query string
    mes = request.args.get('mes', type=int)
    ano = 2025  # Fixado em 2025
    
    from sqlalchemy import func, and_, extract, case, literal_column
    
    # Construir a condição de data
    data_condition = [extract('year', DesempenhoSimulado.data_resposta) == ano]
    if mes:
        data_condition.append(extract('month', DesempenhoSimulado.data_resposta) == mes)
    
    # Criar um Excel writer
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='openpyxl')
    
    # Aba Visão Geral - Dados das escolas
    escolas_query = db.session.query(
        Escolas.id,
        Escolas.nome_da_escola.label('nome'),
        func.count(func.distinct(Usuarios.id)).label('total_alunos'),
        func.count(func.distinct(DesempenhoSimulado.aluno_id)).label('alunos_ativos'),
        func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media')
    ).outerjoin(
        Usuarios, and_(
            Usuarios.escola_id == Escolas.id,
            Usuarios.tipo_usuario_id == 4,
            Usuarios.codigo_ibge == codigo_ibge
        )
    ).outerjoin(
        DesempenhoSimulado, and_(
            DesempenhoSimulado.aluno_id == Usuarios.id,
            *data_condition
        )
    ).filter(
        Escolas.codigo_ibge == codigo_ibge
    ).group_by(
        Escolas.id, Escolas.nome_da_escola
    ).order_by(
        db.desc('media')
    ).all()

    escolas = [dict(zip(['id', 'nome', 'total_alunos', 'alunos_ativos', 'media'], escola))
               for escola in escolas_query.all()]
    
    df_escolas = pd.DataFrame(escolas)
    if not df_escolas.empty:
        df_escolas = df_escolas.rename(columns={
            'nome': 'Escola',
            'total_alunos': 'Total de Alunos',
            'alunos_ativos': 'Alunos Ativos',
            'media': 'Média (%)'
        })
        df_escolas['Média (%)'] = df_escolas['Média (%)'].round(1)
        df_escolas.drop('id', axis=1, inplace=True)
    df_escolas.to_excel(writer, sheet_name='Visão Geral', index=False)
    
    # Aba Desempenho por Disciplina
    disciplinas_query = db.session.query(
        Disciplinas.nome.label('disciplina'),
        func.count(func.distinct(DesempenhoSimulado.aluno_id)).label('total_alunos'),
        func.count(func.distinct(DesempenhoSimulado.simulado_id)).label('total_questoes'),
        func.round(func.avg(DesempenhoSimulado.desempenho), 1).label('media_acertos')
    ).outerjoin(
        SimuladosGerados, SimuladosGerados.disciplina_id == Disciplinas.id
    ).outerjoin(
        DesempenhoSimulado, and_(
            DesempenhoSimulado.simulado_id == SimuladosGerados.id,
            DesempenhoSimulado.codigo_ibge == codigo_ibge,
            *data_condition
        )
    ).group_by(
        Disciplinas.id, Disciplinas.nome
    ).having(
        func.count(func.distinct(DesempenhoSimulado.aluno_id)) > 0
    ).order_by(
        db.desc('media_acertos')
    )
    
    disciplinas = [dict(zip(['disciplina', 'total_alunos', 'total_questoes', 'media_acertos'], disc))
                  for disc in disciplinas_query.all()]
    
    df_disciplinas = pd.DataFrame(disciplinas)
    if not df_disciplinas.empty:
        df_disciplinas = df_disciplinas.rename(columns={
            'disciplina': 'Disciplina',
            'total_alunos': 'Total de Alunos',
            'total_questoes': 'Total de Questões',
            'media_acertos': 'Média de Acertos (%)'
        })
    df_disciplinas.to_excel(writer, sheet_name='Desempenho por Disciplina', index=False)

    # Buscar todas as séries
    Ano_escolar = db.session.query(Ano_escolar.id, Ano_escolar.nome).order_by(Ano_escolar.id).all()

    # Para cada série, criar uma aba com desempenho por escola
    for Ano_escolar in Ano_escolar:
        ano_escolar_id = Ano_escolar[0]
        Ano_escolar_nome = Ano_escolar[1]
        
        # Query para dados da série específica
        anos_escolares_query = db.session.query(
            Escolas.id.label('escola_id'),
            Escolas.nome_da_escola,
            func.count(func.distinct(Usuarios.id)).label('total_alunos'),
            func.count(func.distinct(DesempenhoSimulado.aluno_id)).label('alunos_responderam'),
            func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media_geral'),
            Disciplinas.nome.label('disciplina'),
            func.coalesce(
                func.avg(case((
                    and_(
                        DesempenhoSimulado.tipo_usuario_id == 5,
                        SimuladosGerados.disciplina_id == Disciplinas.id
                    ), DesempenhoSimulado.desempenho
                ))), 0.0
            ).label('media_disciplina')
        ).outerjoin(
            Usuarios, and_(
                Usuarios.escola_id == Escolas.id,
                Usuarios.tipo_usuario_id == 4,
                Usuarios.ano_escolar_id == ano_escolar_id,
                Usuarios.codigo_ibge == codigo_ibge
            )
        ).outerjoin(
            DesempenhoSimulado, and_(
            DesempenhoSimulado.aluno_id == Usuarios.id,
            *data_condition
        )
        ).outerjoin(
            SimuladosGerados, SimuladosGerados.id == DesempenhoSimulado.simulado_id
        ).outerjoin(
            Disciplinas
        ).filter(
            Escolas.codigo_ibge == codigo_ibge
        ).group_by(
            Escolas.id, Escolas.nome_da_escola, Disciplinas.id, Disciplinas.nome
        ).having(
            func.count(func.distinct(Usuarios.id)) > 0
        ).order_by(
            db.desc('media_geral')
        )
        
        rows = anos_escolares_query.all()
        
        if rows:
            # Converter para DataFrame
            df_Ano_escolar = pd.DataFrame([
                dict(zip(
                    ['escola_id', 'nome_da_escola', 'total_alunos', 'alunos_responderam',
                     'media_geral', 'disciplina', 'media_disciplina'],
                    row
                )) for row in rows
            ])
            
            # Renomear colunas
            df_Ano_escolar = df_Ano_escolar.rename(columns={
                'nome_da_escola': 'Escola',
                'total_alunos': 'Total de Alunos',
                'alunos_responderam': 'Alunos Ativos',
                'media_geral': 'Média Geral (%)'
            })
            
            # Arredondar médias
            df_Ano_escolar['Média Geral (%)'] = df_Ano_escolar['Média Geral (%)'].round(1)
            
            # Pivotear para ter disciplinas como colunas
            if 'disciplina' in df_Ano_escolar.columns:
                df_pivot = df_Ano_escolar.pivot_table(
                    index=['escola_id', 'Escola', 'Total de Alunos', 'Alunos Ativos', 'Média Geral (%)'],
                    columns='disciplina',
                    values='media_disciplina',
                    aggfunc='first'
                ).reset_index()
                
                # Arredondar médias das disciplinas
                for col in df_pivot.columns:
                    if col not in ['escola_id', 'Escola', 'Total de Alunos', 'Alunos Ativos', 'Média Geral (%)']:
                        df_pivot[col] = df_pivot[col].round(1)
                        df_pivot = df_pivot.rename(columns={col: f'{col} (%)'})
                
                # Remover coluna escola_id
                df_pivot.drop('escola_id', axis=1, inplace=True)
                
                # Salvar na planilha
                df_pivot.to_excel(writer, sheet_name=Ano_escolar_nome, index=False)
            else:
                # Se não houver dados de disciplinas, salvar apenas dados gerais
                df_Ano_escolar.drop(['escola_id', 'disciplina', 'media_disciplina'], axis=1, errors='ignore', inplace=True)
                df_Ano_escolar.to_excel(writer, sheet_name=Ano_escolar_nome, index=False)
    
    writer.close()
    output.seek(0)
    
    return send_file(
        output,
        download_name='relatorio_rede_municipal.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

def get_relatorio_data():
    codigo_ibge = current_user.codigo_ibge
    
    # Obter mês da query string
    mes = request.args.get('mes', type=int)
    ano = 2025  # Fixado em 2025
    
    from sqlalchemy import func, and_, extract, case
    
    # Construir a condição de data
    data_condition = [extract('year', DesempenhoSimulado.data_resposta) == ano]
    if mes:
        data_condition.append(extract('month', DesempenhoSimulado.data_resposta) == mes)
    
    # Buscar dados gerais
    total_escolas = db.session.query(
        func.count(Escolas.id)
    ).filter(
        Escolas.codigo_ibge == codigo_ibge
    ).scalar()

    total_alunos = db.session.query(
        func.count(Usuarios.id)
    ).filter(
        Usuarios.codigo_ibge == codigo_ibge,
        Usuarios.tipo_usuario_id == 4
    ).scalar()
    
    # Total de simulados com filtro de data
    total_simulados = db.session.query(
        func.count(func.distinct(DesempenhoSimulado.simulado_id))
    ).filter(
        DesempenhoSimulado.codigo_ibge == codigo_ibge,
        *data_condition
    ).scalar()
    
    # Buscar dados das escolas
    escolas_query = db.session.query(
        Escolas.id,
        Escolas.nome_da_escola.label('nome'),
        func.count(func.distinct(Usuarios.id)).label('total_alunos'),
        func.count(func.distinct(DesempenhoSimulado.aluno_id)).label('alunos_ativos'),
        func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media')
    ).outerjoin(
        Usuarios, and_(
            Usuarios.escola_id == Escolas.id,
            Usuarios.tipo_usuario_id == 4,
            Usuarios.codigo_ibge == codigo_ibge
        )
    ).outerjoin(
        DesempenhoSimulado, and_(
            DesempenhoSimulado.aluno_id == Usuarios.id,
            DesempenhoSimulado.codigo_ibge == codigo_ibge,
            *data_condition
        )
    ).filter(
        Escolas.codigo_ibge == codigo_ibge
    ).group_by(
        Escolas.id, Escolas.nome_da_escola
    ).order_by(
        db.desc('media')
    )
    
    escolas = [dict(zip(['id', 'nome', 'total_alunos', 'alunos_ativos', 'media'], escola))
               for escola in escolas_query.all()]
    
    # Calcular média geral ponderada
    total_alunos_ativos = sum(escola['alunos_ativos'] for escola in escolas)
    soma_medias_ponderadas = sum(escola['media'] * escola['alunos_ativos'] for escola in escolas)
    media_geral = soma_medias_ponderadas / total_alunos_ativos if total_alunos_ativos > 0 else 0.0
    
    # Buscar desempenho por disciplina
    disciplinas_query = db.session.query(
        Disciplinas.id,
        Disciplinas.nome.label('disciplina'),
        func.count(func.distinct(DesempenhoSimulado.aluno_id)).label('total_alunos'),
        func.count(func.distinct(DesempenhoSimulado.simulado_id)).label('total_questoes'),
        func.round(func.avg(DesempenhoSimulado.desempenho), 1).label('media_acertos')
    ).outerjoin(
        SimuladosGerados, SimuladosGerados.disciplina_id == Disciplinas.id
    ).outerjoin(
        DesempenhoSimulado, and_(
            DesempenhoSimulado.simulado_id == SimuladosGerados.id,
            DesempenhoSimulado.codigo_ibge == codigo_ibge,
            *data_condition
        )
    ).group_by(
        Disciplinas.id, Disciplinas.nome
    ).having(
        func.count(func.distinct(DesempenhoSimulado.aluno_id)) > 0
    ).order_by(
        db.desc('media_acertos')
    )
    
    disciplinas = [dict(zip(['id', 'disciplina', 'total_alunos', 'total_questoes', 'media_acertos'], disc))
                  for disc in disciplinas_query.all()]
    
    # Preparar dados para o gráfico
    disciplinas_nomes = [d['disciplina'] for d in disciplinas]
    disciplinas_medias = [float(d['media_acertos']) for d in disciplinas]
    
    return {
        'codigo_ibge': codigo_ibge,
        'mes': mes,
        'ano': ano,
        'escolas': escolas,
        'total_escolas': total_escolas,
        'total_alunos': total_alunos,
        'total_simulados': total_simulados,
        'media_geral': media_geral,
        'disciplinas': disciplinas,
        'disciplinas_nomes': disciplinas_nomes,
        'disciplinas_medias': disciplinas_medias
    }

@relatorios_bp.route('/relatorio_escola')
@login_required
def relatorio_escola():
    """Página de relatório por escola."""
    if current_user.tipo_usuario_id not in [5, 6]:
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))
    
    codigo_ibge = current_user.codigo_ibge
    
    # Buscar todas as escolas do município
    escolas = db.session.query(
        Escolas.id, 
        Escolas.nome_da_escola.label('nome')
    ).filter(
        Escolas.codigo_ibge == codigo_ibge
    ).order_by(
        Escolas.nome_da_escola
    ).all()
    
    # Obter escola_id e mês da query string
    escola_id = request.args.get('escola_id', type=int)
    mes = request.args.get('mes', type=int)
    ano = 2025  # Fixado em 2025
    
    # Se uma escola foi selecionada, buscar seus dados
    if escola_id:
        from sqlalchemy import func, and_, extract, case
        
        # Construir a condição de data
        data_condition = [extract('year', DesempenhoSimulado.data_resposta) == ano]
        if mes:
            data_condition.append(extract('month', DesempenhoSimulado.data_resposta) == mes)
        
        # Buscar dados gerais da escola
        escola = db.session.query(
            Escolas.nome_da_escola.label('nome'),
            func.count(func.distinct(Usuarios.id)).label('total_alunos'),
            func.count(func.distinct(DesempenhoSimulado.aluno_id)).label('alunos_ativos'),
            func.count(func.distinct(DesempenhoSimulado.simulado_id)).label('total_simulados'),
            func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media_geral')
        ).outerjoin(
            Usuarios, and_(
                Usuarios.escola_id == Escolas.id,
                Usuarios.tipo_usuario_id == 4
            )
        ).outerjoin(
            DesempenhoSimulado, and_(
                DesempenhoSimulado.aluno_id == Usuarios.id,
                *data_condition
            )
        ).filter(
            Escolas.id == escola_id
        ).group_by(
            Escolas.id, Escolas.nome_da_escola
        ).first()
        
        # Buscar dados por série
        anos_escolares_query = db.session.query(
            Ano_escolar.id,
            Ano_escolar.nome.label('Ano_escolar_nome'),
            func.count(func.distinct(Usuarios.id)).label('total_alunos'),
            func.count(func.distinct(DesempenhoSimulado.aluno_id)).label('alunos_ativos'),
            func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media')
        ).outerjoin(
            Usuarios, and_(
                Usuarios.ano_escolar_id == Ano_escolar.id,
                Usuarios.tipo_usuario_id == 4,
                Usuarios.escola_id == escola_id
            )
        ).outerjoin(
            DesempenhoSimulado, and_(
                DesempenhoSimulado.aluno_id == Usuarios.id,
                *data_condition
            )
        ).group_by(
            Ano_escolar.id, Ano_escolar.nome
        ).order_by(
            Ano_escolar.id
        ).all()
        
        anos_escolares = [dict(zip(['id', 'Ano_escolar_nome', 'total_alunos', 'alunos_ativos', 'media'], ano))
                       for ano in anos_escolares_query]
        
        # Buscar dados por disciplina
        disciplinas = db.session.query(
            Disciplinas.nome.label('disciplina'),
            func.count(func.distinct(DesempenhoSimulado.aluno_id)).label('total_alunos'),
            func.count(func.distinct(DesempenhoSimulado.simulado_id)).label('total_questoes'),
            func.round(func.avg(DesempenhoSimulado.desempenho), 1).label('media_acertos')
        ).outerjoin(
            SimuladosGerados, SimuladosGerados.disciplina_id == Disciplinas.id
        ).outerjoin(
            DesempenhoSimulado, and_(
                DesempenhoSimulado.simulado_id == SimuladosGerados.id,
                *data_condition
            )
        ).join(
            Usuarios, and_(
                Usuarios.id == DesempenhoSimulado.aluno_id,
                Usuarios.escola_id == escola_id
            )
        ).group_by(
            Disciplinas.id, Disciplinas.nome
        ).having(
            func.count(func.distinct(DesempenhoSimulado.aluno_id)) > 0
        ).order_by(
            db.desc('media_acertos')
        ).all()
        
        # Buscar dados por turma
        turmas = db.session.query(
            Turmas.id,
            (Ano_escolar.nome + ' ' + Turmas.turma).label('turma'),
            func.count(func.distinct(Usuarios.id)).label('total_alunos'),
            func.count(func.distinct(DesempenhoSimulado.aluno_id)).label('alunos_ativos'),
            func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media')
        ).join(
            Ano_escolar, Ano_escolar.id == Turmas.ano_escolar_id
        ).outerjoin(
            Usuarios, and_(
                Usuarios.turma_id == Turmas.id,
                Usuarios.tipo_usuario_id == 4,
                Usuarios.escola_id == escola_id
            )
        ).outerjoin(
            DesempenhoSimulado, and_(
                DesempenhoSimulado.aluno_id == Usuarios.id,
                *data_condition
            )
        ).group_by(
            Turmas.id, Turmas.turma, Ano_escolar.nome
        ).having(
            func.count(func.distinct(Usuarios.id)) > 0
        ).order_by(
            Ano_escolar.nome, Turmas.turma
        ).all()
        
        # Buscar dados dos alunos por turma com desempenho por disciplina
        alunos = db.session.query(
            Turmas.id.label('turma_id'),
            Usuarios.id.label('aluno_id'),
            Usuarios.nome.label('aluno_nome'),
            func.count(func.distinct(DesempenhoSimulado.simulado_id)).label('total_simulados'),
            func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media')
        ).join(
            Ano_escolar, Ano_escolar.id == Turmas.ano_escolar_id
        ).join(
            Usuarios, and_(
                Usuarios.turma_id == Turmas.id,
                Usuarios.tipo_usuario_id == 4,
                Usuarios.escola_id == escola_id
            )
        ).outerjoin(
            DesempenhoSimulado, and_(
                DesempenhoSimulado.aluno_id == Usuarios.id,
                *data_condition
            )
        ).group_by(
            Turmas.id,
            Usuarios.id,
            Usuarios.nome
        ).order_by(
            Usuarios.nome
        ).all()

        # Buscar médias por disciplina separadamente
        medias_disciplinas = db.session.query(
            Usuarios.id.label('aluno_id'),
            Disciplinas.id.label('disciplina_id'),
            func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media')
        ).join(
            DesempenhoSimulado, and_(
                DesempenhoSimulado.aluno_id == Usuarios.id,
                *data_condition
            )
        ).join(
            SimuladosGerados, SimuladosGerados.id == DesempenhoSimulado.simulado_id
        ).join(
            Disciplinas, Disciplinas.id == SimuladosGerados.disciplina_id
        ).filter(
            Usuarios.escola_id == escola_id
        ).group_by(
            Usuarios.id,
            Disciplinas.id
        ).all()

        # Criar dicionário com médias por disciplina
        medias_por_aluno = {}
        for media in medias_disciplinas:
            if media.aluno_id not in medias_por_aluno:
                medias_por_aluno[media.aluno_id] = {
                    'media_matematica': 0.0,
                    'media_portugues': 0.0,
                    'media_ciencias': 0.0,
                    'media_historia': 0.0,
                    'media_geografia': 0.0
                }
            
            if media.disciplina_id == 1:
                medias_por_aluno[media.aluno_id]['media_portugues'] = media.media
            elif media.disciplina_id == 2:
                medias_por_aluno[media.aluno_id]['media_matematica'] = media.media
            elif media.disciplina_id == 3:
                medias_por_aluno[media.aluno_id]['media_ciencias'] = media.media
            elif media.disciplina_id == 4:
                medias_por_aluno[media.aluno_id]['media_historia'] = media.media
            elif media.disciplina_id == 5:
                medias_por_aluno[media.aluno_id]['media_geografia'] = media.media

        # Adicionar médias por disciplina aos resultados dos alunos
        alunos_completos = []
        for aluno in alunos:
            medias = medias_por_aluno.get(aluno.aluno_id, {
                'media_matematica': 0.0,
                'media_portugues': 0.0,
                'media_ciencias': 0.0,
                'media_historia': 0.0,
                'media_geografia': 0.0
            })
            alunos_completos.append({
                'turma_id': aluno.turma_id,
                'aluno_id': aluno.aluno_id,
                'aluno_nome': aluno.aluno_nome,
                'total_simulados': aluno.total_simulados,
                'media': aluno.media,
                **medias
            })
        
        return render_template('secretaria_educacao/relatorio_escola.html',
                                 ano=ano,
                                 mes=mes,
                                 escolas=escolas,
                                 escola_id=escola_id,
                                 media_geral=round(escola.media_geral, 1),
                                 total_alunos=escola.total_alunos,
                                 alunos_ativos=escola.alunos_ativos,
                                 total_simulados=escola.total_simulados,
                                 Ano_escolar=anos_escolares,  # Mantive o mesmo nome da variável para manter compatibilidade
                                 disciplinas=disciplinas,
                                 turmas=turmas,
                                 alunos=alunos_completos)
    
    return render_template('secretaria_educacao/relatorio_escola.html',
                         ano=ano,
                         mes=mes,
                         escolas=escolas,
                         escola_id=None)
                         
@relatorios_bp.route('/relatorio_escola/export_pdf')
@login_required
def export_pdf_escola():
    """Exportar relatório da escola em PDF."""
    if current_user.tipo_usuario_id not in [3, 5]:  # Permitir acesso para professores (3) e secretaria (5)
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))
    
    # Obter escola_id e mês da query string
    escola_id = request.args.get('escola_id', type=int)
    mes = request.args.get('mes', type=int)
    ano = 2025  # Fixado em 2025
    
    if not escola_id:
        flash("Escola não especificada.", "danger")
        return redirect(url_for("secretaria_educacao.relatorio_escola"))
    
    # Construir a condição de data
    data_condition = [extract('year', DesempenhoSimulado.data_resposta) == ano]
    if mes:
        data_condition.append(extract('month', DesempenhoSimulado.data_resposta) == mes)
    
    # Buscar dados da escola
    escola = db.session.query(
        Escolas.nome_da_escola.label('nome'),
        func.count(func.distinct(Usuarios.id)).label('total_alunos'),
        func.count(func.distinct(DesempenhoSimulado.aluno_id)).label('alunos_ativos'),
        func.count(func.distinct(DesempenhoSimulado.simulado_id)).label('total_simulados'),
        func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media_geral')
    ).outerjoin(
        Usuarios, and_(
            Usuarios.escola_id == Escolas.id,
            Usuarios.tipo_usuario_id == 4
        )
    ).outerjoin(
        DesempenhoSimulado, and_(
            DesempenhoSimulado.aluno_id == Usuarios.id,
            *data_condition
        )
    ).filter(
        Escolas.id == escola_id
    ).group_by(
        Escolas.id, Escolas.nome_da_escola
    ).first()
    
    # Buscar dados por série
    anos_escolares_query = db.session.query(
        Ano_escolar.id,
        Ano_escolar.nome.label('Ano_escolar_nome'),
        func.count(func.distinct(Usuarios.id)).label('total_alunos'),
        func.count(func.distinct(DesempenhoSimulado.aluno_id)).label('alunos_ativos'),
        func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media')
    ).outerjoin(
        Usuarios, and_(
            Usuarios.ano_escolar_id == Ano_escolar.id,
            Usuarios.tipo_usuario_id == 4,
            Usuarios.escola_id == escola_id
        )
    ).outerjoin(
        DesempenhoSimulado, and_(
            DesempenhoSimulado.aluno_id == Usuarios.id,
            *data_condition
        )
    ).group_by(
        Ano_escolar.id, Ano_escolar.nome
    ).order_by(
        Ano_escolar.id
    ).all()
    
    anos_escolares = [dict(zip(['id', 'Ano_escolar_nome', 'total_alunos', 'alunos_ativos', 'media'], ano))
                   for ano in anos_escolares_query]
    
    # Buscar dados por disciplina
    disciplinas = db.session.query(
        Disciplinas.nome.label('disciplina'),
        func.count(func.distinct(DesempenhoSimulado.aluno_id)).label('total_alunos'),
        func.count(func.distinct(DesempenhoSimulado.simulado_id)).label('total_questoes'),
        func.round(func.avg(DesempenhoSimulado.desempenho), 1).label('media_acertos')
    ).outerjoin(
        SimuladosGerados, SimuladosGerados.disciplina_id == Disciplinas.id
    ).outerjoin(
        DesempenhoSimulado, and_(
            DesempenhoSimulado.simulado_id == SimuladosGerados.id,
            *data_condition
        )
    ).join(
        Usuarios, and_(
            Usuarios.id == DesempenhoSimulado.aluno_id,
            Usuarios.escola_id == escola_id
        )
    ).group_by(
        Disciplinas.id, Disciplinas.nome
    ).having(
        func.count(func.distinct(DesempenhoSimulado.aluno_id)) > 0
    ).order_by(
        db.desc('media_acertos')
    ).all()
    
    # Renderizar o template HTML
    html = render_template('secretaria_educacao/relatorio_escola_pdf.html',
                         ano=ano,
                         mes=MESES_NOMES.get(mes) if mes else None,
                         escola=escola,
                         media_geral=round(escola.media_geral, 1),
                         total_alunos=escola.total_alunos,
                         alunos_ativos=escola.alunos_ativos,
                         total_simulados=escola.total_simulados,
                         Ano_escolar=anos_escolares,
                         disciplinas=disciplinas)
    
    # Gerar o PDF
    pdf = HTML(string=html).write_pdf()
    
    return send_file(
        BytesIO(pdf),
        download_name=f'relatorio_escola_{escola_id}.pdf',
        mimetype='application/pdf'
    )

@relatorios_bp.route('/relatorio_escola/export_excel')
@login_required
def export_excel_escola():
    """Exportar relatório da escola em Excel."""
    if current_user.tipo_usuario_id not in [5, 6]:
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))
    
    # Obter escola_id e mês da query string
    escola_id = request.args.get('escola_id', type=int)
    mes = request.args.get('mes', type=int)
    ano = 2025  # Fixado em 2025
    
    if not escola_id:
        flash("Escola não especificada.", "danger")
        return redirect(url_for("secretaria_educacao.relatorio_escola"))
    
    # Construir a condição de data
    data_condition = [extract('year', DesempenhoSimulado.data_resposta) == ano]
    if mes:
        data_condition.append(extract('month', DesempenhoSimulado.data_resposta) == mes)
    
    # Criar um Excel writer
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='openpyxl')
    
    # Aba Visão Geral
    escola = db.session.query(
        Escolas.nome_da_escola.label('nome'),
        func.count(func.distinct(Usuarios.id)).label('total_alunos'),
        func.count(func.distinct(DesempenhoSimulado.aluno_id)).label('alunos_ativos'),
        func.count(func.distinct(DesempenhoSimulado.simulado_id)).label('total_simulados'),
        func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media_geral')
    ).outerjoin(
        Usuarios, and_(
            Usuarios.escola_id == Escolas.id,
            Usuarios.tipo_usuario_id == 4
        )
    ).outerjoin(
        DesempenhoSimulado, and_(
            DesempenhoSimulado.aluno_id == Usuarios.id,
            *data_condition
        )
    ).filter(
        Escolas.id == escola_id
    ).group_by(
        Escolas.id, Escolas.nome_da_escola
    ).first()
    
    df_geral = pd.DataFrame([{
        'Indicador': 'Média Geral',
        'Valor': f"{round(escola.media_geral, 1)}%"
    }, {
        'Indicador': 'Total de Alunos',
        'Valor': str(escola.total_alunos)
    }, {
        'Indicador': 'Alunos Ativos',
        'Valor': str(escola.alunos_ativos)
    }, {
        'Indicador': 'Simulados Realizados',
        'Valor': str(escola.total_simulados)
    }])
    df_geral.to_excel(writer, sheet_name='Visão Geral', index=False)
    
    # Aba Desempenho por Ano Escolar
    anos_escolares_query = db.session.query(
        Ano_escolar.nome.label('Ano_escolar_nome'),
        func.count(func.distinct(Usuarios.id)).label('total_alunos'),
        func.count(func.distinct(DesempenhoSimulado.aluno_id)).label('alunos_ativos'),
        func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media')
    ).outerjoin(
        Usuarios, and_(
            Usuarios.ano_escolar_id == Ano_escolar.id,
            Usuarios.tipo_usuario_id == 4,
            Usuarios.escola_id == escola_id
        )
    ).outerjoin(
        DesempenhoSimulado, and_(
            DesempenhoSimulado.aluno_id == Usuarios.id,
            *data_condition
        )
    ).group_by(
        Ano_escolar.id, Ano_escolar.nome
    ).order_by(
        Ano_escolar.id
    ).all()
    
    df_anos_escolares = pd.DataFrame([{
        'Ano Escolar': s.Ano_escolar_nome,
        'total_alunos': s.total_alunos,
        'alunos_ativos': s.alunos_ativos,
        'media': s.media
    } for s in anos_escolares_query])
    
    if not df_anos_escolares.empty:
        df_anos_escolares = df_anos_escolares.rename(columns={
            'Ano Escolar': 'Ano Escolar',
            'total_alunos': 'Total de Alunos',
            'alunos_ativos': 'Alunos Ativos',
            'media': 'Média (%)'
        })
        df_anos_escolares['Média (%)'] = df_anos_escolares['Média (%)'].round(1)
    df_anos_escolares.to_excel(writer, sheet_name='Desempenho por Ano Escolar', index=False)

    # Buscar dados por disciplina
    disciplinas = db.session.query(
        Disciplinas.nome.label('disciplina'),
        func.count(func.distinct(DesempenhoSimulado.aluno_id)).label('total_alunos'),
        func.count(func.distinct(DesempenhoSimulado.simulado_id)).label('total_questoes'),
        func.round(func.avg(DesempenhoSimulado.desempenho), 1).label('media_acertos')
    ).outerjoin(
        SimuladosGerados, SimuladosGerados.disciplina_id == Disciplinas.id
    ).outerjoin(
        DesempenhoSimulado, and_(
            DesempenhoSimulado.simulado_id == SimuladosGerados.id,
            *data_condition
        )
    ).join(
        Usuarios, and_(
            Usuarios.id == DesempenhoSimulado.aluno_id,
            Usuarios.escola_id == escola_id
        )
    ).group_by(
        Disciplinas.id, Disciplinas.nome
    ).having(
        func.count(func.distinct(DesempenhoSimulado.aluno_id)) > 0
    ).order_by(
        db.desc('media_acertos')
    ).all()
    
    df_disciplinas = pd.DataFrame([{
        'disciplina': d.disciplina,
        'total_alunos': d.total_alunos,
        'total_questoes': d.total_questoes,
        'media_acertos': d.media_acertos
    } for d in disciplinas])
    
    if not df_disciplinas.empty:
        df_disciplinas = df_disciplinas.rename(columns={
            'disciplina': 'Disciplina',
            'total_alunos': 'Total de Alunos',
            'total_questoes': 'Total de Questões',
            'media_acertos': 'Média de Acertos (%)'
        })
    df_disciplinas.to_excel(writer, sheet_name='Desempenho por Disciplina', index=False)
    
    writer.close()
    output.seek(0)
    
    return send_file(
        output,
        download_name=f'relatorio_escola_{escola_id}.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@relatorios_bp.route('/relatorio_disciplina')
@login_required
def relatorio_disciplina():
    """Página de relatório por disciplina."""
    if current_user.tipo_usuario_id not in [5, 6]:
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))
    
    codigo_ibge = current_user.codigo_ibge
    
    # Buscar todas as disciplinas
    disciplinas = db.session.query(
        Disciplinas.id,
        Disciplinas.nome
    ).order_by(
        Disciplinas.nome
    ).all()
    
    # Obter disciplina_id e mês da query string
    disciplina_id = request.args.get('disciplina_id', type=int)
    mes = request.args.get('mes', type=int)
    ano = 2025  # Fixado em 2025
    
    # Se uma disciplina foi selecionada, buscar seus dados
    if disciplina_id:
        # Construir a condição de data
        data_condition = [extract('year', DesempenhoSimulado.data_resposta) == ano]
        if mes:
            data_condition.append(extract('month', DesempenhoSimulado.data_resposta) == mes)
        
        # Subquery para simulados da disciplina
        simulados_disciplina = db.session.query(
            DesempenhoSimulado.aluno_id,
            DesempenhoSimulado.simulado_id,
            DesempenhoSimulado.desempenho
        ).filter(
            or_(
                and_(
                    DesempenhoSimulado.tipo_usuario_id == 5,
                    exists().where(
                        and_(
                            SimuladosGerados.id == DesempenhoSimulado.simulado_id,
                            SimuladosGerados.disciplina_id == disciplina_id
                        )
                    )
                ),
                and_(
                    DesempenhoSimulado.tipo_usuario_id == 3,
                    exists().where(
                        and_(
                            SimuladosGeradosProfessor.id == DesempenhoSimulado.simulado_id,
                            SimuladosGeradosProfessor.disciplina_id == disciplina_id
                        )
                    )
                )
            ),
            DesempenhoSimulado.codigo_ibge == codigo_ibge,
            *data_condition
        ).subquery()
        
        # Buscar dados gerais da disciplina
        disciplina = db.session.query(
            Disciplinas.nome,
            func.count(func.distinct(simulados_disciplina.c.aluno_id)).label('total_alunos'),
            func.count(func.distinct(simulados_disciplina.c.simulado_id)).label('total_simulados'),
            func.count(simulados_disciplina.c.simulado_id).label('total_questoes'),
            func.coalesce(func.avg(simulados_disciplina.c.desempenho), 0.0).label('media_geral')
        ).outerjoin(
            simulados_disciplina, literal(True)
        ).filter(
            Disciplinas.id == disciplina_id
        ).group_by(
            Disciplinas.id, Disciplinas.nome
        ).first()
        
        # Buscar dados por série
        anos_escolares_query = db.session.query(
            Ano_escolar.id,
            Ano_escolar.nome.label('Ano_escolar_nome'),
            func.count(func.distinct(simulados_disciplina.c.aluno_id)).label('total_alunos'),
            func.count(simulados_disciplina.c.simulado_id).label('total_questoes'),
            func.coalesce(func.avg(simulados_disciplina.c.desempenho), 0.0).label('media')
        ).outerjoin(
            Usuarios, Usuarios.ano_escolar_id == Ano_escolar.id
        ).outerjoin(
            simulados_disciplina, simulados_disciplina.c.aluno_id == Usuarios.id
        ).group_by(
            Ano_escolar.id, Ano_escolar.nome
        ).order_by(
            Ano_escolar.id
        ).all()
        
        anos_escolares = [dict(zip(['id', 'Ano_escolar_nome', 'total_alunos', 'total_questoes', 'media'], ano))
                       for ano in anos_escolares_query]
        
        # Buscar dados por escola
        escolas = db.session.query(
            Escolas.nome_da_escola.label('nome'),
            func.count(func.distinct(simulados_disciplina.c.aluno_id)).label('total_alunos'),
            func.count(simulados_disciplina.c.simulado_id).label('total_questoes'),
            func.round(func.avg(simulados_disciplina.c.desempenho), 1).label('media_acertos')
        ).outerjoin(
            Usuarios, Usuarios.escola_id == Escolas.id
        ).outerjoin(
            simulados_disciplina, simulados_disciplina.c.aluno_id == Usuarios.id
        ).filter(
            Escolas.codigo_ibge == codigo_ibge
        ).group_by(
            Escolas.id, Escolas.nome_da_escola
        ).having(
            func.count(func.distinct(simulados_disciplina.c.aluno_id)) > 0
        ).order_by(
            db.desc('media_acertos')
        ).all()
        
        return render_template('secretaria_educacao/relatorio_disciplina.html',
                             ano=ano,
                             mes=mes,
                             disciplinas=disciplinas,
                             disciplina_id=disciplina_id,
                             media_geral=round(disciplina.media_geral, 1),
                             total_alunos=disciplina.total_alunos,
                             total_questoes=disciplina.total_questoes,
                             total_simulados=disciplina.total_simulados,
                             Ano_escolar=anos_escolares,
                             escolas=escolas)
    
    return render_template('secretaria_educacao/relatorio_disciplina.html',
                         ano=ano,
                         mes=mes,
                         disciplinas=disciplinas,
                         disciplina_id=None)

@relatorios_bp.route('/relatorio_disciplina/export_pdf')
@login_required
def export_pdf_disciplina():
    """Exportar relatório da disciplina em PDF."""
    if current_user.tipo_usuario_id not in [5, 6]:
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))
    
    # Obter disciplina_id e mês da query string
    disciplina_id = request.args.get('disciplina_id', type=int)
    mes = request.args.get('mes', type=int)
    ano = 2025  # Fixado em 2025
    
    if not disciplina_id:
        flash("Disciplina não especificada.", "danger")
        return redirect(url_for("secretaria_educacao.relatorio_disciplina"))
    
    # Construir a condição de data
    data_condition = [extract('year', DesempenhoSimulado.data_resposta) == ano]
    if mes:
        data_condition.append(extract('month', DesempenhoSimulado.data_resposta) == mes)
    
    # Subquery para simulados da disciplina
    simulados_disciplina = db.session.query(
        DesempenhoSimulado.aluno_id,
        DesempenhoSimulado.simulado_id,
        DesempenhoSimulado.desempenho
    ).filter(
        or_(
            and_(
                DesempenhoSimulado.tipo_usuario_id == 5,
                exists().where(
                    and_(
                        SimuladosGerados.id == DesempenhoSimulado.simulado_id,
                        SimuladosGerados.disciplina_id == disciplina_id
                    )
                )
            ),
            and_(
                DesempenhoSimulado.tipo_usuario_id == 3,
                exists().where(
                    and_(
                        SimuladosGeradosProfessor.id == DesempenhoSimulado.simulado_id,
                        SimuladosGeradosProfessor.disciplina_id == disciplina_id
                    )
                )
            )
        ),
        DesempenhoSimulado.codigo_ibge == current_user.codigo_ibge,
        *data_condition
    ).subquery()
    
    # Buscar dados da disciplina
    disciplina = db.session.query(
        Disciplinas.nome,
        func.count(func.distinct(simulados_disciplina.c.aluno_id)).label('total_alunos'),
        func.count(func.distinct(simulados_disciplina.c.simulado_id)).label('total_simulados'),
        func.count(simulados_disciplina.c.simulado_id).label('total_questoes'),
        func.coalesce(func.avg(simulados_disciplina.c.desempenho), 0.0).label('media_geral')
    ).outerjoin(
        simulados_disciplina, literal(True)
    ).filter(
        Disciplinas.id == disciplina_id
    ).group_by(
        Disciplinas.id, Disciplinas.nome
    ).first()
    
    # Buscar dados por série
    anos_escolares_query = db.session.query(
        Ano_escolar.id,
        Ano_escolar.nome.label('Ano_escolar_nome'),
        func.count(func.distinct(simulados_disciplina.c.aluno_id)).label('total_alunos'),
        func.count(simulados_disciplina.c.simulado_id).label('total_questoes'),
        func.coalesce(func.avg(simulados_disciplina.c.desempenho), 0.0).label('media')
    ).outerjoin(
        Usuarios, Usuarios.ano_escolar_id == Ano_escolar.id
    ).outerjoin(
        simulados_disciplina, simulados_disciplina.c.aluno_id == Usuarios.id
    ).group_by(
        Ano_escolar.id, Ano_escolar.nome
    ).order_by(
        Ano_escolar.id
    ).all()
    
    anos_escolares = [dict(zip(['id', 'Ano_escolar_nome', 'total_alunos', 'total_questoes', 'media'], ano))
                   for ano in anos_escolares_query]
    
    # Buscar dados por escola
    escolas = db.session.query(
        Escolas.nome_da_escola.label('nome'),
        func.count(func.distinct(simulados_disciplina.c.aluno_id)).label('total_alunos'),
        func.count(simulados_disciplina.c.simulado_id).label('total_questoes'),
        func.round(func.avg(simulados_disciplina.c.desempenho), 1).label('media_acertos')
    ).outerjoin(
        Usuarios, Usuarios.escola_id == Escolas.id
    ).outerjoin(
        simulados_disciplina, simulados_disciplina.c.aluno_id == Usuarios.id
    ).filter(
        Escolas.codigo_ibge == current_user.codigo_ibge
    ).group_by(
        Escolas.id, Escolas.nome_da_escola
    ).having(
        func.count(func.distinct(simulados_disciplina.c.aluno_id)) > 0
    ).order_by(
        db.desc('media_acertos')
    ).all()
    
    # Renderizar o template HTML
    html = render_template('secretaria_educacao/relatorio_disciplina_pdf.html',
                         ano=ano,
                         mes=MESES_NOMES.get(mes) if mes else None,
                         disciplina=disciplina,
                         media_geral=round(disciplina.media_geral, 1),
                         total_alunos=disciplina.total_alunos,
                         total_questoes=disciplina.total_questoes,
                         total_simulados=disciplina.total_simulados,
                         Ano_escolar=anos_escolares,
                         escolas=escolas)
    
    # Gerar o PDF
    pdf = HTML(string=html).write_pdf()
    
    return send_file(
        BytesIO(pdf),
        download_name=f'relatorio_disciplina_{disciplina_id}.pdf',
        mimetype='application/pdf'
    )

@relatorios_bp.route('/relatorio_disciplina/export_excel')
@login_required
def export_excel_disciplina():
    """Exportar relatório da disciplina em Excel."""
    if current_user.tipo_usuario_id not in [5, 6]:
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))
    
    # Obter disciplina_id e mês da query string
    disciplina_id = request.args.get('disciplina_id', type=int)
    mes = request.args.get('mes', type=int)
    ano = 2025  # Fixado em 2025
    
    if not disciplina_id:
        flash("Disciplina não especificada.", "danger")
        return redirect(url_for("secretaria_educacao.relatorio_disciplina"))
    
    # Construir a condição de data
    data_condition = [extract('year', DesempenhoSimulado.data_resposta) == ano]
    if mes:
        data_condition.append(extract('month', DesempenhoSimulado.data_resposta) == mes)
    
    # Subquery para simulados da disciplina
    simulados_disciplina = db.session.query(
        DesempenhoSimulado.aluno_id,
        DesempenhoSimulado.simulado_id,
        DesempenhoSimulado.desempenho
    ).filter(
        or_(
            and_(
                DesempenhoSimulado.tipo_usuario_id == 5,
                exists().where(
                    and_(
                        SimuladosGerados.id == DesempenhoSimulado.simulado_id,
                        SimuladosGerados.disciplina_id == disciplina_id
                    )
                )
            ),
            and_(
                DesempenhoSimulado.tipo_usuario_id == 3,
                exists().where(
                    and_(
                        SimuladosGeradosProfessor.id == DesempenhoSimulado.simulado_id,
                        SimuladosGeradosProfessor.disciplina_id == disciplina_id
                    )
                )
            )
        ),
        DesempenhoSimulado.codigo_ibge == current_user.codigo_ibge,
        *data_condition
    ).subquery()
    
    # Criar um Excel writer
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='openpyxl')
    
    # Buscar dados da disciplina para a aba Visão Geral
    disciplina = db.session.query(
        Disciplinas.nome,
        func.count(func.distinct(simulados_disciplina.c.aluno_id)).label('total_alunos'),
        func.count(func.distinct(simulados_disciplina.c.simulado_id)).label('total_simulados'),
        func.count(simulados_disciplina.c.simulado_id).label('total_questoes'),
        func.coalesce(func.avg(simulados_disciplina.c.desempenho), 0.0).label('media_geral')
    ).outerjoin(
        simulados_disciplina, literal(True)
    ).filter(
        Disciplinas.id == disciplina_id
    ).group_by(
        Disciplinas.id, Disciplinas.nome
    ).first()
    
    df_geral = pd.DataFrame([{
        'Indicador': 'Média Geral',
        'Valor': f"{round(disciplina.media_geral, 1)}%"
    }, {
        'Indicador': 'Total de Alunos',
        'Valor': str(disciplina.total_alunos)
    }, {
        'Indicador': 'Total de Questões',
        'Valor': str(disciplina.total_questoes)
    }, {
        'Indicador': 'Simulados com a Disciplina',
        'Valor': str(disciplina.total_simulados)
    }])
    df_geral.to_excel(writer, sheet_name='Visão Geral', index=False)
    
    # Buscar dados por série
    anos_escolares_query = db.session.query(
        Ano_escolar.nome.label('Ano_escolar_nome'),
        func.count(func.distinct(simulados_disciplina.c.aluno_id)).label('total_alunos'),
        func.count(simulados_disciplina.c.simulado_id).label('total_questoes'),
        func.coalesce(func.avg(simulados_disciplina.c.desempenho), 0.0).label('media')
    ).outerjoin(
        Usuarios, Usuarios.ano_escolar_id == Ano_escolar.id
    ).outerjoin(
        simulados_disciplina, simulados_disciplina.c.aluno_id == Usuarios.id
    ).group_by(
        Ano_escolar.id, Ano_escolar.nome
    ).order_by(
        Ano_escolar.id
    ).all()
    
    df_anos_escolares = pd.DataFrame([{
        'Ano Escolar': s.Ano_escolar_nome,
        'Total de Alunos': s.total_alunos,
        'Total de Questões': s.total_questoes,
        'Média (%)': round(s.media, 1)
    } for s in anos_escolares_query])
    df_anos_escolares.to_excel(writer, sheet_name='Desempenho por Ano Escolar', index=False)
    
    # Buscar dados por escola
    escolas = db.session.query(
        Escolas.nome_da_escola.label('escola'),
        func.count(func.distinct(simulados_disciplina.c.aluno_id)).label('total_alunos'),
        func.count(simulados_disciplina.c.simulado_id).label('total_questoes'),
        func.round(func.avg(simulados_disciplina.c.desempenho), 1).label('media_acertos')
    ).outerjoin(
        Usuarios, Usuarios.escola_id == Escolas.id
    ).outerjoin(
        simulados_disciplina, simulados_disciplina.c.aluno_id == Usuarios.id
    ).filter(
        Escolas.codigo_ibge == current_user.codigo_ibge
    ).group_by(
        Escolas.id, Escolas.nome_da_escola
    ).having(
        func.count(func.distinct(simulados_disciplina.c.aluno_id)) > 0
    ).order_by(
        db.desc('media_acertos')
    ).all()
    
    df_escolas = pd.DataFrame([{
        'Escola': e.escola,
        'Total de Alunos': e.total_alunos,
        'Total de Questões': e.total_questoes,
        'Média de Acertos (%)': e.media_acertos
    } for e in escolas])
    df_escolas.to_excel(writer, sheet_name='Desempenho por Escola', index=False)
    
    writer.close()
    output.seek(0)
    
    return send_file(
        output,
        download_name=f'relatorio_disciplina_{disciplina_id}.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@relatorios_bp.route('/relatorio_tipo_ensino')
@login_required
def relatorio_tipo_ensino():
    """Página do relatório por tipo de ensino."""
    if current_user.tipo_usuario_id not in [5, 6]:
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))
    
    # Obter mês da query string
    mes = request.args.get('mes', type=int)
    ano = 2025  # Fixado em 2025
    
    # Construir a condição de data
    data_condition = [extract('year', DesempenhoSimulado.data_resposta) == ano]
    if mes:
        data_condition.append(extract('month', DesempenhoSimulado.data_resposta) == mes)
    
    # Subquery para simulados dos alunos
    simulados_alunos = db.session.query(
        DesempenhoSimulado.aluno_id,
        DesempenhoSimulado.simulado_id,
        DesempenhoSimulado.desempenho,
        Usuarios.escola_id,
        Escolas.tipo_ensino_id
    ).join(
        Usuarios, Usuarios.id == DesempenhoSimulado.aluno_id
    ).join(
        Escolas, Escolas.id == Usuarios.escola_id
    ).filter(
        DesempenhoSimulado.codigo_ibge == current_user.codigo_ibge,
        *data_condition
    ).subquery()
    
    # Obter dados gerais
    dados_gerais = db.session.query(
        func.count(func.distinct(simulados_alunos.c.aluno_id)).label('total_alunos'),
        func.count(func.distinct(simulados_alunos.c.simulado_id)).label('total_simulados'),
        func.count(simulados_alunos.c.simulado_id).label('total_questoes'),
        func.coalesce(func.avg(simulados_alunos.c.desempenho), 0.0).label('media_geral')
    ).first()
    
    # Obter dados por tipo de ensino
    tipos_ensino = db.session.query(
        TiposEnsino.nome,
        func.count(func.distinct(simulados_alunos.c.aluno_id)).label('total_alunos'),
        func.count(simulados_alunos.c.simulado_id).label('total_questoes'),
        func.coalesce(func.avg(simulados_alunos.c.desempenho), 0.0).label('media')
    ).outerjoin(
        simulados_alunos, simulados_alunos.c.tipo_ensino_id == TiposEnsino.id
    ).group_by(
        TiposEnsino.id, TiposEnsino.nome
    ).having(
        func.count(func.distinct(simulados_alunos.c.aluno_id)) > 0
    ).order_by(
        db.desc('media')
    ).all()
    
    # Obter dados por escola
    escolas = db.session.query(
        Escolas.nome_da_escola.label('nome'),
        TiposEnsino.nome.label('tipo_ensino'),
        func.count(func.distinct(simulados_alunos.c.aluno_id)).label('total_alunos'),
        func.count(simulados_alunos.c.simulado_id).label('total_questoes'),
        func.coalesce(func.avg(simulados_alunos.c.desempenho), 0.0).label('media')
    ).join(
        TiposEnsino, TiposEnsino.id == Escolas.tipo_ensino_id
    ).outerjoin(
        simulados_alunos, simulados_alunos.c.escola_id == Escolas.id
    ).filter(
        Escolas.codigo_ibge == current_user.codigo_ibge
    ).group_by(
        Escolas.id, Escolas.nome_da_escola, TiposEnsino.nome
    ).having(
        func.count(func.distinct(simulados_alunos.c.aluno_id)) > 0
    ).order_by(
        db.desc('media')
    ).all()
    
    return render_template(
        'secretaria_educacao/relatorio_tipo_ensino.html',
        ano=ano,
        mes=mes,
        media_geral=dados_gerais.media_geral,
        total_alunos=dados_gerais.total_alunos,
        total_questoes=dados_gerais.total_questoes,
        total_simulados=dados_gerais.total_simulados,
        tipos_ensino=tipos_ensino,
        escolas=escolas
    )

@relatorios_bp.route('/relatorio_tipo_ensino/export_pdf')
@login_required
def export_pdf_tipo_ensino():
    """Exportar relatório por tipo de ensino em PDF."""
    if current_user.tipo_usuario_id not in [5, 6]:
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))
    
    # Obter mês da query string
    mes = request.args.get('mes', type=int)
    ano = 2025  # Fixado em 2025
    
    # Construir a condição de data
    data_condition = [extract('year', DesempenhoSimulado.data_resposta) == ano]
    if mes:
        data_condition.append(extract('month', DesempenhoSimulado.data_resposta) == mes)
    
    # Subquery para simulados dos alunos
    simulados_alunos = db.session.query(
        DesempenhoSimulado.aluno_id,
        DesempenhoSimulado.simulado_id,
        DesempenhoSimulado.desempenho,
        Usuarios.escola_id,
        Escolas.tipo_ensino_id
    ).join(
        Usuarios, Usuarios.id == DesempenhoSimulado.aluno_id
    ).join(
        Escolas, Escolas.id == Usuarios.escola_id
    ).filter(
        DesempenhoSimulado.codigo_ibge == current_user.codigo_ibge,
        *data_condition
    ).subquery()
    
    # Obter dados gerais
    dados_gerais = db.session.query(
        func.count(func.distinct(simulados_alunos.c.aluno_id)).label('total_alunos'),
        func.count(func.distinct(simulados_alunos.c.simulado_id)).label('total_simulados'),
        func.count(simulados_alunos.c.simulado_id).label('total_questoes'),
        func.coalesce(func.avg(simulados_alunos.c.desempenho), 0.0).label('media_geral')
    ).first()
    
    # Obter dados por tipo de ensino
    tipos_ensino = db.session.query(
        TiposEnsino.nome,
        func.count(func.distinct(simulados_alunos.c.aluno_id)).label('total_alunos'),
        func.count(simulados_alunos.c.simulado_id).label('total_questoes'),
        func.coalesce(func.avg(simulados_alunos.c.desempenho), 0.0).label('media')
    ).outerjoin(
        simulados_alunos, simulados_alunos.c.tipo_ensino_id == TiposEnsino.id
    ).group_by(
        TiposEnsino.id, TiposEnsino.nome
    ).having(
        func.count(func.distinct(simulados_alunos.c.aluno_id)) > 0
    ).order_by(
        db.desc('media')
    ).all()
    
    # Obter dados por escola
    escolas = db.session.query(
        Escolas.nome_da_escola.label('nome'),
        TiposEnsino.nome.label('tipo_ensino'),
        func.count(func.distinct(simulados_alunos.c.aluno_id)).label('total_alunos'),
        func.count(simulados_alunos.c.simulado_id).label('total_questoes'),
        func.coalesce(func.avg(simulados_alunos.c.desempenho), 0.0).label('media')
    ).join(
        TiposEnsino, TiposEnsino.id == Escolas.tipo_ensino_id
    ).outerjoin(
        simulados_alunos, simulados_alunos.c.escola_id == Escolas.id
    ).filter(
        Escolas.codigo_ibge == current_user.codigo_ibge
    ).group_by(
        Escolas.id, Escolas.nome_da_escola, TiposEnsino.nome
    ).having(
        func.count(func.distinct(simulados_alunos.c.aluno_id)) > 0
    ).order_by(
        db.desc('media')
    ).all()
    
    # Renderizar o template
    html = render_template(
        'secretaria_educacao/relatorio_tipo_ensino_pdf.html',
        ano=ano,
        mes=MESES_NOMES.get(mes) if mes else None,
        media_geral=dados_gerais.media_geral,
        total_alunos=dados_gerais.total_alunos,
        total_questoes=dados_gerais.total_questoes,
        total_simulados=dados_gerais.total_simulados,
        tipos_ensino=tipos_ensino,
        escolas=escolas
    )
    
    # Converter para PDF
    pdf = HTML(string=html).write_pdf()
    
    return send_file(
        BytesIO(pdf),
        download_name='relatorio_tipo_ensino.pdf',
        mimetype='application/pdf'
    )

@relatorios_bp.route('/relatorio_tipo_ensino/export_excel')
@login_required
def export_excel_tipo_ensino():
    """Exportar relatório por tipo de ensino em Excel."""
    if current_user.tipo_usuario_id not in [5, 6]:
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))
    
    # Obter mês da query string
    mes = request.args.get('mes', type=int)
    ano = 2025  # Fixado em 2025
    
    # Construir a condição de data
    data_condition = [extract('year', DesempenhoSimulado.data_resposta) == ano]
    if mes:
        data_condition.append(extract('month', DesempenhoSimulado.data_resposta) == mes)
    
    # Subquery para simulados dos alunos
    simulados_alunos = db.session.query(
        DesempenhoSimulado.aluno_id,
        DesempenhoSimulado.simulado_id,
        DesempenhoSimulado.desempenho,
        Usuarios.escola_id,
        Escolas.tipo_ensino_id
    ).join(
        Usuarios, Usuarios.id == DesempenhoSimulado.aluno_id
    ).join(
        Escolas, Escolas.id == Usuarios.escola_id
    ).filter(
        DesempenhoSimulado.codigo_ibge == current_user.codigo_ibge,
        *data_condition
    ).subquery()
    
    # Obter dados gerais
    dados_gerais = db.session.query(
        func.count(func.distinct(simulados_alunos.c.aluno_id)).label('total_alunos'),
        func.count(func.distinct(simulados_alunos.c.simulado_id)).label('total_simulados'),
        func.count(simulados_alunos.c.simulado_id).label('total_questoes'),
        func.coalesce(func.avg(simulados_alunos.c.desempenho), 0.0).label('media_geral')
    ).first()
    
    # Criar um Excel writer
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='openpyxl')
    
    # Aba Visão Geral
    df_geral = pd.DataFrame([{
        'Indicador': 'Média Geral',
        'Valor': f"{round(dados_gerais.media_geral, 1)}%"
    }, {
        'Indicador': 'Total de Alunos',
        'Valor': str(dados_gerais.total_alunos)
    }, {
        'Indicador': 'Total de Questões',
        'Valor': str(dados_gerais.total_questoes)
    }, {
        'Indicador': 'Total de Simulados',
        'Valor': str(dados_gerais.total_simulados)
    }])
    df_geral.to_excel(writer, sheet_name='Visão Geral', index=False)
    
    # Obter dados por tipo de ensino
    tipos_ensino = db.session.query(
        TiposEnsino.nome,
        func.count(func.distinct(simulados_alunos.c.aluno_id)).label('total_alunos'),
        func.count(simulados_alunos.c.simulado_id).label('total_questoes'),
        func.coalesce(func.avg(simulados_alunos.c.desempenho), 0.0).label('media')
    ).outerjoin(
        simulados_alunos, simulados_alunos.c.tipo_ensino_id == TiposEnsino.id
    ).group_by(
        TiposEnsino.id, TiposEnsino.nome
    ).having(
        func.count(func.distinct(simulados_alunos.c.aluno_id)) > 0
    ).order_by(
        db.desc('media')
    ).all()
    
    df_tipos = pd.DataFrame([{
        'Tipo de Ensino': t.nome,
        'Total de Alunos': t.total_alunos,
        'Total de Questões': t.total_questoes,
        'Média (%)': round(t.media, 1)
    } for t in tipos_ensino])
    df_tipos.to_excel(writer, sheet_name='Desempenho por Tipo', index=False)
    
    # Obter dados por escola
    escolas = db.session.query(
        Escolas.nome_da_escola.label('nome'),
        TiposEnsino.nome.label('tipo_ensino'),
        func.count(func.distinct(simulados_alunos.c.aluno_id)).label('total_alunos'),
        func.count(simulados_alunos.c.simulado_id).label('total_questoes'),
        func.coalesce(func.avg(simulados_alunos.c.desempenho), 0.0).label('media')
    ).join(
        TiposEnsino, TiposEnsino.id == Escolas.tipo_ensino_id
    ).outerjoin(
        simulados_alunos, simulados_alunos.c.escola_id == Escolas.id
    ).filter(
        Escolas.codigo_ibge == current_user.codigo_ibge
    ).group_by(
        Escolas.id, Escolas.nome_da_escola, TiposEnsino.nome
    ).having(
        func.count(func.distinct(simulados_alunos.c.aluno_id)) > 0
    ).order_by(
        db.desc('media')
    ).all()
    
    df_escolas = pd.DataFrame([{
        'Escola': e.nome,
        'Tipo de Ensino': e.tipo_ensino,
        'Total de Alunos': e.total_alunos,
        'Total de Questões': e.total_questoes,
        'Média (%)': round(e.media, 1)
    } for e in escolas])
    df_escolas.to_excel(writer, sheet_name='Desempenho por Escola', index=False)
    
    writer.close()
    output.seek(0)
    
    return send_file(
        output,
        download_name='relatorio_tipo_ensino.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


@relatorios_bp.route('/relatorio_turma')
@login_required
def relatorio_turma():
    """Página de relatório por turma."""
    if current_user.tipo_usuario_id not in [5, 6]:
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))

    # Pegar parâmetros da URL
    escola_id = request.args.get('escola_id', type=int)
    turma_id = request.args.get('turma_id', type=int)
    ano = request.args.get('ano', default=datetime.now().year, type=int)
    mes = request.args.get('mes', type=int)

    # Construir condição de data
    data_condition = []
    if mes:
        data_condition.append(extract('month', DesempenhoSimulado.data_resposta) == mes)

    # Buscar todas as escolas
    escolas = db.session.query(
        Escolas.id, 
        Escolas.nome_da_escola
    ).filter(
        Escolas.codigo_ibge == current_user.codigo_ibge
    ).order_by(
        Escolas.nome_da_escola
    ).all()

    if escola_id:
        # Buscar turmas da escola selecionada
        turmas_query = db.session.query(
            Turmas.id,
            Turmas.turma,
            Ano_escolar.nome.label('Ano_escolar'),
            func.count(func.distinct(Usuarios.id)).label('total_alunos'),
            func.count(func.distinct(
                case((DesempenhoSimulado.id != None, Usuarios.id))
            )).label('alunos_ativos'),
            func.count(func.distinct(DesempenhoSimulado.simulado_id)).label('total_simulados'),
            func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media')
        ).filter(
            Turmas.escola_id == escola_id
        ).join(
            Ano_escolar, Ano_escolar.id == Turmas.ano_escolar_id
        ).outerjoin(
            Usuarios, and_(
                Usuarios.turma_id == Turmas.id,
                Usuarios.tipo_usuario_id == 4
            )
        ).outerjoin(
            DesempenhoSimulado, DesempenhoSimulado.aluno_id == Usuarios.id
        ).group_by(
            Turmas.id, Turmas.turma, Ano_escolar.nome
        ).order_by(Turmas.turma)

        turmas = turmas_query.all()

        # Buscar métricas gerais da escola
        escola_query = db.session.query(
            func.count(func.distinct(Usuarios.id)).label('total_alunos'),
            func.count(func.distinct(
                case((DesempenhoSimulado.id != None, Usuarios.id))
            )).label('alunos_ativos'),
            func.count(func.distinct(DesempenhoSimulado.simulado_id)).label('total_simulados'),
            func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media_geral')
        ).outerjoin(
            DesempenhoSimulado, DesempenhoSimulado.aluno_id == Usuarios.id
        ).filter(
            Usuarios.escola_id == escola_id,
            Usuarios.tipo_usuario_id == 4
        )

        escola = escola_query.first()

        # Subquery para médias por disciplina
        simulados_disciplinas = db.session.query(
            DesempenhoSimulado.aluno_id,
            DesempenhoSimulado.simulado_id,
            DesempenhoSimulado.desempenho,
            case(
                (SimuladosGerados.disciplina_id != None, SimuladosGerados.disciplina_id),
                (SimuladosGeradosProfessor.disciplina_id != None, SimuladosGeradosProfessor.disciplina_id)
            ).label('disciplina_id'),
            Usuarios.turma_id
        ).join(
            Usuarios, Usuarios.id == DesempenhoSimulado.aluno_id
        ).outerjoin(
            SimuladosGerados, and_(
                SimuladosGerados.id == DesempenhoSimulado.simulado_id,
                DesempenhoSimulado.tipo_usuario_id == 5
            )
        ).outerjoin(
            SimuladosGeradosProfessor, and_(
                SimuladosGeradosProfessor.id == DesempenhoSimulado.simulado_id,
                DesempenhoSimulado.tipo_usuario_id == 3
            )
        ).filter(
            Usuarios.escola_id == escola_id,
            *data_condition
        ).subquery()

        # Query para alunos e suas médias
        alunos_query = db.session.query(
            Turmas.id.label('turma_id'),
            Usuarios.id.label('aluno_id'),
            Usuarios.nome.label('aluno_nome'),
            func.count(func.distinct(DesempenhoSimulado.simulado_id)).label('total_simulados'),
            func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media'),
            func.max(case(
                (simulados_disciplinas.c.disciplina_id == 2, simulados_disciplinas.c.desempenho)
            )).label('media_matematica'),
            func.max(case(
                (simulados_disciplinas.c.disciplina_id == 1, simulados_disciplinas.c.desempenho)
            )).label('media_portugues'),
            func.max(case(
                (simulados_disciplinas.c.disciplina_id == 3, simulados_disciplinas.c.desempenho)
            )).label('media_ciencias'),
            func.max(case(
                (simulados_disciplinas.c.disciplina_id == 4, simulados_disciplinas.c.desempenho)
            )).label('media_historia'),
            func.max(case(
                (simulados_disciplinas.c.disciplina_id == 5, simulados_disciplinas.c.desempenho)
            )).label('media_geografia')
        ).join(
            Usuarios, and_(
                Usuarios.turma_id == Turmas.id,
                Usuarios.tipo_usuario_id == 4,
                Usuarios.escola_id == escola_id
            )
        ).outerjoin(
            DesempenhoSimulado, DesempenhoSimulado.aluno_id == Usuarios.id
        ).outerjoin(
            simulados_disciplinas, and_(
                simulados_disciplinas.c.aluno_id == Usuarios.id,
                simulados_disciplinas.c.turma_id == Turmas.id
            )
        )

        if turma_id:
            alunos_query = alunos_query.filter(Turmas.id == turma_id)

        alunos = alunos_query.group_by(
            Turmas.id, Turmas.turma, Usuarios.id, Usuarios.nome
        ).order_by(
            Turmas.turma, Usuarios.nome
        ).all()

        return render_template('secretaria_educacao/relatorio_turma.html',
                             ano=ano,
                             mes=mes,
                             escolas=escolas,
                             escola_id=escola_id,
                             turma_id=turma_id,
                             media_geral=round(escola.media_geral, 1),
                             total_alunos=escola.total_alunos,
                             alunos_ativos=escola.alunos_ativos,
                             total_simulados=escola.total_simulados,
                             turmas=turmas,
                             alunos=alunos)
    
    return render_template('secretaria_educacao/relatorio_turma.html',
                         ano=ano,
                         mes=mes,
                         escolas=escolas,
                         escola_id=None,
                         turma_id=None)

@relatorios_bp.route('/relatorio_turma/export_pdf')
@login_required
def export_pdf_turma():
    """Exportar relatório por turma em PDF."""
    if current_user.tipo_usuario_id not in [5, 6]:
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))
    
    # Obter mês da query string
    mes = request.args.get('mes', type=int)
    ano = 2025  # Fixado em 2025
    
    # Construir a condição de data
    data_condition = [extract('year', DesempenhoSimulado.data_resposta) == ano]
    if mes:
        data_condition.append(extract('month', DesempenhoSimulado.data_resposta) == mes)
    
    # Obter dados gerais
    dados_gerais = db.session.query(
        func.count(func.distinct(DesempenhoSimulado.aluno_id)).label('total_alunos'),
        func.count(func.distinct(DesempenhoSimulado.simulado_id)).label('total_simulados'),
        func.count(DesempenhoSimulado.simulado_id).label('total_questoes'),
        func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media_geral')
    ).join(
        Usuarios, Usuarios.id == DesempenhoSimulado.aluno_id
    ).filter(
        DesempenhoSimulado.codigo_ibge == current_user.codigo_ibge,
        *data_condition
    ).first()
    
    # Obter dados por turma
    turmas = db.session.query(
        Turmas.turma,
        func.count(func.distinct(DesempenhoSimulado.aluno_id)).label('total_alunos'),
        func.count(DesempenhoSimulado.simulado_id).label('total_questoes'),
        func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media')
    ).join(
        Usuarios, Usuarios.turma_id == Turmas.id
    ).outerjoin(
        DesempenhoSimulado, and_(
            DesempenhoSimulado.aluno_id == Usuarios.id,
            DesempenhoSimulado.codigo_ibge == current_user.codigo_ibge,
            *data_condition
        )
    ).filter(
        Usuarios.tipo_usuario_id == 1,
        Usuarios.codigo_ibge == current_user.codigo_ibge
    ).group_by(
        Turmas.id, Turmas.turma
    ).having(
        func.count(func.distinct(DesempenhoSimulado.aluno_id)) > 0
    ).order_by(
        Turmas.turma
    ).all()
    
    # Obter dados por escola e turma
    escolas_turmas = db.session.query(
        Escolas.nome_da_escola.label('escola'),
        Turmas.turma,
        func.count(func.distinct(DesempenhoSimulado.aluno_id)).label('total_alunos'),
        func.count(DesempenhoSimulado.simulado_id).label('total_questoes'),
        func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media')
    ).join(
        Usuarios, Usuarios.escola_id == Escolas.id
    ).join(
        Turmas, Turmas.id == Usuarios.turma_id
    ).outerjoin(
        DesempenhoSimulado, and_(
            DesempenhoSimulado.aluno_id == Usuarios.id,
            DesempenhoSimulado.codigo_ibge == current_user.codigo_ibge,
            *data_condition
        )
    ).filter(
        Usuarios.tipo_usuario_id == 1,
        Escolas.codigo_ibge == current_user.codigo_ibge
    ).group_by(
        Escolas.id, Escolas.nome_da_escola, Turmas.id, Turmas.turma
    ).having(
        func.count(func.distinct(DesempenhoSimulado.aluno_id)) > 0
    ).order_by(
        Escolas.nome_da_escola, Turmas.turma
    ).all()
    
    # Renderizar o template
    html = render_template(
        'secretaria_educacao/relatorio_turma_pdf.html',
        ano=ano,
        mes=MESES_NOMES.get(mes) if mes else None,
        media_geral=dados_gerais.media_geral,
        total_alunos=dados_gerais.total_alunos,
        total_questoes=dados_gerais.total_questoes,
        total_simulados=dados_gerais.total_simulados,
        turmas=turmas,
        escolas_turmas=escolas_turmas
    )
    
    # Converter para PDF
    pdf = HTML(string=html).write_pdf()
    
    return send_file(
        BytesIO(pdf),
        download_name='relatorio_turma.pdf',
        mimetype='application/pdf'
    )

@relatorios_bp.route('/relatorio_turma/export_excel')
@login_required
def export_excel_turma():
    """Exportar relatório por turma em Excel."""
    if current_user.tipo_usuario_id not in [5, 6]:
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))
    
    # Obter mês da query string
    mes = request.args.get('mes', type=int)
    ano = 2025  # Fixado em 2025
    
    # Construir a condição de data
    data_condition = [extract('year', DesempenhoSimulado.data_resposta) == ano]
    if mes:
        data_condition.append(extract('month', DesempenhoSimulado.data_resposta) == mes)
    
    # Obter dados gerais
    dados_gerais = db.session.query(
        func.count(func.distinct(DesempenhoSimulado.aluno_id)).label('total_alunos'),
        func.count(func.distinct(DesempenhoSimulado.simulado_id)).label('total_simulados'),
        func.count(DesempenhoSimulado.simulado_id).label('total_questoes'),
        func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media_geral')
    ).join(
        Usuarios, Usuarios.id == DesempenhoSimulado.aluno_id
    ).filter(
        DesempenhoSimulado.codigo_ibge == current_user.codigo_ibge,
        *data_condition
    ).first()
    
    # Criar um Excel writer
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='openpyxl')
    
    # Aba Visão Geral
    df_geral = pd.DataFrame([{
        'Indicador': 'Média Geral',
        'Valor': f"{round(dados_gerais.media_geral, 1)}%"
    }, {
        'Indicador': 'Total de Alunos',
        'Valor': str(dados_gerais.total_alunos)
    }, {
        'Indicador': 'Total de Questões',
        'Valor': str(dados_gerais.total_questoes)
    }, {
        'Indicador': 'Total de Simulados',
        'Valor': str(dados_gerais.total_simulados)
    }])
    df_geral.to_excel(writer, sheet_name='Visão Geral', index=False)
    
    # Obter dados por turma
    turmas = db.session.query(
        Turmas.turma,
        func.count(func.distinct(DesempenhoSimulado.aluno_id)).label('total_alunos'),
        func.count(DesempenhoSimulado.simulado_id).label('total_questoes'),
        func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media')
    ).join(
        Usuarios, Usuarios.turma_id == Turmas.id
    ).outerjoin(
        DesempenhoSimulado, and_(
            DesempenhoSimulado.aluno_id == Usuarios.id,
            DesempenhoSimulado.codigo_ibge == current_user.codigo_ibge,
            *data_condition
        )
    ).filter(
        Usuarios.tipo_usuario_id == 1,
        Usuarios.codigo_ibge == current_user.codigo_ibge
    ).group_by(
        Turmas.id, Turmas.turma
    ).having(
        func.count(func.distinct(DesempenhoSimulado.aluno_id)) > 0
    ).order_by(
        Turmas.turma
    ).all()
    
    df_turmas = pd.DataFrame([{
        'Turma': t.turma,
        'Total de Alunos': t.total_alunos,
        'Total de Questões': t.total_questoes,
        'Média (%)': round(t.media, 1)
    } for t in turmas])
    
    if not df_turmas.empty:
        df_turmas.to_excel(writer, sheet_name='Desempenho por Turma', index=False)
    
    # Obter dados por escola e turma
    escolas_turmas = db.session.query(
        Escolas.nome_da_escola.label('escola'),
        Turmas.turma,
        func.count(func.distinct(DesempenhoSimulado.aluno_id)).label('total_alunos'),
        func.count(DesempenhoSimulado.simulado_id).label('total_questoes'),
        func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media')
    ).join(
        Usuarios, Usuarios.escola_id == Escolas.id
    ).join(
        Turmas, Turmas.id == Usuarios.turma_id
    ).outerjoin(
        DesempenhoSimulado, and_(
            DesempenhoSimulado.aluno_id == Usuarios.id,
            DesempenhoSimulado.codigo_ibge == current_user.codigo_ibge,
            *data_condition
        )
    ).filter(
        Usuarios.tipo_usuario_id == 1,
        Escolas.codigo_ibge == current_user.codigo_ibge
    ).group_by(
        Escolas.id, Escolas.nome_da_escola, Turmas.id, Turmas.turma
    ).having(
        func.count(func.distinct(DesempenhoSimulado.aluno_id)) > 0
    ).order_by(
        Escolas.nome_da_escola, Turmas.turma
    ).all()
    
    df_escolas = pd.DataFrame([{
        'Escola': e.escola,
        'Turma': e.turma,
        'Total de Alunos': e.total_alunos,
        'Total de Questões': e.total_questoes,
        'Média (%)': round(e.media, 1)
    } for e in escolas_turmas])
    
    if not df_escolas.empty:
        df_escolas.to_excel(writer, sheet_name='Desempenho por Escola', index=False)
    
    writer.close()
    output.seek(0)
    
    return send_file(
        output,
        download_name='relatorio_turma.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@relatorios_bp.route('/relatorio_individual')
@login_required
def relatorio_individual():
    """Página de relatório de desempenho individual."""
    if current_user.tipo_usuario_id not in [5, 6]:  # Verifica se é secretaria
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))
    
    # Obtém o ano atual
    ano = datetime.now().year
    
    # Obtém os parâmetros de filtro
    mes = request.args.get('mes', type=int)
    aluno_id = request.args.get('aluno_id', type=int)
    nome_filtro = request.args.get('nome', '')
    escola_id = request.args.get('escola_id', type=int)
    ano_escolar_id = request.args.get('ano_escolar_id', type=int)
    turma_id = request.args.get('turma_id', type=int)
    
    # Condição de data para filtrar por mês
    data_condition = []
    if mes:
        data_condition.append(extract('month', DesempenhoSimulado.data_resposta) == mes)
    data_condition.append(extract('year', DesempenhoSimulado.data_resposta) == ano)
    
    # Query base para alunos
    alunos_query = db.session.query(
        Usuarios.id,
        Usuarios.nome.label('nome'),
        Escolas.nome_da_escola.label('escola'),
        Turmas.turma.label('turma'),
        Ano_escolar.nome.label('ano_escolar'),
        func.count(DesempenhoSimulado.id).label('total_simulados'),
        func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media_geral')
    ).join(
        Escolas, Usuarios.escola_id == Escolas.id
    ).join(
        Turmas, Usuarios.turma_id == Turmas.id
    ).join(
        Ano_escolar, Turmas.ano_escolar_id == Ano_escolar.id
    ).outerjoin(
        DesempenhoSimulado, and_(
            DesempenhoSimulado.aluno_id == Usuarios.id,
            *data_condition
        )
    ).filter(
        Usuarios.tipo_usuario_id == 4  # Tipo aluno
    )

    # Aplicar filtros
    if nome_filtro:
        alunos_query = alunos_query.filter(Usuarios.nome.ilike(f'%{nome_filtro}%'))
    if escola_id:
        alunos_query = alunos_query.filter(Usuarios.escola_id == escola_id)
    if ano_escolar_id:
        alunos_query = alunos_query.filter(Turmas.ano_escolar_id == ano_escolar_id)
    if turma_id:
        alunos_query = alunos_query.filter(Usuarios.turma_id == turma_id)

    # Aplicar group by e order by
    alunos_query = alunos_query.group_by(
        Usuarios.id,
        Usuarios.nome,
        Escolas.nome_da_escola,
        Turmas.turma,
        Ano_escolar.nome
    ).order_by(
        Escolas.nome_da_escola,
        Ano_escolar.nome,
        Turmas.turma,
        Usuarios.nome
    )
    
    alunos = alunos_query.all()
    
    # Buscar dados para os filtros
    escolas = db.session.query(Escolas.id, Escolas.nome_da_escola).order_by(Escolas.nome_da_escola).all()
    anos_escolares = db.session.query(Ano_escolar.id, Ano_escolar.nome).order_by(Ano_escolar.nome).all()
    turmas = db.session.query(Turmas.id, Turmas.turma).order_by(Turmas.turma).all()
    
    # Se um aluno específico foi selecionado
    aluno_data = None
    if aluno_id:
        # Desempenho por disciplina
        disciplinas_query = db.session.query(
            Disciplinas.nome.label('disciplina'),
            func.count(DesempenhoSimulado.id).label('total_simulados'),
            func.sum(func.json_length(DesempenhoSimulado.respostas_corretas)).label('total_questoes'),
            func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media')
        ).join(
            SimuladosGerados, SimuladosGerados.id == DesempenhoSimulado.simulado_id
        ).join(
            Disciplinas, Disciplinas.id == SimuladosGerados.disciplina_id
        ).filter(
            DesempenhoSimulado.aluno_id == aluno_id,
            *data_condition
        ).group_by(
            Disciplinas.nome
        ).order_by(
            Disciplinas.nome
        ).all()
        
        # Histórico de desempenho
        historico_query = db.session.query(
            DesempenhoSimulado.data_resposta,
            Disciplinas.nome.label('disciplina'),
            DesempenhoSimulado.desempenho.label('nota'),
            func.json_length(DesempenhoSimulado.respostas_corretas).label('total_questoes'),
            func.json_length(case((DesempenhoSimulado.respostas_aluno == DesempenhoSimulado.respostas_corretas, DesempenhoSimulado.respostas_aluno), else_=None)).label('questoes_corretas')
        ).join(
            SimuladosGerados, SimuladosGerados.id == DesempenhoSimulado.simulado_id
        ).join(
            Disciplinas, Disciplinas.id == SimuladosGerados.disciplina_id
        ).filter(
            DesempenhoSimulado.aluno_id == aluno_id,
            *data_condition
        ).order_by(
            DesempenhoSimulado.data_resposta.desc()
        ).all()

        # Converter os resultados em dicionários
        historico_list = []
        for item in historico_query:
            historico_list.append({
                'data_resposta': item.data_resposta,
                'disciplina': item.disciplina,
                'nota': float(item.nota) if item.nota else 0.0,
                'total_questoes': item.total_questoes,
                'questoes_corretas': item.questoes_corretas
            })
        
        # Dados do aluno
        aluno = db.session.query(
            Usuarios.nome,
            Escolas.nome_da_escola.label('escola'),
            Turmas.turma.label('turma'),
            Ano_escolar.nome.label('ano_escolar')
        ).join(
            Escolas, Usuarios.escola_id == Escolas.id
        ).join(
            Turmas, Usuarios.turma_id == Turmas.id
        ).join(
            Ano_escolar, Turmas.ano_escolar_id == Ano_escolar.id
        ).filter(
            Usuarios.id == aluno_id
        ).first()
        
        aluno_data = {
            'info': {
                'nome': aluno.nome,
                'escola': aluno.escola,
                'turma': aluno.turma,
                'ano_escolar': aluno.ano_escolar
            },
            'disciplinas': disciplinas_query,
            'historico': historico_list
        }
    
    return render_template(
        'secretaria_educacao/relatorio_individual.html',
        alunos=alunos,
        aluno_data=aluno_data,
        mes=mes,
        ano=ano,
        escolas=escolas,
        anos_escolares=anos_escolares,
        turmas=turmas,
        nome_filtro=nome_filtro,
        escola_id=escola_id,
        ano_escolar_id=ano_escolar_id,
        turma_id=turma_id
    )