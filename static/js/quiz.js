let quiz = {
    questoes: [],
    questaoAtual: 0,
    pontos: 0,
    tempoInicio: null,
    timer: null,
    respostas: [],
    modoEstudo: true
};

function iniciarQuizManual() {
    console.log('Iniciando quiz...');
    
    // Mostrar loading
    document.getElementById('loading').style.display = 'block';
    document.getElementById('config-card').style.display = 'none';
    document.getElementById('quiz-area').style.display = 'block';

    // Pegar valores do formulário
    const data = {
        disciplina: document.getElementById('disciplina').value,
        nivel: document.getElementById('nivel').value,
        quantidade: document.getElementById('quantidade').value,
        conteudo: document.getElementById('conteudo').value
    };

    console.log('Dados:', data);

    if (!data.disciplina || !data.nivel || !data.conteudo.trim()) {
        alert('Por favor, preencha todos os campos obrigatórios.');
        novoQuiz();
        return;
    }

    quiz.modoEstudo = document.getElementById('modo_estudo').checked;

    // Fazer requisição para gerar quiz
    fetch('/alunos/gerar-quiz', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    })
    .then(response => {
        console.log('Resposta recebida');
        return response.json();
    })
    .then(data => {
        console.log('Dados processados:', data);
        if (data.success) {
            quiz.questoes = data.quiz;
            iniciarQuiz();
        } else {
            alert(data.error || 'Erro ao gerar quiz');
            novoQuiz();
        }
    })
    .catch(error => {
        console.error('Erro:', error);
        alert('Erro ao gerar quiz');
        novoQuiz();
    })
    .finally(() => {
        document.getElementById('loading').style.display = 'none';
    });
}

function iniciarQuiz() {
    quiz.questaoAtual = 0;
    quiz.pontos = 0;
    quiz.respostas = new Array(quiz.questoes.length).fill(null);
    quiz.tempoInicio = new Date();
    
    // Iniciar timer
    quiz.timer = setInterval(atualizarTempo, 1000);
    
    // Mostrar primeira questão
    mostrarQuestao();
    document.getElementById('questao-card').style.display = 'block';
}

function mostrarQuestao() {
    const questao = quiz.questoes[quiz.questaoAtual];
    document.getElementById('questao-numero').textContent = quiz.questaoAtual + 1;
    document.getElementById('pontos').textContent = quiz.pontos;
    
    // Atualizar conteúdo da questão
    document.getElementById('questao-content').innerHTML = `
        <p class="lead">${questao.pergunta}</p>
    `;
    
    // Criar alternativas
    const alternativas = document.getElementById('alternativas');
    alternativas.innerHTML = '';
    questao.alternativas.forEach((alt, index) => {
        const btn = document.createElement('button');
        btn.className = 'btn btn-outline-info w-100 text-start mb-2 p-3';
        if (quiz.respostas[quiz.questaoAtual] !== null) {
            if (index === questao.resposta) {
                btn.className = 'btn btn-success w-100 text-start mb-2 p-3';
            } else if (index === quiz.respostas[quiz.questaoAtual]) {
                btn.className = 'btn btn-danger w-100 text-start mb-2 p-3';
            }
            btn.disabled = true;
        } else {
            btn.onclick = () => responder(index);
        }
        btn.innerHTML = `
            <div class="d-flex align-items-center">
                <span class="me-3">${String.fromCharCode(65 + index)}.</span>
                <span>${alt}</span>
            </div>
        `;
        alternativas.appendChild(btn);
    });
    
    // Atualizar botões de navegação
    document.getElementById('btn-anterior').disabled = quiz.questaoAtual === 0;
    document.getElementById('btn-proximo').style.display = quiz.questaoAtual < quiz.questoes.length - 1 ? 'block' : 'none';
    
    // Mostrar feedback se já respondeu
    const feedback = document.getElementById('feedback');
    if (quiz.respostas[quiz.questaoAtual] !== null && quiz.modoEstudo) {
        feedback.innerHTML = `
            <div class="alert ${quiz.respostas[quiz.questaoAtual] === questao.resposta ? 'alert-success' : 'alert-danger'}">
                <h5 class="alert-heading">${quiz.respostas[quiz.questaoAtual] === questao.resposta ? 'Correto!' : 'Incorreto'}</h5>
                <p>${questao.explicacao}</p>
            </div>
        `;
        feedback.style.display = 'block';
    } else {
        feedback.style.display = 'none';
    }
}

function responder(index) {
    const questao = quiz.questoes[quiz.questaoAtual];
    quiz.respostas[quiz.questaoAtual] = index;
    
    if (index === questao.resposta) {
        quiz.pontos += 10;
    }
    
    mostrarQuestao();
    
    // Se for a última questão
    if (quiz.questaoAtual === quiz.questoes.length - 1) {
        const btnProximo = document.getElementById('btn-proximo');
        btnProximo.textContent = 'Finalizar';
        btnProximo.onclick = finalizarQuiz;
        btnProximo.style.display = 'block';
    }
}

function proximaQuestao() {
    if (quiz.questaoAtual < quiz.questoes.length - 1) {
        quiz.questaoAtual++;
        mostrarQuestao();
    }
}

function questaoAnterior() {
    if (quiz.questaoAtual > 0) {
        quiz.questaoAtual--;
        mostrarQuestao();
    }
}

