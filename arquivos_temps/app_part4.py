# Rotas principais
@app.route('/portal_administrador')
@login_required
def portal_administrador():
    if current_user.tipo_usuario_id != 1:
        flash('Acesso não autorizado', 'error')
        return redirect(url_for('home'))
    return render_template('admin/dashboard.html')

@app.route('/portal_secretaria')
@login_required
def portal_secretaria():
    if current_user.tipo_usuario_id != 2:
        flash('Acesso não autorizado', 'error')
        return redirect(url_for('home'))
    return render_template('secretaria/dashboard.html')

@app.route('/portal_professores')
@login_required
def portal_professores():
    if current_user.tipo_usuario_id not in [3, 6]:
        flash('Acesso não autorizado', 'error')
        return redirect(url_for('home'))
    return render_template('professores/dashboard.html')

@app.route('/portal_coordenador')
@login_required
def portal_coordenador():
    if current_user.tipo_usuario_id not in [4, 6]:
        flash('Acesso não autorizado', 'error')
        return redirect(url_for('home'))
    return render_template('coordenador/dashboard.html')

@app.route('/portal_alunos')
@login_required
def portal_alunos():
    if current_user.tipo_usuario_id not in [5, 6]:
        flash('Acesso não autorizado', 'error')
        return redirect(url_for('home'))
    return render_template('alunos/dashboard.html')

