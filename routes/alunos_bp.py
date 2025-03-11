from flask import Blueprint, render_template, g, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from extensions import db
from models import Usuarios, SimuladosEnviados, AlunoSimulado, SimuladosGeradosProfessor, SimuladoQuestoesProfessor, BancoQuestoes, SimuladosGerados, Disciplinas, MESES, DesempenhoSimulado
from sqlalchemy import func, case, exists, and_
import openai
import json
import os
from dotenv import load_dotenv
import re
from weasyprint import HTML as WeasyHTML

# Carregar variáveis de ambiente
load_dotenv()

# Criar o blueprint
alunos_bp = Blueprint('alunos_bp', __name__, url_prefix='/alunos')

@alunos_bp.route('/portal')
@login_required
def portal_alunos():
    if current_user.tipo_usuario_id not in [4, 6]:  # Apenas alunos podem acessar
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))

    # Buscar simulados pendentes do aluno usando SQLAlchemy
    simulados = db.session.query(
        SimuladosGerados.id,
        Disciplinas.nome.label('disciplina_nome'),
        SimuladosGerados.mes_id,
        func.date_format(SimuladosGerados.data_envio, '%d-%m-%Y').label('data_envio'),
        case(
            (exists().where(
                and_(
                    DesempenhoSimulado.simulado_id == SimuladosGerados.id,
                    DesempenhoSimulado.aluno_id == current_user.id
                )
            ), 'Respondido'),
            else_='Pendente'
        ).label('status')
    ).join(
        Disciplinas, Disciplinas.id == SimuladosGerados.disciplina_id
    ).filter(
        SimuladosGerados.ano_escolar_id == current_user.ano_escolar_id
    ).order_by(
        case(
            (exists().where(
                and_(
                    DesempenhoSimulado.simulado_id == SimuladosGerados.id,
                    DesempenhoSimulado.aluno_id == current_user.id
                )
            ), 1),
            else_=0
        ),
        SimuladosGerados.data_envio.desc()
    ).all()

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
    return render_template('alunos/tutor-virtual.html')

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
        
        # Extrair dados do request
        disciplina = data.get('disciplina')
        nivel = data.get('nivel')
        tipo = data.get('tipo', 'completo')
        conteudo = data.get('conteudo')
        incluir_exemplos = data.get('incluir_exemplos', True)
        destacar_importante = data.get('destacar_importante', True)
        
        # Validar dados
        if not all([disciplina, nivel, conteudo]):
            return jsonify({'success': False, 'error': 'Dados incompletos'})
            
        # Construir o prompt baseado no tipo de resumo
        prompt_base = f"""Você é um professor especialista em {disciplina} para o nível {nivel}. 
        Crie um resumo conciso e objetivo do seguinte conteúdo, focando apenas nos pontos mais importantes. 
        O resumo deve ter no máximo 30% do tamanho do texto original.
        """
        
        if tipo == 'completo':
            prompt = prompt_base + """
            Estruture o resumo em parágrafos curtos e objetivos.
            Use linguagem clara e direta.
            Destaque os conceitos principais em negrito.
            """
        elif tipo == 'topicos':
            prompt = prompt_base + """
            Crie uma lista com os tópicos principais.
            Cada tópico deve ter no máximo 2 linhas.
            Use marcadores para organizar os tópicos.
            """
        elif tipo == 'mapa_conceitual':
            prompt = prompt_base + """
            Crie um mapa conceitual em formato de texto.
            Use → para indicar relações entre conceitos.
            Organize os conceitos de forma hierárquica.
            """
        else:  # esquema
            prompt = prompt_base + """
            Crie um esquema resumido com títulos e subtítulos.
            Use numeração para organizar os tópicos.
            Mantenha cada item do esquema curto e direto.
            """
            
        if incluir_exemplos:
            prompt += "\nIncluir 1-2 exemplos breves para ilustrar os conceitos mais importantes."
            
        if destacar_importante:
            prompt += "\nDestaque em negrito (**texto**) os conceitos mais importantes."
            
        prompt += f"\n\nConteúdo para resumir:\n{conteudo}"
        
        # Fazer a chamada para a API
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um assistente especializado em criar resumos educacionais concisos e objetivos."},
                {"role": "user", "content": prompt}
            ]
        )
        
        # Extrair e formatar o resumo
        resumo = response.choices[0].message.content
        resumo_formatado = formatar_resumo_html(resumo, tipo)
        
        return jsonify({
            'success': True,
            'resumo': resumo_formatado
        })
        
    except Exception as e:
        print(f"Erro ao gerar resumo: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Erro ao gerar o resumo. Por favor, tente novamente.'
        })

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

