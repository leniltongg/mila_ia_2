from flask import Blueprint, request, render_template, flash, redirect, url_for, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from models import User
from security import check_login_attempts, reset_login_attempts, log_security_event, sanitize_input
from database import get_db

auth = Blueprint('auth', __name__, url_prefix='/auth')

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = sanitize_input(request.form.get('email'))
        senha = request.form.get('senha')

        if not email or not senha:
            flash('Por favor, preencha todos os campos.', 'error')
            return render_template('auth/login.html')

        # Verifica tentativas de login
        if not check_login_attempts(email):
            flash('Muitas tentativas de login. Tente novamente mais tarde.', 'error')
            log_security_event('excessive_login_attempts', details={'email': email})
            return render_template('auth/login.html'), 429

        db = get_db()
        cursor = db.cursor()
        
        try:
            cursor.execute("""
                SELECT id, nome, tipo_usuario_id, escola_id, serie_id, turma_id, email, 
                       codigo_ibge, senha_hash
                FROM usuarios 
                WHERE email = ?
            """, (email,))
            
            user_data = cursor.fetchone()
            
            if user_data and check_password_hash(user_data['senha_hash'], senha):
                user = User(
                    id=user_data['id'],
                    nome=user_data['nome'],
                    tipo_usuario_id=user_data['tipo_usuario_id'],
                    escola_id=user_data['escola_id'],
                    serie_id=user_data['serie_id'],
                    turma_id=user_data['turma_id'],
                    email=user_data['email'],
                    codigo_ibge=user_data['codigo_ibge']
                )
                login_user(user)
                reset_login_attempts(email)
                log_security_event('login_success', user_id=user.id)
                
                next_page = request.args.get('next')
                if not next_page or not next_page.startswith('/'):
                    next_page = url_for('index')
                return redirect(next_page)
            
            log_security_event('login_failure', details={'email': email})
            flash('Email ou senha incorretos.', 'error')
            return render_template('auth/login.html')
            
        except Exception as e:
            log_security_event('login_error', details={'error': str(e)})
            flash('Erro ao tentar fazer login. Tente novamente.', 'error')
            return render_template('auth/login.html')

    return render_template('auth/login.html')

@auth.route('/logout')
@login_required
def logout():
    log_security_event('logout', user_id=current_user.id)
    logout_user()
    flash('Você foi desconectado com sucesso.', 'success')
    return redirect(url_for('index'))

@auth.route('/alterar_senha', methods=['GET', 'POST'])
@login_required
def alterar_senha():
    if request.method == 'POST':
        senha_atual = request.form.get('senha_atual')
        nova_senha = request.form.get('nova_senha')
        confirmar_senha = request.form.get('confirmar_senha')

        if not all([senha_atual, nova_senha, confirmar_senha]):
            flash('Por favor, preencha todos os campos.', 'error')
            return render_template('auth/alterar_senha.html')

        if nova_senha != confirmar_senha:
            flash('As senhas não coincidem.', 'error')
            return render_template('auth/alterar_senha.html')

        db = get_db()
        cursor = db.cursor()

        try:
            # Verifica a senha atual
            cursor.execute("SELECT senha_hash FROM usuarios WHERE id = ?", (current_user.id,))
            result = cursor.fetchone()

            if not result or not check_password_hash(result['senha_hash'], senha_atual):
                flash('Senha atual incorreta.', 'error')
                log_security_event('failed_password_change', user_id=current_user.id)
                return render_template('auth/alterar_senha.html')

            # Atualiza a senha
            nova_senha_hash = generate_password_hash(nova_senha)
            cursor.execute("""
                UPDATE usuarios 
                SET senha_hash = ?, data_atualizacao_senha = CURRENT_TIMESTAMP 
                WHERE id = ?
            """, (nova_senha_hash, current_user.id))
            
            db.commit()
            log_security_event('password_changed', user_id=current_user.id)
            flash('Senha alterada com sucesso!', 'success')
            return redirect(url_for('index'))

        except Exception as e:
            db.rollback()
            flash('Erro ao alterar a senha. Tente novamente.', 'error')
            log_security_event('password_change_error', user_id=current_user.id, details={'error': str(e)})
            current_app.logger.error(f'Erro na alteração de senha: {str(e)}')

    return render_template('auth/alterar_senha.html')
