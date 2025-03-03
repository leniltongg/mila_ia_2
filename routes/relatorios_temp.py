from flask import Blueprint, render_template, request, jsonify, send_file, flash, redirect, url_for
from flask_login import login_required, current_user
from extensions import db
from models import *
import pandas as pd
from datetime import datetime
from utils import get_nome_mes, verificar_permissao
from weasyprint import HTML
from io import BytesIO
from sqlalchemy import func, and_, extract, case

relatorios_bp = Blueprint('relatorios', __name__)

@relatorios_bp.route('/relatorios_dashboard', methods=['GET'])
@login_required
def relatorios_dashboard():
    if current_user.tipo_usuario_id not in [5, 6]:  # Apenas para Secretaria de Educação
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))

    codigo_ibge = current_user.codigo_ibge

    # Desempenho geral
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

    return render_template(
        'secretaria_educacao/relatorios_dashboard.html',
        desempenho_geral=desempenho_geral,
        melhor_escola=melhor_escola
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
    return render_template('secretaria_educacao/relatorio_rede_municipal.html', mes=mes)

@relatorios_bp.route('/relatorio_rede_municipal/export_pdf')
@login_required
def export_pdf_relatorio():
    """Exportar relatório em PDF."""
    if current_user.tipo_usuario_id not in [5, 6]:
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))
    mes = request.args.get('mes', type=int)
    return send_file(
        path_or_file='relatorio.pdf',
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'relatorio_rede_municipal_{mes}.pdf'
    )

@relatorios_bp.route('/relatorio_rede_municipal/export_excel')
@login_required
def export_excel_relatorio():
    """Exportar relatório em Excel."""
    if current_user.tipo_usuario_id not in [5, 6]:
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))
    mes = request.args.get('mes', type=int)
    return send_file(
        path_or_file='relatorio.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'relatorio_rede_municipal_{mes}.xlsx'
    )
