from flask import Blueprint, render_template, request, current_app
from flask_login import login_required, current_user
from database import get_db

professores_bp = Blueprint('professores_bp', __name__)

@professores_bp.route('/portal_professores', methods=['GET'])
@login_required
def portal_professores():
    db = get_db()
    cursor = db.cursor()

    # Recuperar as turmas vinculadas ao professor na tabela professor_turma_escola
    cursor.execute("""
        SELECT DISTINCT t.id, se.nome AS serie, t.turma, e.nome_da_escola AS escola
        FROM professor_turma_escola pte
        JOIN turmas t ON pte.turma_id = t.id
        JOIN series se ON t.serie_id = se.id
        JOIN escolas e ON t.escola_id = e.id
        WHERE pte.professor_id = ?
    """, (current_user.id,))
    turmas = cursor.fetchall()

    print("Turmas vinculadas:", turmas)

    # Recuperar filtros
    assunto_filtro = request.args.get('assunto', '').strip()
    avaliacao_filtro = request.args.get('avaliacao', '').strip()
    page = int(request.args.get('page', 1))
    per_page = 10
    offset = (page - 1) * per_page

    # Base da consulta para simulados gerados
    query = """
        SELECT 
            s.id, 
            a.nome AS assunto,
            d.nome AS disciplina, 
            se.nome AS serie,
            t.id AS turma_id,
            t.turma AS letra_turma,
            s.data_envio,
            s.status
        FROM simulados_gerados s
        JOIN series se ON s.serie_id = se.id
        JOIN disciplinas d ON s.disciplina_id = d.id
        JOIN professor_turma_escola pte ON pte.professor_id = ?
        JOIN turmas t ON t.serie_id = s.serie_id AND t.id = pte.turma_id
        LEFT JOIN assuntos a ON a.disciplina_id = s.disciplina_id AND a.professor_id = pte.professor_id
    """
    filters = []
    params = [current_user.id]

    # Aplicar filtros, se disponíveis
    if assunto_filtro:
        filters.append("a.nome LIKE ?")
        params.append(f"%{assunto_filtro}%")
    if avaliacao_filtro:
        filters.append("s.status = ?")
        params.append(avaliacao_filtro)

    if filters:
        query += " AND " + " AND ".join(filters)

    # Adicionar paginação
    query += " ORDER BY s.id DESC LIMIT ? OFFSET ?"
    params.extend([per_page, offset])

    print("Consulta SQL final:", query)
    print("Parâmetros da consulta:", params)

    # Executar a consulta para simulados
    cursor.execute(query, params)
    simulados = cursor.fetchall()
    print("Simulados retornados antes do tratamento:", simulados)

    # Tratar valores retornados e ajustar a saída
    simulados_tratados = [
        (
            simulado[0],  # s.id
            simulado[1],  # a.nome (assunto)
            simulado[2],  # d.nome (disciplina)
            simulado[3],  # se.nome (serie)
            simulado[4],  # t.id (turma_id)
            simulado[5],  # t.turma (letra da turma)
            simulado[6],  # s.data_envio
            simulado[7]   # s.status
        )
        for simulado in simulados
    ]
    print("Simulados tratados:", simulados_tratados)

    # Contar total de simulados para paginação
    count_query = """
        SELECT COUNT(*)
        FROM simulados_gerados s
        JOIN series se ON s.serie_id = se.id
        JOIN disciplinas d ON s.disciplina_id = d.id
        JOIN professor_turma_escola pte ON pte.professor_id = ?
        JOIN turmas t ON t.serie_id = s.serie_id AND t.id = pte.turma_id
        LEFT JOIN assuntos a ON a.disciplina_id = s.disciplina_id AND a.professor_id = pte.professor_id
    """
    if filters:
        count_query += " AND " + " AND ".join(filters)

    print("Consulta SQL de contagem:", count_query)
    print("Parâmetros da contagem:", params[:-2])

    cursor.execute(count_query, params[:-2])
    total_simulados = cursor.fetchone()[0]
    total_pages = (total_simulados + per_page - 1) // per_page

    return render_template(
        "portal_professores.html",
        title="Portal dos Professores",
        turmas=turmas,
        simulados=simulados_tratados,
        total_pages=total_pages,
        current_page=page,
        assunto_filtro=assunto_filtro,
        avaliacao_filtro=avaliacao_filtro
    )
