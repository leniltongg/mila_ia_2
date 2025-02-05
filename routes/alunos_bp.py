from flask import Blueprint, render_template, request, jsonify, current_app, redirect, url_for, flash, send_file, make_response, g
from flask_login import login_required, current_user
from openai import OpenAI
import sqlite3
import json
import os
from dotenv import load_dotenv
import re

# Criar o blueprint
alunos_bp = Blueprint('alunos_bp', __name__, url_prefix='/alunos')

load_dotenv()
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect('educacional.db')
        g.db.row_factory = sqlite3.Row
    return g.db

@alunos_bp.route('/portal')
@login_required
def portal_alunos():
    if current_user.tipo_usuario_id != 4:  # Apenas alunos podem acessar
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))

    db = get_db()
    cursor = db.cursor()

    # Buscar simulados pendentes do aluno, ordenando por status (Pendente primeiro) e data
    cursor.execute("""
        SELECT sg.id, d.nome AS disciplina_nome, sg.mes_id, 
               strftime('%d-%m-%Y', date(sg.data_envio)) as data_envio,
               CASE 
                   WHEN EXISTS (
                       SELECT 1 
                       FROM desempenho_simulado ds 
                       WHERE ds.simulado_id = sg.id 
                       AND ds.aluno_id = ?
                   ) THEN 'Respondido'
                   ELSE 'Pendente'
               END as status
        FROM simulados_gerados sg
        JOIN disciplinas d ON sg.disciplina_id = d.id
        WHERE sg.serie_id = ?
        ORDER BY 
            CASE 
                WHEN EXISTS (
                    SELECT 1 
                    FROM desempenho_simulado ds 
                    WHERE ds.simulado_id = sg.id 
                    AND ds.aluno_id = ?
                ) THEN 1 
                ELSE 0 
            END,
            sg.data_envio DESC
    """, (current_user.id, current_user.serie_id, current_user.id))
    simulados = cursor.fetchall()

    # Lista de meses para exibição
    meses = [
        (1, "Janeiro"), (2, "Fevereiro"), (3, "Março"),
        (4, "Abril"), (5, "Maio"), (6, "Junho"),
        (7, "Julho"), (8, "Agosto"), (9, "Setembro"),
        (10, "Outubro"), (11, "Novembro"), (12, "Dezembro")
    ]

    return render_template('alunos/portal_alunos.html', simulados=simulados, meses=meses)

@alunos_bp.route('/tutor-virtual')
@login_required
def tutor_virtual():
    return render_template('alunos/tutor_virtual.html')

@alunos_bp.route('/resolver-exercicios')
@login_required
def resolver_exercicios():
    return render_template('alunos/area_aluno.html')

@alunos_bp.route('/criar-resumo')
@login_required
def criar_resumo():
    return render_template('alunos/criar_resumo.html')

@alunos_bp.route('/gerar_resumo', methods=['POST'])
@login_required
def gerar_resumo():
    try:
        data = request.get_json()
        print("Dados recebidos:", data)  # Log para debug
        
        disciplina = data.get('disciplina')
        nivel = data.get('nivel')
        tipo = data.get('tipo')
        conteudo = data.get('conteudo')
        incluir_exemplos = data.get('incluir_exemplos', False)
        destacar_importante = data.get('destacar_importante', False)
        
        # Criar o prompt base
        base_prompt = f"""
        Você é um professor especialista em {disciplina} do nível {nivel}.
        Crie um resumo do seguinte conteúdo, seguindo estas diretrizes:
        
        1. Tipo de resumo: {tipo}
        2. {'Inclua exemplos práticos e aplicações.' if incluir_exemplos else ''}
        3. {'Destaque os conceitos mais importantes.' if destacar_importante else ''}
        4. Mantenha uma linguagem clara e adequada ao nível {nivel}
        5. Organize o conteúdo de forma lógica e estruturada
        
        Conteúdo para resumir:
        {conteudo}
        """
        
        # Ajustar o prompt baseado no tipo de resumo
        if tipo == "topicos":
            base_prompt += "\nOrganize o resumo em tópicos e subtópicos claros."
        elif tipo == "mapa_conceitual":
            base_prompt += "\nCrie um mapa conceitual textual mostrando as relações entre os conceitos."
        elif tipo == "esquema":
            base_prompt += "\nCrie um esquema de estudo com palavras-chave e conexões."
            
        print("Enviando prompt para GPT-4:", base_prompt)  # Log para debug
            
        # Gerar resumo usando GPT-4
        completion = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Você é um professor especialista em criar resumos educacionais."},
                {"role": "user", "content": base_prompt}
            ]
        )
        
        resumo = completion.choices[0].message.content
        print("Resumo gerado:", resumo)  # Log para debug
        
        # Formatar o resumo com HTML
        resumo_formatado = formatar_resumo_html(resumo, tipo)
        
        return jsonify({
            'success': True,
            'resumo': resumo_formatado
        })
        
    except Exception as e:
        print(f"Erro ao gerar resumo: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Erro ao gerar resumo: {str(e)}'
        }), 500