@app.route('/cadastrar_questao', methods=['GET', 'POST'])
@login_required
def cadastrar_questao():
    if current_user.tipo_usuario_id not in [1, 3]:  # Apenas admin e professores
        flash('Acesso não autorizado', 'error')
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        questao = request.form.get('questao')
        alternativa_a = request.form.get('alternativa_a')
        alternativa_b = request.form.get('alternativa_b')
        alternativa_c = request.form.get('alternativa_c')
        alternativa_d = request.form.get('alternativa_d')
        alternativa_e = request.form.get('alternativa_e')
        questao_correta = request.form.get('questao_correta')
        disciplina_id = request.form.get('disciplina_id')
        assunto = request.form.get('assunto')
        ano_escolar_id = request.form.get('ano_escolar_id')
        
        nova_questao = BancoQuestoes(
            questao=questao,
            alternativa_a=alternativa_a,
            alternativa_b=alternativa_b,
            alternativa_c=alternativa_c,
            alternativa_d=alternativa_d,
            alternativa_e=alternativa_e,
            questao_correta=questao_correta,
            disciplina_id=disciplina_id,
            assunto=assunto,
            ano_escolar_id=ano_escolar_id,
            mes_id=datetime.now().month
        )
        
        try:
            db.session.add(nova_questao)
            db.session.commit()
            flash('Questão cadastrada com sucesso!', 'success')
            return redirect(url_for('listar_questoes'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao cadastrar questão: {str(e)}', 'error')
    
    disciplinas = Disciplinas.query.all()
    Ano_escolar = Ano_escolar.query.all()
    return render_template('questoes/cadastrar.html', disciplinas=disciplinas, Ano_escolar=Ano_escolar)

@app.route('/listar_questoes')
@login_required
def listar_questoes():
    if current_user.tipo_usuario_id not in [1, 3]:  # Apenas admin e professores
        flash('Acesso não autorizado', 'error')
        return redirect(url_for('home'))
    
    questoes = BancoQuestoes.query.all()
    return render_template('questoes/listar.html', questoes=questoes)

@app.route('/gerar_simulado', methods=['GET', 'POST'])
@login_required
def gerar_simulado():
    if current_user.tipo_usuario_id not in [1, 3]:  # Apenas admin e professores
        flash('Acesso não autorizado', 'error')
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        ano_escolar_id = request.form.get('ano_escolar_id')
        disciplina_id = request.form.get('disciplina_id')
        
        # Criar simulado
        simulado = SimuladosGeradosProfessor(
            professor_id=current_user.id,
            disciplina_id=disciplina_id,
            ano_escolar_id=ano_escolar_id,
            mes_id=datetime.now().month,
            status='gerado'
        )
        
        try:
            db.session.add(simulado)
            db.session.flush()
            
            # Buscar questões disponíveis
            questoes = BancoQuestoes.query.filter_by(
                ano_escolar_id=ano_escolar_id,
                disciplina_id=disciplina_id
            ).all()
            
            # Adicionar questões ao simulado
            for questao in questoes:
                simulado_questao = SimuladoQuestoesProfessor(
                    simulado_id=simulado.id,
                    questao_id=questao.id
                )
                db.session.add(simulado_questao)
            
            db.session.commit()
            flash('Simulado gerado com sucesso!', 'success')
            return redirect(url_for('listar_simulados'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao gerar simulado: {str(e)}', 'error')
    
    Ano_escolar = Ano_escolar.query.all()
    disciplinas = Disciplinas.query.all()
    return render_template('simulados/gerar.html', Ano_escolar=Ano_escolar, disciplinas=disciplinas)

@app.route('/listar_simulados')
@login_required
def listar_simulados():
    if current_user.tipo_usuario_id not in [1, 3]:  # Apenas admin e professores
        flash('Acesso não autorizado', 'error')
        return redirect(url_for('home'))
    
    if current_user.tipo_usuario_id == 1:
        simulados = SimuladosGeradosProfessor.query.all()
    else:
        simulados = SimuladosGeradosProfessor.query.filter_by(professor_id=current_user.id).all()
    
    return render_template('simulados/listar.html', simulados=simulados)

@app.route('/enviar_simulado/<int:simulado_id>', methods=['GET', 'POST'])
@login_required
def enviar_simulado(simulado_id):
    if current_user.tipo_usuario_id not in [1, 3]:  # Apenas admin e professores
        flash('Acesso não autorizado', 'error')
        return redirect(url_for('home'))
    
    simulado = SimuladosGeradosProfessor.query.get_or_404(simulado_id)
    
    if request.method == 'POST':
        turma_id = request.form.get('turma_id')
        data_limite = request.form.get('data_limite')
        
        # Criar registro de simulado enviado
        simulado_enviado = SimuladosEnviados(
            simulado_id=simulado_id,
            turma_id=turma_id,
            data_limite=datetime.strptime(data_limite, '%Y-%m-%d'),
            status='enviado'
        )
        
        try:
            db.session.add(simulado_enviado)
            db.session.flush()
            
            # Buscar alunos da turma
            alunos = Usuarios.query.filter_by(
                turma_id=turma_id,
                tipo_usuario_id=5  # Tipo aluno
            ).all()
            
            # Criar registros para cada aluno
            for aluno in alunos:
                aluno_simulado = AlunoSimulado(
                    aluno_id=aluno.id,
                    simulado_id=simulado_enviado.id,
                    status='pendente'
                )
                db.session.add(aluno_simulado)
            
            simulado.status = 'enviado'
            db.session.commit()
            flash('Simulado enviado com sucesso!', 'success')
            return redirect(url_for('listar_simulados'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao enviar simulado: {str(e)}', 'error')
    
    # Buscar turmas do professor
    turmas = (Turmas.query
             .join(ProfessorTurmaEscola)
             .filter(ProfessorTurmaEscola.professor_id == current_user.id)
             .filter(Turmas.ano_escolar_id == simulado.ano_escolar_id)
             .all())
    
    return render_template('simulados/enviar.html', simulado=simulado, turmas=turmas)

@app.route('/responder_simulado/<int:simulado_id>', methods=['GET', 'POST'])
@login_required
def responder_simulado(simulado_id):
    if current_user.tipo_usuario_id not in [5, 6]:  # Apenas alunos
        flash('Acesso não autorizado', 'error')
        return redirect(url_for('home'))
    
    aluno_simulado = AlunoSimulado.query.filter_by(
        aluno_id=current_user.id,
        simulado_id=simulado_id
    ).first_or_404()
    
    if aluno_simulado.status == 'respondido':
        flash('Este simulado já foi respondido', 'warning')
        return redirect(url_for('portal_alunos'))
    
    simulado_enviado = SimuladosEnviados.query.get_or_404(simulado_id)
    if simulado_enviado.data_limite and datetime.now() > simulado_enviado.data_limite:
        flash('O prazo para responder este simulado já expirou', 'warning')
        return redirect(url_for('portal_alunos'))
    
    simulado = SimuladosGeradosProfessor.query.get_or_404(simulado_enviado.simulado_id)
    questoes = (BancoQuestoes.query
               .join(SimuladoQuestoesProfessor)
               .filter(SimuladoQuestoesProfessor.simulado_id == simulado.id)
               .all())
    
    if request.method == 'POST':
        respostas = {}
        respostas_corretas = {}
        total_questoes = len(questoes)
        acertos = 0
        
        for questao in questoes:
            resposta = request.form.get(f'questao_{questao.id}')
            respostas[str(questao.id)] = resposta
            respostas_corretas[str(questao.id)] = questao.questao_correta
            if resposta == questao.questao_correta:
                acertos += 1
        
        desempenho = (acertos / total_questoes) * 100
        
        # Registrar desempenho
        desempenho_registro = DesempenhoSimulado(
            aluno_id=current_user.id,
            simulado_id=simulado_id,
            escola_id=current_user.escola_id,
            ano_escolar_id=current_user.ano_escolar_id,
            codigo_ibge=current_user.codigo_ibge,
            respostas_aluno=json.dumps(respostas),
            respostas_corretas=json.dumps(respostas_corretas),
            desempenho=desempenho,
            turma_id=current_user.turma_id
        )
        
        try:
            db.session.add(desempenho_registro)
            aluno_simulado.status = 'respondido'
            aluno_simulado.data_resposta = datetime.now()
            db.session.commit()
            flash('Simulado respondido com sucesso!', 'success')
            return redirect(url_for('portal_alunos'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao registrar respostas: {str(e)}', 'error')
    
    return render_template('simulados/responder.html', simulado=simulado, questoes=questoes)

@app.route('/relatorio_desempenho')
@login_required
def relatorio_desempenho():
    if current_user.tipo_usuario_id not in [1, 2, 3, 4]:  # Todos exceto alunos
        flash('Acesso não autorizado', 'error')
        return redirect(url_for('home'))
    
    # Filtros
    escola_id = request.args.get('escola_id', type=int)
    ano_escolar_id = request.args.get('ano_escolar_id', type=int)
    turma_id = request.args.get('turma_id', type=int)
    
    query = DesempenhoSimulado.query
    
    if escola_id:
        query = query.filter_by(escola_id=escola_id)
    if ano_escolar_id:
        query = query.filter_by(ano_escolar_id=ano_escolar_id)
    if turma_id:
        query = query.filter_by(turma_id=turma_id)
    
    desempenhos = query.all()
    
    # Calcular médias
    media_geral = sum(d.desempenho for d in desempenhos) / len(desempenhos) if desempenhos else 0
    
    # Agrupar por escola
    desempenhos_por_escola = {}
    for d in desempenhos:
        if d.escola_id not in desempenhos_por_escola:
            desempenhos_por_escola[d.escola_id] = []
        desempenhos_por_escola[d.escola_id].append(d.desempenho)
    
    medias_por_escola = {
        escola_id: sum(desempenhos) / len(desempenhos)
        for escola_id, desempenhos in desempenhos_por_escola.items()
    }
    
    escolas = Escolas.query.all()
    Ano_escolar = Ano_escolar.query.all()
    turmas = Turmas.query.all() if escola_id else []
    
    return render_template(
        'relatorios/desempenho.html',
        desempenhos=desempenhos,
        media_geral=media_geral,
        medias_por_escola=medias_por_escola,
        escolas=escolas,
        Ano_escolar=Ano_escolar,
        turmas=turmas
    )
