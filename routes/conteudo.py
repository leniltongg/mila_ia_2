from flask import Blueprint, render_template, request, jsonify, send_file
from flask_login import login_required, current_user
from openai import OpenAI
import os
from dotenv import load_dotenv
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import tempfile
import json
import graphviz
import re
from app import db
from models import Disciplinas, Ano_escolar, SimuladosGeradosProfessor

# Criar o blueprint
conteudo_bp = Blueprint('conteudo', __name__)

# Carregar variáveis de ambiente
load_dotenv()

# Debug: imprimir variáveis de ambiente
print("DEBUG - Variáveis de ambiente:")
print(f"OPENAI_API_KEY exists: {'OPENAI_API_KEY' in os.environ}")
print(f"OPENAI_API_KEY value: {os.getenv('OPENAI_API_KEY')[:10]}...")  # Mostrar só os primeiros 10 caracteres por segurança

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def gerar_mapa_mental(tema, conteudo):
    """Gera um mapa mental usando graphviz."""
    # Criar um novo grafo
    dot = graphviz.Digraph(comment='Mapa Mental')
    
    # Configurar o estilo do grafo
    dot.attr(rankdir='LR')  # Layout da esquerda para direita
    dot.attr('node', shape='box', style='rounded,filled', fillcolor='white', fontname='Arial', fontsize='12')
    dot.attr('edge', color='#666666')
    
    # Função para limpar o texto e gerar um ID único
    def clean_text(text):
        return re.sub(r'[^a-zA-Z0-9]', '', text)
    
    # Adicionar nó central
    dot.node('central', tema, shape='box', style='rounded,filled', fillcolor='#E8F4F9', fontsize='14')
    
    # Extrair tópicos e subtópicos do conteúdo
    linhas = conteudo.split('\n')
    topico_atual = None
    cor_atual = '#ffffff'
    cores = ['#F0F9E8', '#F4E8F9', '#F9E8E8', '#E8F4F9', '#F9F4E8']
    cor_index = 0
    
    for linha in linhas:
        linha = linha.strip()
        if not linha:
            continue
            
        if not linha.startswith('  '):  # Tópico principal
            topico_atual = linha
            cor_atual = cores[cor_index % len(cores)]
            cor_index += 1
            
            # Adicionar nó do tópico
            node_id = clean_text(topico_atual)
            dot.node(node_id, topico_atual, fillcolor=cor_atual)
            dot.edge('central', node_id)
        else:  # Subtópico
            if topico_atual:
                subtopico = linha.strip()
                sub_node_id = clean_text(subtopico)
                dot.node(sub_node_id, subtopico, fillcolor=cor_atual)
                dot.edge(clean_text(topico_atual), sub_node_id)
    
    # Gerar o arquivo de imagem
    output_path = os.path.join(tempfile.gettempdir(), 'mapa_mental')
    dot.render(output_path, format='png', cleanup=True)
    return output_path + '.png'

@conteudo_bp.route('/criar_plano_aula', methods=['GET', 'POST'])
@login_required
def criar_plano_aula():
    # Verificar se é professor
    if current_user.tipo_usuario_id not in [3, 6]:  # 3 = Professor
        return jsonify({'error': 'Acesso não autorizado'}), 403

    # Buscar disciplinas e séries que o professor tem acesso
    disciplinas_series = (
        db.session.query(
            Disciplinas.id.label('disciplina_id'),
            Disciplinas.nome.label('disciplina_nome'),
            Ano_escolar.id.label('Ano_escolar_id'),
            Ano_escolar.nome.label('Ano_escolar_nome')
        )
        .join(SimuladosGeradosProfessor, SimuladosGeradosProfessor.disciplina_id == Disciplinas.id)
        .join(Ano_escolar, SimuladosGeradosProfessor.Ano_escolar_id == Ano_escolar.id)
        .filter(SimuladosGeradosProfessor.professor_id == current_user.id)
        .distinct()
        .order_by(Disciplinas.nome, Ano_escolar.nome)
        .all()
    )

    if request.method == 'GET':
        # Organizar dados para o template
        disciplinas = {}
        anos_escolares = set()
        
        for item in disciplinas_series:
            disciplinas[item.disciplina_id] = item.disciplina_nome  # Usar ID como chave
            anos_escolares.add((item.Ano_escolar_id, item.Ano_escolar_nome))
        
        return render_template('conteudo/plano_aula.html', 
                             disciplinas=[(id, nome) for id, nome in disciplinas.items()],  # Enviar tuplas (id, nome)
                             Ano_escolar=sorted(anos_escolares, key=lambda x: x[1]))

    elif request.method == 'POST':
        disciplina_id = request.form.get('disciplina')
        ano_escolar_id = request.form.get('Ano_escolar')
        tema = request.form.get('tema')
        duracao = request.form.get('duracao')
        
        # Verificar se o professor tem acesso à disciplina e série selecionadas
        tem_acesso = False
        disciplina_nome = None
        for item in disciplinas_series:
            if str(item.disciplina_id) == disciplina_id and str(item.Ano_escolar_id) == ano_escolar_id:
                tem_acesso = True
                disciplina_nome = item.disciplina_nome
                break
        
        if not tem_acesso:
            return jsonify({
                'success': False,
                'error': 'Você não tem acesso a esta combinação de disciplina e série'
            }), 403
        
        prompt = f"""Crie um plano de aula detalhado para:
        Disciplina: {disciplina_nome}
        Ano Escolar: {ano_escolar_id}º ano
        Tema: {tema}
        Duração: {duracao} minutos

        O plano deve incluir:
        1. Objetivos de aprendizagem
        2. Materiais necessários
        3. Introdução (motivação)
        4. Desenvolvimento
        5. Atividades práticas
        6. Avaliação
        7. Tarefa de casa
        8. Referências"""

        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Você é um professor experiente especializado em criar planos de aula efetivos e envolventes."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            plano_aula = response.choices[0].message.content
            return jsonify({'success': True, 'plano_aula': plano_aula})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})

