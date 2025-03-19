from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from models import db, Usuarios, Cidades
from datetime import datetime

secretaria_educacao_bp = Blueprint('secretaria_educacao_bp', __name__)

@secretaria_educacao_bp.route('/perfil')
@login_required
def perfil():
    try:
        # Buscar informações do usuário
        usuario = db.session.query(Usuarios).filter(
            Usuarios.id == current_user.id
        ).first()

        # Buscar informações da cidade
        cidade = None
        if usuario.cidade_id:
            cidade = db.session.query(Cidades).filter(
                Cidades.id == usuario.cidade_id
            ).first()

        # Formatação dos dados
        if usuario.data_nascimento:
            try:
                # Tentar converter para o formato brasileiro
                data = datetime.strptime(usuario.data_nascimento, '%Y-%m-%d')
                usuario.data_nascimento = data.strftime('%d/%m/%Y')
            except:
                pass

        # Formatar CPF se existir
        if usuario.cpf:
            cpf = usuario.cpf
            if len(cpf) == 11:
                usuario.cpf = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"

        return render_template('secretaria_educacao/perfil.html',
                             usuario=usuario,
                             cidade=cidade)
    except Exception as e:
        import traceback
        print(f"Erro detalhado ao carregar perfil: {str(e)}")
        print(traceback.format_exc())
        flash('Erro ao carregar perfil', 'danger')
        return redirect(url_for('secretaria_educacao_bp.index'))