def formatar_resumo_html(resumo, tipo):
    """Formata o resumo com HTML e estilos apropriados."""
    if tipo == "topicos":
        # Detectar e formatar listas
        resumo = re.sub(r'^\s*[\-\*]\s+(.+)$', r'<li>\1</li>', resumo, flags=re.MULTILINE)
        resumo = re.sub(r'((?:<li>.*?</li>\s*)+)', r'<ul class="mb-3">\1</ul>', resumo)
        
    elif tipo == "mapa_conceitual":
        # Adicionar classes para estilização de mapa conceitual
        resumo = f'<div class="mapa-conceitual">{resumo}</div>'
        
    elif tipo == "esquema":
        # Formatar esquemas com indentação e cores
        resumo = f'<div class="esquema-estudo">{resumo}</div>'
    
    # Formatar títulos
    resumo = re.sub(r'^(.*?):$', r'<h4 class="mt-4 mb-3">\1</h4>', resumo, flags=re.MULTILINE)
    
    # Destacar palavras-chave
    resumo = re.sub(r'\*\*(.*?)\*\*', r'<strong class="text-primary">\1</strong>', resumo)
    
    # Formatar parágrafos
    resumo = re.sub(r'\n\n+', '</p><p class="mb-3">', resumo)
    resumo = f'<p class="mb-3">{resumo}</p>'
    
    return resumo