@conteudo_bp.route('/criar_resumo', methods=['GET', 'POST'])
@login_required
def criar_resumo():
    if request.method == 'POST':
        disciplina = request.form.get('disciplina')
        Ano_escolar = request.form.get('Ano_escolar')
        tema = request.form.get('tema')
        tipo_resumo = request.form.get('tipo_resumo')
        nivel_detalhe = request.form.get('nivel_detalhe')
        gerar_imagem = request.form.get('gerar_imagem') == 'on'
        imagem_desc = request.form.get('imagem_desc')
        
        prompt = f"""Crie um resumo educacional para:
        Disciplina: {disciplina}
        Ano Escolar: {Ano_escolar}
        Tema: {tema}
        Tipo de Resumo: {tipo_resumo}
        Nível de Detalhamento: {nivel_detalhe}"""

        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Você é um professor experiente especializado em criar resumos educacionais claros e efetivos."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            resumo = response.choices[0].message.content
            
            # Se solicitado, gerar uma imagem
            imagem_url = None
            if gerar_imagem and imagem_desc:
                try:
                    image_response = client.images.generate(
                        prompt=imagem_desc,
                        n=1,
                        size="512x512"
                    )
                    imagem_url = image_response.data[0].url
                except Exception as e:
                    print(f"Erro ao gerar imagem: {str(e)}")
            
            # Gerar mapa mental
            try:
                mapa_mental_path = gerar_mapa_mental(tema, resumo)
            except Exception as e:
                print(f"Erro ao gerar mapa mental: {str(e)}")
                mapa_mental_path = None
            
            return jsonify({
                'success': True, 
                'resumo': resumo,
                'imagem_url': imagem_url if imagem_url else None,
                'mapa_mental': mapa_mental_path if mapa_mental_path else None
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})

    return render_template('conteudo/resumo.html')

@conteudo_bp.route('/criar_exercicios', methods=['GET', 'POST'])
@login_required
def criar_exercicios():
    if request.method == 'POST':
        disciplina = request.form.get('disciplina')
        Ano_escolar = request.form.get('Ano_escolar')
        tema = request.form.get('tema')
        num_questoes = request.form.get('num_questoes')
        nivel = request.form.get('nivel')
        tipo_questoes = request.form.get('tipo_questoes')
        
        prompt = f"""Crie uma lista de exercícios para:
        Disciplina: {disciplina}
        Ano Escolar: {Ano_escolar}
        Tema: {tema}
        Número de Questões: {num_questoes}
        Nível: {nivel}
        Tipo de Questões: {tipo_questoes}

        Para cada questão, forneça:
        1. Enunciado
        2. Alternativas (se for múltipla escolha)
        3. Resposta correta
        4. Explicação da resposta

        Formate cada questão assim:
        Questão X:
        Enunciado: [enunciado aqui]
        Alternativas (se aplicável):
        a) [alternativa]
        b) [alternativa]
        c) [alternativa]
        d) [alternativa]
        e) [alternativa]
        Resposta: [letra ou resposta]
        Explicação: [explicação detalhada]"""

        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Você é um professor experiente especializado em criar exercícios educacionais efetivos e envolventes."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            exercicios = response.choices[0].message.content
            return jsonify({'success': True, 'exercicios': exercicios})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})

    return render_template('conteudo/exercicios.html')