@alunos_bp.route('/gerar_flashcards', methods=['POST'])
@login_required
def gerar_flashcards():
    try:
        data = request.get_json()
        print("Dados recebidos:", data)
        
        # Extrair dados do request
        disciplina = data.get('disciplina')
        quantidade = int(data.get('quantidade', 10))
        conteudo = data.get('conteudo')
        incluir_imagens = data.get('incluir_imagens', False)
        incluir_dicas = data.get('incluir_dicas', True)
        
        print(f"Disciplina: {disciplina}")
        print(f"Quantidade: {quantidade}")
        print(f"Tamanho do conteúdo: {len(conteudo) if conteudo else 0}")
        
        # Validar dados
        if not all([disciplina, conteudo]):
            return jsonify({'success': False, 'error': 'Dados incompletos'})
            
        # Limitar quantidade
        quantidade = min(max(quantidade, 5), 20)
            
        # Construir o prompt
        prompt = f"""Você é um professor especialista em {disciplina}. 
        Crie {quantidade} flashcards de estudo baseados no seguinte conteúdo.
        Para cada flashcard, forneça:
        1. Uma pergunta clara e específica
        2. Uma resposta concisa e direta
        3. {'Uma dica de memorização' if incluir_dicas else ''}
        
        Regras:
        - As perguntas devem ser diretas e testar conceitos importantes
        - As respostas devem ser curtas (máximo 3 linhas)
        - {'As dicas devem ajudar a memorizar o conceito' if incluir_dicas else ''}
        - Use uma linguagem apropriada para estudo
        - Foque nos conceitos mais importantes
        
        Retorne os flashcards no seguinte formato JSON:
        {{
            "flashcards": [
                {{
                    "pergunta": "Pergunta 1?",
                    "resposta": "Resposta 1",
                    "dica": "Dica 1"
                }},
                // ... mais flashcards
            ]
        }}
        
        Conteúdo: {conteudo}"""

        print("Prompt construído")
        
        # Fazer a chamada para a API
        try:
            print("Chamando API OpenAI...")
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Você é um assistente especializado em criar flashcards educacionais."},
                    {"role": "user", "content": prompt}
                ]
            )
            print("Resposta da API recebida")
            
        except Exception as api_error:
            print(f"Erro na chamada da API: {str(api_error)}")
            raise api_error
        
        # Extrair e processar os flashcards
        try:
            content = response.choices[0].message.content
            print("Conteúdo recebido:", content)
            
            # Encontrar o JSON na resposta
            json_str = content[content.find('{'):content.rfind('}')+1]
            print("JSON extraído:", json_str)
            
            flashcards = json.loads(json_str)
            print("JSON decodificado com sucesso")
            
            return jsonify({
                'success': True,
                'flashcards': flashcards['flashcards']
            })
            
        except json.JSONDecodeError as e:
            print(f"Erro ao decodificar JSON: {str(e)}")
            print(f"Conteúdo recebido: {content}")
            return jsonify({
                'success': False,
                'error': 'Erro ao processar os flashcards. Por favor, tente novamente.'
            })
        
    except Exception as e:
        print(f"Erro ao gerar flashcards: {str(e)}")
        import traceback
        print("Traceback completo:", traceback.format_exc())
        return jsonify({
            'success': False,
            'error': 'Erro ao gerar os flashcards. Por favor, tente novamente.'
        })

