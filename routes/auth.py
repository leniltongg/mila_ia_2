from flask import Blueprint, request, render_template, flash, redirect, url_for
from flask_login import login_user
from models import User, TIPO_USUARIO_ADMIN, TIPO_USUARIO_SECRETARIA, TIPO_USUARIO_PROFESSOR, TIPO_USUARIO_ALUNO, TIPO_USUARIO_SECRETARIA_EDUCACAO
from security import check_password

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        login_identifier = request.form['email']  # Pode ser email ou CPF
        senha = request.form['senha']

        # Busca o usuário usando SQLAlchemy
        user = User.query.filter(
            (User.email == login_identifier) | (User.cpf == login_identifier)
        ).first()

        if user and check_password(senha, user.senha):  # Verifica a senha usando a função check_password
            login_user(user)
            flash('Login realizado com sucesso!', 'success')
            
            # Redirecionar com base no tipo de usuário
            if user.tipo_usuario_id == TIPO_USUARIO_PROFESSOR:
                return redirect(url_for("portal_professores"))
            elif user.tipo_usuario_id == TIPO_USUARIO_ALUNO:
                return redirect(url_for("alunos_bp.portal_alunos"))
            elif user.tipo_usuario_id == TIPO_USUARIO_ADMIN:
                return redirect(url_for("admin_v2.escolas_list"))  # Redirecionando para a lista de escolas
            elif user.tipo_usuario_id == TIPO_USUARIO_SECRETARIA:
                return redirect(url_for("portal_administracao"))
            elif user.tipo_usuario_id == TIPO_USUARIO_SECRETARIA_EDUCACAO:
                return redirect(url_for("secretaria_educacao.portal_secretaria_educacao"))
            else:
                return redirect(url_for("auth.login"))
        else:
            error = 'Credenciais inválidas. Por favor, tente novamente.'
            flash(error, 'error')

    return render_template('login.html', error=error)