@conteudo_bp.route('/criar_material_complementar', methods=['GET', 'POST'])
@login_required
def criar_material_complementar():
    if request.method == 'POST':
        disciplina = request.form.get('disciplina')
        Ano_escolar = request.form.get('Ano_escolar')
        tema = request.form.get('tema')
        tipo_material = request.form.get('tipo_material')
        nivel_detalhe = request.form.get('nivel_detalhe')
        
        prompt = f"""Crie um material complementar para:
        Disciplina: {disciplina}
        Ano Escolar: {Ano_escolar}
        Tema: {tema}
        Tipo de Material: {tipo_material}
        Nível de Detalhamento: {nivel_detalhe}

        O material deve incluir:
        1. Introdução ao tema
        2. Desenvolvimento detalhado
        3. Exemplos práticos
        4. Curiosidades
        5. Sugestões de aprofundamento
        6. Referências"""

        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Você é um professor experiente especializado em criar materiais complementares educacionais."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            material = response.choices[0].message.content
            return jsonify({'success': True, 'material': material})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})

    return render_template('conteudo/material_complementar.html')

@conteudo_bp.route('/download_resumo', methods=['POST'])
@login_required
def download_resumo():
    try:
        data = request.get_json()
        resumo_text = data.get('resumo')
        
        # Criar arquivo PDF temporário
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            # Configurar o documento PDF
            doc = SimpleDocTemplate(temp_file.name, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []
            
            # Adicionar título
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                spaceAfter=30
            )
            story.append(Paragraph("Resumo", title_style))
            story.append(Spacer(1, 12))
            
            # Adicionar conteúdo
            text_style = ParagraphStyle(
                'CustomBody',
                parent=styles['Normal'],
                fontSize=12,
                leading=14,
                spaceAfter=12
            )
            
            # Dividir o texto em parágrafos
            paragraphs = resumo_text.split('\n')
            for paragraph in paragraphs:
                if paragraph.strip():
                    story.append(Paragraph(paragraph, text_style))
                    story.append(Spacer(1, 6))
            
            # Gerar o PDF
            doc.build(story)
            
            # Retornar o arquivo
            return send_file(
                temp_file.name,
                as_attachment=True,
                download_name='resumo.pdf',
                mimetype='application/pdf'
            )
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@conteudo_bp.route('/download_exercicios', methods=['POST'])
@login_required
def download_exercicios():
    try:
        data = request.get_json()
        versao_aluno = data.get('versao_aluno', '')
        versao_professor = data.get('versao_professor', '')
        
        # Criar arquivo PDF temporário
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            # Configurar o documento PDF
            doc = SimpleDocTemplate(temp_file.name, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []
            
            # Estilo para títulos
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                spaceAfter=30
            )
            
            # Estilo para texto
            text_style = ParagraphStyle(
                'CustomBody',
                parent=styles['Normal'],
                fontSize=12,
                leading=14,
                spaceAfter=12
            )
            
            # Versão do Aluno
            story.append(Paragraph("Exercícios - Versão do Aluno", title_style))
            story.append(Spacer(1, 12))
            story.append(Paragraph(versao_aluno, text_style))
            story.append(PageBreak())
            
            # Versão do Professor
            story.append(Paragraph("Exercícios - Versão do Professor (com gabarito)", title_style))
            story.append(Spacer(1, 12))
            story.append(Paragraph(versao_professor, text_style))
            
            # Gerar o PDF
            doc.build(story)
            
            # Retornar o arquivo
            return send_file(
                temp_file.name,
                as_attachment=True,
                download_name='exercicios.pdf',
                mimetype='application/pdf'
            )
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@conteudo_bp.route('/download_material', methods=['POST'])
@login_required
def download_material():
    try:
        data = request.get_json()
        material = data.get('material', '')
        
        # Criar arquivo PDF temporário
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            # Configurar o documento PDF
            doc = SimpleDocTemplate(temp_file.name, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []
            
            # Estilo para títulos
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                spaceAfter=30
            )
            
            # Estilo para texto
            text_style = ParagraphStyle(
                'CustomBody',
                parent=styles['Normal'],
                fontSize=12,
                leading=14,
                spaceAfter=12
            )
            
            # Adicionar título
            story.append(Paragraph("Material Complementar", title_style))
            story.append(Spacer(1, 12))
            
            # Adicionar conteúdo
            story.append(Paragraph(material, text_style))
            
            # Gerar o PDF
            doc.build(story)
            
            # Retornar o arquivo
            return send_file(
                temp_file.name,
                as_attachment=True,
                download_name='material_complementar.pdf',
                mimetype='application/pdf'
            )
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
