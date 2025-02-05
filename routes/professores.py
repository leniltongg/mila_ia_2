from flask import Blueprint, render_template, request, jsonify, g, redirect, url_for
from flask_login import login_required, current_user
import sqlite3

professores_bp = Blueprint('professores', __name__)

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect('mila.db')
        g.db.row_factory = sqlite3.Row
    return g.db

@professores_bp.route('/')
@login_required
def index():
    return redirect(url_for('professores.portal'))

@professores_bp.route('/portal')
@login_required
def portal():
    db = get_db()
    cursor = db.cursor()
    
    # Buscar turmas do professor
    cursor.execute("""
        SELECT t.id, t.nome, d.nome as disciplina, s.nome as serie
        FROM turmas t
        JOIN disciplinas d ON t.disciplina_id = d.id
        JOIN series s ON t.serie_id = s.id
        WHERE t.professor_id = ?
        ORDER BY t.nome
    """, (current_user.id,))
    turmas = cursor.fetchall()
    
    return render_template('portal_professores.html', turmas=turmas)

@professores_bp.route('/ver_alunos/<int:turma_id>')
@login_required
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
