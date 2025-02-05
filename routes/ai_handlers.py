from flask import jsonify, request
import openai
from flask_login import login_required

def process_chat_message(message):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um tutor virtual educacional, especializado em ajudar estudantes com suas dúvidas acadêmicas. Seja sempre prestativo, paciente e encoraje o pensamento crítico."},
                {"role": "user", "content": message}
            ],
            max_tokens=500,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Erro ao processar mensagem com OpenAI: {str(e)}")
        return "Desculpe, ocorreu um erro ao processar sua mensagem. Por favor, tente novamente."

def setup_ai_routes(app):
    @app.route("/alunos/processar-chat", methods=["POST"])
    @login_required
    def processar_chat():
        try:
            data = request.get_json()
            message = data.get('message', '')
            if not message:
                return jsonify({"error": "Mensagem não pode estar vazia"}), 400

            response = process_chat_message(message)
            return jsonify({"success": True, "response": response})
            
        except Exception as e:
            print(f"Erro ao processar chat: {str(e)}")
            return jsonify({
                "success": False, 
                "error": "Erro ao processar sua mensagem"
            }), 500
