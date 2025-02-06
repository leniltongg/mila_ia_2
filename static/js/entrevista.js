let entrevista = {
    timer: null,
    inicio: null,
    historico: [],
    finalizada: false
};

document.addEventListener('DOMContentLoaded', function() {
    console.log('Inicializando script de entrevista...');
    
    const form = document.getElementById('entrevista-form');
    const entrevistaArea = document.getElementById('entrevista-area');
    const loadingDiv = document.getElementById('loading');
    const chatCard = document.getElementById('chat-card');
    const configCard = document.getElementById('config-card');
    const respostaForm = document.getElementById('resposta-form');

    console.log('Form encontrado:', form);
    console.log('Entrevista area encontrada:', entrevistaArea);
    console.log('Loading div encontrada:', loadingDiv);
    console.log('Chat card encontrado:', chatCard);
    console.log('Config card encontrado:', configCard);
    console.log('Resposta form encontrado:', respostaForm);

    if (!form) {
        console.error('Formulário não encontrado!');
        return;
    }

    // Garantir que o formulário não seja enviado normalmente
    form.onsubmit = function(e) {
        e.preventDefault();
        return false;
    };

    // Adicionar o evento de clique ao botão de submit
    const submitButton = form.querySelector('button[type="submit"]');
    submitButton.addEventListener('click', async function(e) {
        e.preventDefault();
        console.log('Botão de submit clicado!');
        
        const tipo = document.getElementById('tipo').value;
        const area = document.getElementById('area').value;
        const nivel = document.getElementById('nivel').value;
        const feedbackDetalhado = document.getElementById('feedback_detalhado').checked;
        const gravarSessao = document.getElementById('gravar_sessao').checked;

        console.log('Dados do formulário:', {
            tipo,
            area,
            nivel,
            feedbackDetalhado,
            gravarSessao
        });

        if (!tipo || !area) {
            alert('Por favor, preencha todos os campos obrigatórios.');
            return;
        }

        // Mostrar loading
        configCard.style.display = 'none';
        entrevistaArea.style.display = 'block';
        loadingDiv.style.display = 'block';
        chatCard.style.display = 'none';

        try {
            console.log('Iniciando entrevista...');
            // Iniciar entrevista
            entrevista.inicio = new Date();
            entrevista.timer = setInterval(atualizarTempo, 1000);
            entrevista.historico = [];
            entrevista.finalizada = false;

            // Primeira mensagem do entrevistador
            const response = await fetch('/alunos/processar-entrevista', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    tipo: tipo,
                    area: area,
                    nivel: nivel,
                    feedback_detalhado: feedbackDetalhado,
                    historico: []
                })
            });

            console.log('Resposta recebida:', response);
            const data = await response.json();
            console.log('Dados processados:', data);

            if (data.success) {
                adicionarMensagem(data.mensagem, false);
            } else {
                throw new Error('Erro ao iniciar entrevista');
            }
        } catch (error) {
            console.error('Erro detalhado:', error);
            alert('Erro ao iniciar entrevista');
            novaEntrevista();
        } finally {
            loadingDiv.style.display = 'none';
            chatCard.style.display = 'block';
        }
    });

    if (!respostaForm) {
        console.error('Formulário de resposta não encontrado!');
        return;
    }

    respostaForm.onsubmit = function(e) {
        e.preventDefault();
        return false;
    };

    const respostaButton = respostaForm.querySelector('button[type="submit"]');
    respostaButton.addEventListener('click', async function(e) {
        e.preventDefault();
        console.log('Botão de resposta clicado!');
        
        const input = document.getElementById('resposta-input');
        const resposta = input.value.trim();
        
        if (resposta && !entrevista.finalizada) {
            input.value = '';
            adicionarMensagem(resposta, true);
            
            try {
                console.log('Enviando resposta...');
                const response = await fetch('/alunos/processar-entrevista', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        mensagem: resposta,
                        historico: entrevista.historico.map(msg => ({
                            texto: msg.mensagem,
                            isEntrevistador: !msg.isUser
                        }))
                    })
                });

                console.log('Resposta recebida:', response);
                const data = await response.json();
                console.log('Dados processados:', data);

                if (data.success) {
                    if (data.feedback) {
                        mostrarFeedback(data.feedback);
                    }
                    
                    if (data.finalizar) {
                        finalizarEntrevista(data.resultado);
                    } else {
                        adicionarMensagem(data.mensagem, false);
                    }
                } else {
                    throw new Error('Erro ao processar resposta');
                }
            } catch (error) {
                console.error('Erro detalhado:', error);
                alert('Erro ao processar sua resposta');
            }
        }
    });
});