function finalizarQuiz() {
    clearInterval(quiz.timer);
    
    const tempoTotal = Math.floor((new Date() - quiz.tempoInicio) / 1000);
    const acertos = quiz.respostas.filter((r, i) => r === quiz.questoes[i].resposta).length;
    
    document.getElementById('questao-card').style.display = 'none';
    document.getElementById('resultado-card').style.display = 'block';
    
    document.getElementById('pontuacao-final').textContent = quiz.pontos;
    document.getElementById('acertos').textContent = `${acertos}/${quiz.questoes.length}`;
    document.getElementById('tempo-total').textContent = formatarTempo(tempoTotal);
}

function atualizarTempo() {
    const tempoDecorrido = Math.floor((new Date() - quiz.tempoInicio) / 1000);
    document.getElementById('tempo').textContent = formatarTempo(tempoDecorrido);
}

function formatarTempo(segundos) {
    const minutos = Math.floor(segundos / 60);
    segundos = segundos % 60;
    return `${minutos.toString().padStart(2, '0')}:${segundos.toString().padStart(2, '0')}`;
}

function verRevisao() {
    quiz.questaoAtual = 0;
    quiz.modoEstudo = true;
    document.getElementById('resultado-card').style.display = 'none';
    document.getElementById('questao-card').style.display = 'block';
    mostrarQuestao();
}

function baixarResultado() {
    const resultado = {
        pontos: quiz.pontos,
        acertos: quiz.respostas.filter((r, i) => r === quiz.questoes[i].resposta).length,
        total: quiz.questoes.length,
        tempo: formatarTempo(Math.floor((new Date() - quiz.tempoInicio) / 1000)),
        detalhes: quiz.questoes.map((q, i) => ({
            pergunta: q.pergunta,
            alternativas: q.alternativas,
            resposta_correta: q.alternativas[q.resposta],
            sua_resposta: q.alternativas[quiz.respostas[i]],
            acertou: quiz.respostas[i] === q.resposta,
            explicacao: q.explicacao
        }))
    };
    
    // Criar HTML bonito
    const html = `
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Resultado do Quiz</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                color: #333;
                margin: 0;
                padding: 20px;
                background-color: #f8f9fa;
            }
            .container {
                max-width: 800px;
                margin: 0 auto;
                background-color: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .resumo {
                background-color: #f8f9fa;
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 30px;
            }
            .questao {
                margin-bottom: 30px;
                padding: 20px;
                border: 1px solid #dee2e6;
                border-radius: 8px;
            }
            .questao.correta {
                border-left: 5px solid #28a745;
            }
            .questao.incorreta {
                border-left: 5px solid #dc3545;
            }
            .alternativa {
                padding: 10px;
                margin: 5px 0;
                border-radius: 4px;
            }
            .alternativa.correta {
                background-color: #d4edda;
                color: #155724;
            }
            .alternativa.incorreta {
                background-color: #f8d7da;
                color: #721c24;
            }
            .explicacao {
                margin-top: 15px;
                padding: 15px;
                background-color: #e9ecef;
                border-radius: 4px;
            }
            .badge {
                font-size: 1em;
                padding: 8px 12px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1 class="text-center mb-4">Resultado do Quiz</h1>
            
            <div class="resumo">
                <div class="row text-center">
                    <div class="col-md-4">
                        <h4>Pontuação</h4>
                        <span class="badge bg-primary">${resultado.pontos} pontos</span>
                    </div>
                    <div class="col-md-4">
                        <h4>Acertos</h4>
                        <span class="badge bg-success">${resultado.acertos}/${resultado.total}</span>
                    </div>
                    <div class="col-md-4">
                        <h4>Tempo</h4>
                        <span class="badge bg-info">${resultado.tempo}</span>
                    </div>
                </div>
            </div>

            <div class="questoes">
                ${resultado.detalhes.map((q, index) => `
                    <div class="questao ${q.acertou ? 'correta' : 'incorreta'}">
                        <h5>Questão ${index + 1}</h5>
                        <p class="lead">${q.pergunta}</p>
                        
                        <div class="alternativas">
                            ${q.alternativas.map((alt, i) => `
                                <div class="alternativa ${alt === q.resposta_correta ? 'correta' : (alt === q.sua_resposta && !q.acertou ? 'incorreta' : '')}">
                                    <strong>${String.fromCharCode(65 + i)}.</strong> ${alt}
                                    ${alt === q.resposta_correta ? ' <span class="badge bg-success">Correta</span>' : ''}
                                    ${alt === q.sua_resposta && !q.acertou ? ' <span class="badge bg-danger">Sua resposta</span>' : ''}
                                </div>
                            `).join('')}
                        </div>
                        
                        <div class="explicacao">
                            <h6>Explicação:</h6>
                            <p>${q.explicacao}</p>
                        </div>
                    </div>
                `).join('')}
            </div>
        </div>
    </body>
    </html>
    `;
    
    // Criar blob e fazer download
    const blob = new Blob([html], { type: 'text/html' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'resultado_quiz.html';
    a.click();
    window.URL.revokeObjectURL(url);
}

function novoQuiz() {
    // Limpar quiz atual
    quiz = {
        questoes: [],
        questaoAtual: 0,
        pontos: 0,
        tempoInicio: null,
        timer: null,
        respostas: [],
        modoEstudo: true
    };
    
    // Resetar interface
    document.getElementById('quiz-form').reset();
    document.getElementById('quiz-area').style.display = 'none';
    document.getElementById('config-card').style.display = 'block';
    document.getElementById('questao-card').style.display = 'none';
    document.getElementById('resultado-card').style.display = 'none';
}
