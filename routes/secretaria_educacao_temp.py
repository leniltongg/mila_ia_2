@bp.route('/editar-tema-redacao/<int:tema_id>', methods=['GET', 'POST'])
@login_required
def editar_tema_redacao(tema_id):
    """Edita um tema de redação existente"""
    if current_user.tipo_usuario_id != 5:  # Secretaria de Educação
        flash('Acesso não autorizado.', 'danger')
        return redirect(url_for('index'))
        
    tema = TemasRedacao.query.get_or_404(tema_id)
    
    if request.method == 'POST':
        try:
            tema.titulo = request.form['titulo']
            tema.descricao = request.form['descricao']
            tema.tipo = request.form['tipo']
            tema.data_limite = datetime.strptime(request.form['data_limite'], '%Y-%m-%d') if request.form['data_limite'] else None
            tema.ano_escolar_id = request.form['ano_escolar_id']
            
            db.session.commit()
            flash('Tema de redação atualizado com sucesso!', 'success')
            return redirect(url_for('secretaria_educacao.gerenciar_temas_redacao'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar tema de redação: {str(e)}', 'danger')
            return redirect(url_for('secretaria_educacao.editar_tema_redacao', tema_id=tema_id))
    
    anos_escolares = Ano_escolar.query.all()
    return render_template(
        'secretaria_educacao/editar_tema_redacao.html',
        tema=tema,
        anos_escolares=anos_escolares
    )