function adicionarMensagem(mensagem, isUser) {
    const chatArea = document.getElementById('chat-area');
    const messageDiv = document.createElement('div');
    messageDiv.className = `d-flex ${isUser ? 'justify-content-end' : 'justify-content-start'} mb-3`;
    
    messageDiv.innerHTML = `
        <div class="message p-3 rounded ${isUser ? 'bg-warning text-dark' : 'bg-light'}" 
             style="max-width: 75%;">
            ${mensagem}
        </div>
    `;
    
    chatArea.appendChild(messageDiv);
    chatArea.scrollTop = chatArea.scrollHeight;
    
    // Adicionar ao histórico
    entrevista.historico.push({
        mensagem: mensagem,
        isUser: isUser
    });
}

function mostrarFeedback(feedback) {
    const feedbackArea = document.getElementById('feedback-area');
    feedbackArea.innerHTML = `
        <div class="alert alert-light border">
            <h6 class="alert-heading">Feedback da Resposta</h6>
            <p class="mb-0">${feedback}</p>
        </div>
    `;
    feedbackArea.style.display = 'block';
}

function finalizarEntrevista(resultado) {
    entrevista.finalizada = true;
    clearInterval(entrevista.timer);
    
    document.getElementById('chat-card').style.display = 'none';
    document.getElementById('resultado-card').style.display = 'block';
    
    // Preencher pontuações
    document.getElementById('pontos-clareza').textContent = `${resultado.clareza}/10`;
    document.getElementById('pontos-conteudo').textContent = `${resultado.conteudo}/10`;
    document.getElementById('pontos-objetividade').textContent = `${resultado.objetividade}/10`;
    
    // Preencher feedback geral
    document.getElementById('feedback-geral').innerHTML = resultado.feedback_geral;
    
    // Preencher pontos fortes e a melhorar
    const pontosFortes = document.getElementById('pontos-fortes');
    const pontosMelhorar = document.getElementById('pontos-melhorar');
    
    pontosFortes.innerHTML = resultado.pontos_fortes.map(ponto => 
        `<li><i class="fas fa-check-circle text-success me-2"></i>${ponto}</li>`
    ).join('');
    
    pontosMelhorar.innerHTML = resultado.pontos_melhorar.map(ponto => 
        `<li><i class="fas fa-exclamation-circle text-danger me-2"></i>${ponto}</li>`
    ).join('');
}

function atualizarTempo() {
    const tempoDecorrido = Math.floor((new Date() - entrevista.inicio) / 1000);
    document.getElementById('tempo').textContent = formatarTempo(tempoDecorrido);
}

function formatarTempo(segundos) {
    const minutos = Math.floor(segundos / 60);
    segundos = segundos % 60;
    return `${String(minutos).padStart(2, '0')}:${String(segundos).padStart(2, '0')}`;
}

function verTranscricao() {
    const transcricao = entrevista.historico.map(msg => 
        `${msg.isUser ? 'Você' : 'Entrevistador'}: ${msg.mensagem}`
    ).join('\n\n');
    
    const win = window.open('', '_blank');
    win.document.write(`
        <html>
            <head>
                <title>Transcrição da Entrevista</title>
                <style>
                    body { font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; }
                    .mensagem { margin-bottom: 20px; }
                </style>
            </head>
            <body>
                <h2>Transcrição da Entrevista</h2>
                <pre>${transcricao}</pre>
            </body>
        </html>
    `);
}

async function baixarRelatorio() {
    try {
        const response = await fetch('/alunos/download-relatorio-entrevista', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                historico: entrevista.historico,
                tempo: Math.floor((new Date() - entrevista.inicio) / 1000),
                pontuacoes: {
                    clareza: document.getElementById('pontos-clareza').textContent,
                    conteudo: document.getElementById('pontos-conteudo').textContent,
                    objetividade: document.getElementById('pontos-objetividade').textContent
                },
                feedback_geral: document.getElementById('feedback-geral').innerHTML,
                pontos_fortes: Array.from(document.getElementById('pontos-fortes').children).map(li => li.textContent),
                pontos_melhorar: Array.from(document.getElementById('pontos-melhorar').children).map(li => li.textContent)
            })
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'relatorio_entrevista.pdf';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
        } else {
            alert('Erro ao gerar PDF');
        }
    } catch (error) {
        console.error('Erro:', error);
        alert('Erro ao baixar relatório');
    }
}

function novaEntrevista() {
    if (entrevista.timer) {
        clearInterval(entrevista.timer);
    }
    
    document.getElementById('entrevista-form').reset();
    document.getElementById('config-card').style.display = 'block';
    document.getElementById('entrevista-area').style.display = 'none';
    document.getElementById('chat-card').style.display = 'none';
    document.getElementById('resultado-card').style.display = 'none';
    
    entrevista = {
        timer: null,
        inicio: null,
        historico: [],
        finalizada: false
    };
}