@alunos_bp.route('/download_resumo', methods=['POST'])
@login_required
def download_resumo():
    try:
        data = request.get_json()
        html_content = data.get('resumo', '')
        
        # Criar uma página HTML completa
        html_page = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 2cm; }}
                h4 {{ color: #2c3e50; margin-top: 1.5em; }}
                .mapa-conceitual {{ margin: 1em 0; }}
                .esquema-estudo {{ margin: 1em 0; }}
                strong {{ color: #3498db; }}
                ul {{ margin-left: 1em; }}
                li {{ margin: 0.5em 0; }}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """
        
        # Criar resposta com o HTML
        response = make_response(html_page)
        response.headers['Content-Type'] = 'text/html'
        response.headers['Content-Disposition'] = 'attachment; filename=resumo.html'
        
        return response
        
    except Exception as e:
        print(f"Erro ao gerar HTML: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Erro ao gerar arquivo do resumo.'
        }), 500

@alunos_bp.route('/criar-flashcards')
@login_required
def criar_flashcards():
    return render_template('alunos/criar_flashcards.html')

@alunos_bp.route('/fazer-quiz')
@login_required
def fazer_quiz():
    return render_template('alunos/fazer_quiz.html')

@alunos_bp.route('/treinar-apresentacao')
@login_required
def treinar_apresentacao():
    return render_template('alunos/treinar_apresentacao.html')

@alunos_bp.route('/simular-entrevista')
@login_required
def simular_entrevista():
    return render_template('alunos/simular_entrevista.html')

@alunos_bp.route('/preparar-redacao')
@login_required
def preparar_redacao():
    return render_template('alunos/preparar_redacao.html')

@alunos_bp.route('/analisar_redacao', methods=['POST'])
@login_required
def analisar_redacao():
    try:
        data = request.get_json()
        tipo = data.get('tipo', '')
        tema = data.get('tema', '')
        redacao = data.get('redacao', '')
        analise_estrutura = data.get('analise_estrutura', True)
        analise_argumentos = data.get('analise_argumentos', True)
        analise_gramatical = data.get('analise_gramatical', True)
        sugestoes_melhoria = data.get('sugestoes_melhoria', True)

        if not tipo or not tema or not redacao.strip():
            return jsonify({
                'success': False,
                'error': 'Por favor, preencha todos os campos.'
            }), 400

        # Prompt para o OpenAI
        prompt = f"""Analise a redação abaixo e forneça uma avaliação detalhada.

Tipo de redação: {tipo}
Tema: {tema}

Redação:
{redacao}

Por favor, forneça:
1. Nota final (0-1000)
2. Notas por competência (0-200 cada):
   - Competência 1: Domínio da norma culta
   - Competência 2: Compreensão do tema e tipo textual
   - Competência 3: Organização e argumentação
   - Competência 4: Mecanismos linguísticos e coesão
   - Competência 5: Proposta de intervenção

3. Análises solicitadas:
{f'- Análise estrutural: avalie a estrutura do texto, parágrafos e desenvolvimento.' if analise_estrutura else ''}
{f'- Análise argumentativa: avalie a qualidade e desenvolvimento dos argumentos.' if analise_argumentos else ''}
{f'- Análise gramatical: aponte erros gramaticais e sugestões de correção.' if analise_gramatical else ''}
{f'- Sugestões de melhoria: forneça sugestões específicas para melhorar o texto.' if sugestoes_melhoria else ''}

Responda em formato JSON com os seguintes campos:
- nota_final: número
- comp1: número
- comp2: número
- comp3: número
- comp4: número
- comp5: número
- estrutura: string com análise estrutural em HTML (use <p>, <ul>, <li>, etc.)
- argumentacao: string com análise argumentativa em HTML
- gramatica: string com análise gramatical em HTML
- sugestoes: string com sugestões de melhoria em HTML"""

        # Fazer a chamada para o OpenAI
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-16k",
            messages=[
                {"role": "system", "content": "Você é um professor especializado em redação, com vasta experiência em correção de textos do ENEM e vestibulares."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=4000,
            temperature=0.7
        )

        # Processar resposta
        try:
            content = response.choices[0].message.content.strip()
            # Remover possíveis textos antes ou depois do JSON
            content = content[content.find('{'):content.rfind('}')+1]
            analise = json.loads(content)
            return jsonify({
                'success': True,
                'analise': analise
            })
        except Exception as e:
            print(f"Erro ao processar resposta: {str(e)}")
            print(f"Resposta recebida: {response.choices[0].message.content}")
            return jsonify({
                'success': False,
                'error': 'Erro ao processar a análise da redação.'
            }), 500

    except Exception as e:
        print(f"Erro ao analisar redação: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Erro ao analisar a redação.'
        }), 500

@alunos_bp.route('/download_analise_redacao', methods=['POST'])
@login_required
def download_analise_redacao():
    try:
        data = request.get_json()
        tipo = data.get('tipo', '')
        tema = data.get('tema', '')
        redacao = data.get('redacao', '')
        analise = data.get('analise', {})

        # Criar HTML bonito
        html = f"""
        <!DOCTYPE html>
        <html lang="pt-BR">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Análise da Redação</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <style>
                body {{ 
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    margin: 0;
                    padding: 20px;
                    background-color: #f8f9fa;
                }}
                .container {{
                    max-width: 800px;
                    margin: 0 auto;
                    background-color: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .header {{
                    background-color: #f8f9fa;
                    padding: 20px;
                    border-radius: 8px;
                    margin-bottom: 30px;
                }}
                .competencia {{
                    margin-bottom: 10px;
                }}
                .progress {{
                    height: 25px;
                }}
                .analise-section {{
                    margin-bottom: 30px;
                    padding: 20px;
                    border: 1px solid #dee2e6;
                    border-radius: 8px;
                }}
                .nota-final {{
                    font-size: 2em;
                    font-weight: bold;
                    color: #0d6efd;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1 class="text-center mb-4">Análise da Redação</h1>
                
                <div class="header">
                    <div class="row">
                        <div class="col-md-6">
                            <h5>Tipo de Redação</h5>
                            <p class="lead">{tipo.upper()}</p>
                        </div>
                        <div class="col-md-6">
                            <h5>Tema</h5>
                            <p class="lead">{tema}</p>
                        </div>
                    </div>
                </div>

                <div class="analise-section text-center">
                    <h4>Nota Final</h4>
                    <span class="nota-final">{analise.get('nota_final', 0)}</span>
                    <div class="mt-4">
                        <h5>Competências</h5>
                        <div class="competencia">
                            <label>1. Domínio da norma culta</label>
                            <div class="progress">
                                <div class="progress-bar" role="progressbar" 
                                     style="width: {(analise.get('comp1', 0)/200)*100}%" 
                                     aria-valuenow="{analise.get('comp1', 0)}" 
                                     aria-valuemin="0" aria-valuemax="200">
                                    {analise.get('comp1', 0)}
                                </div>
                            </div>
                        </div>
                        <div class="competencia">
                            <label>2. Compreensão do tema</label>
                            <div class="progress">
                                <div class="progress-bar bg-success" role="progressbar" 
                                     style="width: {(analise.get('comp2', 0)/200)*100}%" 
                                     aria-valuenow="{analise.get('comp2', 0)}" 
                                     aria-valuemin="0" aria-valuemax="200">
                                    {analise.get('comp2', 0)}
                                </div>
                            </div>
                        </div>
                        <div class="competencia">
                            <label>3. Organização e argumentação</label>
                            <div class="progress">
                                <div class="progress-bar bg-info" role="progressbar" 
                                     style="width: {(analise.get('comp3', 0)/200)*100}%" 
                                     aria-valuenow="{analise.get('comp3', 0)}" 
                                     aria-valuemin="0" aria-valuemax="200">
                                    {analise.get('comp3', 0)}
                                </div>
                            </div>
                        </div>
                        <div class="competencia">
                            <label>4. Mecanismos linguísticos</label>
                            <div class="progress">
                                <div class="progress-bar bg-warning" role="progressbar" 
                                     style="width: {(analise.get('comp4', 0)/200)*100}%" 
                                     aria-valuenow="{analise.get('comp4', 0)}" 
                                     aria-valuemin="0" aria-valuemax="200">
                                    {analise.get('comp4', 0)}
                                </div>
                            </div>
                        </div>
                        <div class="competencia">
                            <label>5. Proposta de intervenção</label>
                            <div class="progress">
                                <div class="progress-bar bg-danger" role="progressbar" 
                                     style="width: {(analise.get('comp5', 0)/200)*100}%" 
                                     aria-valuenow="{analise.get('comp5', 0)}" 
                                     aria-valuemin="0" aria-valuemax="200">
                                    {analise.get('comp5', 0)}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="analise-section">
                    <h4>Sua Redação</h4>
                    <div class="redacao-text mt-3">
                        <pre class="p-3 bg-light" style="white-space: pre-wrap;">{redacao}</pre>
                    </div>
                </div>

                <div class="analise-section">
                    <h4>Análise Estrutural</h4>
                    <div class="mt-3">
                        {analise.get('estrutura', '')}
                    </div>
                </div>

                <div class="analise-section">
                    <h4>Análise Argumentativa</h4>
                    <div class="mt-3">
                        {analise.get('argumentacao', '')}
                    </div>
                </div>

                <div class="analise-section">
                    <h4>Análise Gramatical</h4>
                    <div class="mt-3">
                        {analise.get('gramatica', '')}
                    </div>
                </div>

                <div class="analise-section">
                    <h4>Sugestões de Melhoria</h4>
                    <div class="mt-3">
                        {analise.get('sugestoes', '')}
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        return send_file(
            data=html.encode('utf-8'),
            mimetype='text/html',
            as_attachment=True,
            attachment_filename='analise_redacao.html'
        )

    except Exception as e:
        print(f"Erro ao gerar HTML da análise: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Erro ao gerar o arquivo da análise.'
        }), 500

# Rotas para processamento de dados via AJAX
@alunos_bp.route('/processar-chat', methods=['POST'])
@login_required
def processar_chat():
    try:
        data = request.get_json()
        message = data.get('message', '')
        if not message:
            return jsonify({"error": "Mensagem não pode estar vazia"}), 400

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": """Você é um tutor virtual educacional, especializado em ajudar estudantes com suas dúvidas acadêmicas. 
                Siga estas diretrizes rigorosamente:
                1. NUNCA forneça respostas diretas para questões de múltipla escolha ou qualquer outro tipo de questão
                2. Em vez disso, guie o aluno através do raciocínio necessário para chegar à resposta
                3. Explique os conceitos fundamentais relacionados à questão
                4. Faça perguntas que levem o aluno a refletir sobre o problema
                5. Use analogias e exemplos práticos para facilitar o entendimento
                6. Incentive o aluno a chegar à sua própria conclusão
                7. Se o aluno insistir em pedir a resposta, reforce a importância do processo de aprendizagem

                Seu objetivo é desenvolver o pensamento crítico e a autonomia do aluno, não apenas fornecer respostas."""},
                {"role": "user", "content": message}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        return jsonify({
            "success": True, 
            "response": response.choices[0].message.content
        })
            
    except Exception as e:
        print(f"Erro ao processar chat: {str(e)}")
        return jsonify({
            "success": False, 
            "error": "Erro ao processar sua mensagem"
        }), 500

@alunos_bp.route('/gerar-quiz', methods=['POST'])
@login_required
def gerar_quiz():
    try:
        data = request.get_json()
        conteudo = data.get('conteudo', '')
        disciplina = data.get('disciplina', '')
        nivel = data.get('nivel', '')
        quantidade = data.get('quantidade', 10)

        if not conteudo or not disciplina or not nivel:
            return jsonify({
                'success': False,
                'error': 'Por favor, preencha todos os campos.'
            }), 400

        # Gerar quiz usando OpenAI
        prompt = f"""Com base no conteúdo fornecido, crie {quantidade} questões de múltipla escolha sobre {disciplina} para nível {nivel}.
        
        Formato da resposta deve ser um array JSON com objetos contendo:
        - pergunta: texto da questão
        - alternativas: array com 4 opções
        - resposta: índice da alternativa correta (0-3)
        - explicacao: explicação detalhada da resposta correta
        
        Conteúdo: {conteudo}"""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um professor especializado em criar questões educativas e desafiadoras. Responda APENAS com o JSON solicitado, sem nenhum texto adicional."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.7
        )

        # Processar resposta
        try:
            content = response.choices[0].message.content.strip()
            # Remover possíveis textos antes ou depois do JSON
            content = content[content.find('['):content.rfind(']')+1]
            quiz = json.loads(content)
            return jsonify({
                'success': True,
                'quiz': quiz
            })
        except Exception as e:
            print(f"Erro ao processar resposta: {str(e)}")
            print(f"Resposta recebida: {response.choices[0].message.content}")
            return jsonify({
                'success': False,
                'error': 'Erro ao processar as questões geradas.'
            }), 500

    except Exception as e:
        print(f"Erro ao gerar quiz: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Erro ao gerar o quiz.'
        }), 500

@alunos_bp.route('/avaliar-apresentacao', methods=['POST'])
@login_required
def avaliar_apresentacao():
    data = request.get_json()
    apresentacao = data.get('apresentacao', '')
    # Avaliar apresentação
    feedback = "Feedback da apresentação"  # Placeholder
    return jsonify({'success': True, 'feedback': feedback})

@alunos_bp.route('/avaliar-entrevista', methods=['POST'])
@login_required
def avaliar_entrevista():
    data = request.get_json()
    resposta = data.get('resposta', '')
    # Avaliar resposta da entrevista
    feedback = "Feedback da entrevista"  # Placeholder
    return jsonify({'success': True, 'feedback': feedback})

@alunos_bp.route('/avaliar-redacao', methods=['POST'])
@login_required
def avaliar_redacao():
    data = request.get_json()
    redacao = data.get('redacao', '')
    # Avaliar redação
    feedback = "Feedback da redação"  # Placeholder
    return jsonify({'success': True, 'feedback': feedback})

@alunos_bp.route('/processar-entrevista', methods=['POST'])
@login_required
def processar_entrevista():
    try:
        data = request.get_json()
        tipo = data.get('tipo')
        area = data.get('area')
        nivel = data.get('nivel')
        mensagem = data.get('mensagem')
        historico = data.get('historico', [])
        
        # Se não houver histórico, é o início da entrevista
        if not historico:
            # Criar o primeiro prompt baseado no tipo e área
            prompts = {
                'vestibular': f'Você é um avaliador de vestibular da área de {area}. Faça uma entrevista simulada focando em conhecimentos específicos e motivação do candidato.',
                'estagio': f'Você é um recrutador de uma empresa de {area}. Faça uma entrevista de estágio avaliando habilidades técnicas e comportamentais.',
                'apresentacao': f'Você é um professor avaliador de {area}. Faça perguntas sobre a apresentação do trabalho, metodologia e resultados.',
                'debate': f'Você é um mediador de debate sobre {area}. Proponha tópicos polêmicos e peça argumentação fundamentada.'
            }
            
            # Ajustar dificuldade baseado no nível
            niveis = {
                'facil': 'Mantenha as perguntas simples e diretas, dando dicas quando necessário.',
                'medio': 'Faça perguntas moderadamente complexas, equilibrando teoria e prática.',
                'dificil': 'Faça perguntas desafiadoras que exigem pensamento crítico e conhecimento aprofundado.'
            }
            
            system_prompt = f"{prompts.get(tipo, prompts['vestibular'])} {niveis.get(nivel, niveis['medio'])}"
            
            # Primeira mensagem do entrevistador
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "assistant", "content": "Olá! Vou conduzir sua entrevista hoje. Para começar, poderia se apresentar brevemente?"}
            ]
            
            return jsonify({
                'success': True,
                'mensagem': messages[1]["content"],
                'feedback': None
            })
        
        # Se já existe histórico, continuar a conversa
        messages = [
            {"role": "system", "content": "Você é um entrevistador experiente. Mantenha o foco no tema e faça perguntas relevantes. Dê feedback construtivo após cada resposta do candidato, mas mantenha a conversa fluindo naturalmente."}
        ]
        
        # Adicionar histórico de mensagens
        for msg in historico:
            role = "assistant" if msg["isEntrevistador"] else "user"
            messages.append({"role": role, "content": msg["texto"]})
        
        # Adicionar mensagem atual do usuário
        messages.append({"role": "user", "content": mensagem})
        
        # Gerar resposta do entrevistador e feedback
        completion = client.chat.completions.create(
            model="gpt-4",
            messages=messages + [
                {"role": "system", "content": "Agora forneça duas respostas: 1) Sua próxima pergunta ou comentário como entrevistador 2) Um breve feedback construtivo sobre a última resposta do candidato. Separe as duas respostas com [FEEDBACK]"}
            ]
        )
        
        resposta = completion.choices[0].message.content
        
        # Separar resposta e feedback
        partes = resposta.split('[FEEDBACK]')
        mensagem_entrevistador = partes[0].strip()
        feedback = partes[1].strip() if len(partes) > 1 else None
        
        return jsonify({
            'success': True,
            'mensagem': mensagem_entrevistador,
            'feedback': feedback
        })
        
    except Exception as e:
        print(f"Erro na entrevista: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Erro ao processar a entrevista.'
        }), 500

@alunos_bp.route('/finalizar-entrevista', methods=['POST'])
@login_required
def finalizar_entrevista():
    try:
        data = request.get_json()
        historico = data.get('historico', [])
        tipo = data.get('tipo')
        area = data.get('area')
        
        if not historico:
            raise ValueError("Histórico vazio")
        
        # Criar mensagens para avaliação
        messages = [
            {"role": "system", "content": "Você é um avaliador experiente. Analise a entrevista e forneça uma avaliação detalhada."},
        ]
        
        # Adicionar contexto
        messages.append({
            "role": "user", 
            "content": f"Esta foi uma entrevista de {tipo} na área de {area}. Analise o desempenho do candidato no seguinte histórico:\n\n" + 
                      "\n".join([f"{'Entrevistador' if msg['isEntrevistador'] else 'Candidato'}: {msg['texto']}" for msg in historico])
        })
        
        # Solicitar avaliação estruturada
        messages.append({
            "role": "system",
            "content": """Forneça uma avaliação estruturada com os seguintes elementos, separados por [SECTION]:
            1. Pontuação (0-10) para: Clareza, Conteúdo e Objetividade
            2. Feedback geral sobre o desempenho
            3. Lista de pontos fortes (máximo 3)
            4. Lista de pontos a melhorar (máximo 3)"""
        })
        
        # Gerar avaliação
        completion = client.chat.completions.create(
            model="gpt-4",
            messages=messages
        )
        
        # Processar resultado
        sections = completion.choices[0].message.content.split('[SECTION]')
        
        # Extrair pontuações
        pontuacoes = sections[1].strip().split(',')
        clareza = int(pontuacoes[0].strip())
        conteudo = int(pontuacoes[1].strip())
        objetividade = int(pontuacoes[2].strip())
        
        return jsonify({
            'success': True,
            'resultado': {
                'pontuacao': {
                    'clareza': clareza,
                    'conteudo': conteudo,
                    'objetividade': objetividade
                },
                'feedback_geral': sections[2].strip(),
                'pontos_fortes': [p.strip() for p in sections[3].strip().split('\n')],
                'pontos_melhorar': [p.strip() for p in sections[4].strip().split('\n')]
            }
        })
        
    except Exception as e:
        print(f"Erro ao finalizar entrevista: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Erro ao gerar avaliação da entrevista.'
        }), 500
