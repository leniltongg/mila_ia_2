document.addEventListener('DOMContentLoaded', function() {
    console.log('Inicializando script de apresentação...');
    
    const form = document.getElementById('apresentacao-form');
    const feedbackArea = document.getElementById('feedback-area');
    const loadingDiv = document.getElementById('loading');
    
    console.log('Form encontrado:', form);
    console.log('Feedback area encontrada:', feedbackArea);
    console.log('Loading div encontrada:', loadingDiv);

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
        const duracao = document.getElementById('duracao').value;
        const conteudo = document.getElementById('conteudo').value;
        const incluirSlides = document.getElementById('incluir_slides').checked;
        const incluirTecnicas = document.getElementById('incluir_tecnicas').checked;

        console.log('Dados do formulário:', {
            tipo,
            duracao,
            conteudo,
            incluirSlides,
            incluirTecnicas
        });

        if (!tipo || !conteudo.trim()) {
            alert('Por favor, preencha todos os campos obrigatórios.');
            return;
        }

        // Mostrar loading
        feedbackArea.style.display = 'block';
        document.querySelectorAll('.tab-pane').forEach(pane => {
            const div = pane.querySelector('div');
            if (div) div.innerHTML = '';
        });
        loadingDiv.style.display = 'block';

        try {
            console.log('Enviando requisição para o servidor...');
            const response = await fetch('/alunos/avaliar-apresentacao', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    tipo: tipo,
                    duracao: duracao,
                    conteudo: conteudo,
                    incluir_slides: incluirSlides,
                    incluir_tecnicas: incluirTecnicas
                })
            });

            console.log('Resposta recebida:', response);
            if (!response.ok) {
                throw new Error('Erro na requisição: ' + response.status);
            }

            const data = await response.json();
            console.log('Dados processados:', data);

            if (data.success) {
                // Preencher as tabs com o feedback
                document.getElementById('estrutura-content-text').innerHTML = data.feedback.estrutura;
                document.getElementById('oratoria-content-text').innerHTML = data.feedback.oratoria;
                document.getElementById('slides-content-text').innerHTML = data.feedback.slides;
                document.getElementById('tempo-content-text').innerHTML = data.feedback.tempo;
                console.log('Feedback inserido nas tabs com sucesso!');
            } else {
                throw new Error(data.error || 'Erro ao gerar feedback');
            }
        } catch (error) {
            console.error('Erro detalhado:', error);
            alert(error.message || 'Erro ao processar sua solicitação');
        } finally {
            loadingDiv.style.display = 'none';
        }
    });
});

function copiarFeedback() {
    const estrutura = document.getElementById('estrutura-content-text').innerHTML;
    const oratoria = document.getElementById('oratoria-content-text').innerHTML;
    const slides = document.getElementById('slides-content-text').innerHTML;
    const tempo = document.getElementById('tempo-content-text').innerHTML;

    const texto = `FEEDBACK DA APRESENTAÇÃO\n\n` +
                 `ESTRUTURA:\n${estrutura}\n\n` +
                 `ORATÓRIA:\n${oratoria}\n\n` +
                 `SLIDES:\n${slides}\n\n` +
                 `GESTÃO DO TEMPO:\n${tempo}`;

    navigator.clipboard.writeText(texto.replace(/<[^>]*>/g, ''))
        .then(() => alert('Feedback copiado para a área de transferência!'))
        .catch(err => {
            console.error('Erro ao copiar:', err);
            alert('Erro ao copiar o feedback');
        });
}

function baixarFeedback() {
    const estrutura = document.getElementById('estrutura-content-text').innerHTML;
    const oratoria = document.getElementById('oratoria-content-text').innerHTML;
    const slides = document.getElementById('slides-content-text').innerHTML;
    const tempo = document.getElementById('tempo-content-text').innerHTML;

    fetch('/alunos/download_feedback', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            estrutura: estrutura,
            oratoria: oratoria,
            slides: slides,
            tempo: tempo
        })
    })
    .then(response => {
        if (!response.ok) throw new Error('Erro ao gerar PDF');
        return response.blob();
    })
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'feedback_apresentacao.pdf';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();
    })
    .catch(error => {
        console.error('Erro:', error);
        alert('Erro ao baixar o feedback');
    });
}