@alunos_bp.route('/download_flashcards', methods=['POST'])
@login_required
def download_flashcards():
    try:
        data = request.get_json()
        flashcards = data.get('flashcards', '')
        disciplina = data.get('disciplina', 'geral')
        
        # Criar HTML para PDF
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Flashcards - {disciplina}</title>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .flashcard {{
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    padding: 15px;
                    margin: 10px 0;
                    page-break-inside: avoid;
                }}
                .pergunta {{ 
                    font-weight: bold;
                    color: #2c3e50;
                    margin-bottom: 10px;
                }}
                .resposta {{
                    color: #34495e;
                    margin-bottom: 8px;
                }}
                .dica {{
                    color: #7f8c8d;
                    font-style: italic;
                    font-size: 0.9em;
                }}
            </style>
        </head>
        <body>
            <h1>Flashcards - {disciplina}</h1>
            {flashcards}
        </body>
        </html>
        """

        # Criar PDF
        pdf = WeasyHTML(string=html).write_pdf()
        
        # Retornar o PDF
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=Flashcards_{disciplina}.pdf'
        
        return response
        
    except Exception as e:
        print(f"Erro ao gerar PDF: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Erro ao gerar o PDF. Por favor, tente novamente.'
        }), 500

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
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo-16k",
            messages=[
                {"role": "system", "content": "Você é um professor especializado em redação, com vasta experiência em correção de textos do ENEM e vestibulares."},
                {"role": "user", "content": prompt}
            ]
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

@alunos_bp.route('/processar-chat', methods=['POST'])
@login_required
def processar_chat():
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({"success": False, "error": "Mensagem não fornecida"}), 400
            
        message = data['message']
        if not message.strip():
            return jsonify({"success": False, "error": "Mensagem vazia"}), 400

        try:
            response = openai.chat.completions.create(
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
                ]
            )
            
            return jsonify({
                "success": True, 
                "response": response.choices[0].message.content
            })
        except Exception as e:
            print(f"Erro ao processar chat: {str(e)}")
            return jsonify({
                "success": False, 
                "error": str(e)
            }), 500

    except Exception as e:
        print(f"Erro ao processar chat: {str(e)}")
        return jsonify({
            "success": False, 
            "error": str(e)
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

        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um professor especializado em criar questões educativas e desafiadoras. Responda APENAS com o JSON solicitado, sem nenhum texto adicional."},
                {"role": "user", "content": prompt}
            ]
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
    try:
        data = request.get_json()
        tipo = data.get('tipo', '')
        duracao = data.get('duracao', '')
        conteudo = data.get('conteudo', '')
        incluir_slides = data.get('incluir_slides', True)
        incluir_tecnicas = data.get('incluir_tecnicas', True)

        if not tipo or not conteudo.strip():
            return jsonify({
                'success': False,
                'error': 'Por favor, preencha todos os campos obrigatórios.'
            }), 400

        # Prompt para o OpenAI
        prompt = f"""Analise a apresentação abaixo e forneça feedback detalhado.

Tipo de apresentação: {tipo}
Duração prevista: {duracao} minutos
Conteúdo:
{conteudo}

Por favor, forneça feedback estruturado em 4 áreas:

1. Estrutura:
- Análise da organização do conteúdo
- Sugestões para melhorar a estrutura
- Pontos fortes e fracos

2. Oratória:
- Dicas de comunicação verbal
- Sugestões de linguagem corporal
- Técnicas para engajar a audiência

3. Slides (se aplicável):
- Sugestões para organização visual
- Dicas de design e formatação
- Melhores práticas para apresentações

4. Gestão do Tempo:
- Como distribuir o conteúdo no tempo disponível
- Pontos que podem precisar de mais ou menos tempo
- Dicas para controle do tempo

Forneça o feedback em formato HTML com tags <p> para parágrafos."""

        # Chamar a API do OpenAI
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Você é um especialista em apresentações e oratória, com vasta experiência em avaliar e orientar alunos."},
                {"role": "user", "content": prompt}
            ]
        )

        # Processar a resposta
        feedback_text = response.choices[0].message.content

        # Dividir o feedback em seções
        sections = feedback_text.split('\n\n')
        feedback = {
            'estrutura': sections[0] if len(sections) > 0 else '',
            'oratoria': sections[1] if len(sections) > 1 else '',
            'slides': sections[2] if len(sections) > 2 else '',
            'tempo': sections[3] if len(sections) > 3 else ''
        }

        return jsonify({
            'success': True,
            'feedback': feedback
        })

    except Exception as e:
        print(f"Erro ao avaliar apresentação: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Erro ao avaliar a apresentação.'
        }), 500

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
        completion = openai.chat.completions.create(
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
        completion = openai.chat.completions.create(
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

@alunos_bp.route('/feedback_apresentacao', methods=['POST'])
@login_required
def feedback_apresentacao():
    try:
        data = request.get_json()
        
        # Extrair dados do request
        tipo = data.get('tipo')
        duracao = int(data.get('duracao', 15))
        conteudo = data.get('conteudo')
        incluir_slides = data.get('incluir_slides', True)
        incluir_tecnicas = data.get('incluir_tecnicas', True)
        
        # Validar dados
        if not all([tipo, conteudo]):
            return jsonify({'success': False, 'error': 'Dados incompletos'})
            
        # Construir o prompt
        prompt = f"""Você é um professor especialista em apresentações e oratória.
        Analise o conteúdo desta apresentação de {tipo} com duração prevista de {duracao} minutos.
        
        Forneça um feedback detalhado nos seguintes aspectos:
        
        1. Estrutura da Apresentação:
        - Analise a organização do conteúdo
        - Verifique se há introdução, desenvolvimento e conclusão claros
        - Sugira melhorias na estrutura
        
        2. Técnicas de Oratória:
        - Dê dicas de como apresentar cada parte
        - Sugira técnicas para manter a atenção do público
        - Indique momentos para pausas e ênfases
        
        3. Sugestões para Slides:
        - Recomende como dividir o conteúdo em slides
        - Sugira elementos visuais que podem ser usados
        - Dê dicas de design e formatação
        
        4. Gestão do Tempo:
        - Analise se o conteúdo é adequado para {duracao} minutos
        - Sugira quanto tempo dedicar a cada parte
        - Indique se algo deve ser removido ou expandido
        
        Retorne o feedback no seguinte formato JSON:
        {{
            "estrutura": "Feedback sobre estrutura em HTML",
            "oratoria": "Feedback sobre oratória em HTML",
            "slides": "Feedback sobre slides em HTML",
            "tempo": "Feedback sobre gestão do tempo em HTML"
        }}
        
        Use tags HTML para formatar o texto (h4, p, ul, li, etc).
        Seja específico e dê exemplos práticos.
        
        Conteúdo da apresentação:
        {conteudo}"""
        
        # Fazer a chamada para a API
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um assistente especializado em dar feedback sobre apresentações."},
                {"role": "user", "content": prompt}
            ]
        )
        
        # Extrair e processar o feedback
        try:
            content = response.choices[0].message.content
            # Encontrar o JSON na resposta
            json_str = content[content.find('{'):content.rfind('}')+1]
            feedback = json.loads(json_str)
            
            return jsonify({
                'success': True,
                'feedback': feedback
            })
            
        except json.JSONDecodeError as e:
            print(f"Erro ao decodificar JSON: {str(e)}")
            print(f"Conteúdo recebido: {content}")
            return jsonify({
                'success': False,
                'error': 'Erro ao processar o feedback. Por favor, tente novamente.'
            })
        
    except Exception as e:
        print(f"Erro ao gerar feedback: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Erro ao gerar o feedback. Por favor, tente novamente.'
        })

@alunos_bp.route('/download_feedback', methods=['POST'])
@login_required
def download_feedback():
    try:
        data = request.get_json()
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #2c3e50; }}
                h2 {{ color: #34495e; margin-top: 20px; }}
                .section {{ margin-bottom: 30px; }}
            </style>
        </head>
        <body>
            <h1>Feedback da Apresentação</h1>
            <div class="section">
                <h2>Estrutura</h2>
                {data['estrutura']}
            </div>
            <div class="section">
                <h2>Oratória</h2>
                {data['oratoria']}
            </div>
            <div class="section">
                <h2>Slides</h2>
                {data['slides']}
            </div>
            <div class="section">
                <h2>Gestão do Tempo</h2>
                {data['tempo']}
            </div>
        </body>
        </html>
        """
        
        # Criar PDF
        pdf = WeasyHTML(string=html).write_pdf()
        
        # Criar resposta com o PDF
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = 'attachment; filename=feedback_apresentacao.pdf'
        
        return response
        
    except Exception as e:
        print(f"Erro ao gerar PDF: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Erro ao gerar PDF do feedback.'
        }), 500

@alunos_bp.route('/simulados')
@login_required
def simulados():
    try:
        # Primeiro, pegar a série do aluno logado
        ano_escolar_id = current_user.ano_escolar_id

        # Buscar apenas simulados da série do aluno
        simulados = db.session.query(
            SimuladosGerados.id,
            SimuladosGerados.mes_id,
            SimuladosGerados.status,
            func.date_format(SimuladosGerados.data_envio, '%d-%m-%Y').label('data_envio'),
            Disciplinas.nome.label('disciplina_nome'),
            MESES.nome.label('mes_nome')
        ).join(
            Disciplinas, Disciplinas.id == SimuladosGerados.disciplina_id
        ).join(
            MESES, MESES.id == SimuladosGerados.mes_id
        ).filter(
            SimuladosGerados.ano_escolar_id == ano_escolar_id
        ).filter(
            SimuladosGerados.status == 'enviado'
        ).order_by(
            SimuladosGerados.data_envio.desc()
        ).all()

        # Buscar simulados já respondidos pelo aluno (tipo_usuario_id = 5 para secretaria)
        desempenho_simulado = db.session.query(
            DesempenhoSimulado.simulado_id,
            DesempenhoSimulado.desempenho
        ).filter(
            DesempenhoSimulado.aluno_id == current_user.id
        ).filter(
            DesempenhoSimulado.tipo_usuario_id == 5
        ).all()
        
        # Criar um dicionário com os simulados respondidos
        desempenho_simulado = {row[0]: {'desempenho': row[1]} for row in desempenho_simulado}
        
        return render_template('alunos/simulados.html', 
                             simulados=simulados,
                             desempenho_simulado=desempenho_simulado)
    except Exception as e:
        print(f"Erro ao buscar simulados: {str(e)}")
        flash('Erro ao carregar simulados', 'danger')
        return redirect(url_for('alunos_bp.portal_alunos'))

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
