document.addEventListener('DOMContentLoaded', function() {
    // Inicializar Select2
    $('.select2').select2({
        width: '100%',
        theme: 'bootstrap-5'
    });

    // Mostrar/ocultar alternativas baseado no tipo de questão
    document.getElementById('tipo').addEventListener('change', function() {
        const alternativasContainer = document.getElementById('alternativas-container');
        alternativasContainer.style.display = this.value === 'objetiva' ? 'block' : 'none';
    });

    // Form de cadastro de questão
    document.getElementById('questao-form').addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = {
            disciplina: document.getElementById('disciplina').value,
            assunto: document.getElementById('assunto').value,
            nivel: document.getElementById('nivel').value,
            tipo: document.getElementById('tipo').value,
            enunciado: document.getElementById('enunciado').value,
            resposta: document.getElementById('resposta').value,
            explicacao: document.getElementById('explicacao').value
        };

        // Adicionar alternativas se for questão objetiva
        if (formData.tipo === 'objetiva') {
            const alternativas = [];
            document.querySelectorAll('.alternativa-input').forEach((input, index) => {
                alternativas.push({
                    letra: String.fromCharCode(65 + index), // A, B, C, D, E
                    texto: input.value
                });
            });
            formData.alternativas = alternativas;
        }

        try {
            const response = await fetch('/professores/salvar-questao', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });

            const data = await response.json();
            
            if (data.success) {
                alert('Questão salva com sucesso!');
                limparFormulario();
                pesquisarQuestoes(); // Atualizar a lista
            } else {
                throw new Error(data.error || 'Erro ao salvar questão');
            }
        } catch (error) {
            console.error('Erro:', error);
            alert(error.message);
        }
    });

    // Form de pesquisa
    document.getElementById('pesquisa-form').addEventListener('submit', function(e) {
        e.preventDefault();
        pesquisarQuestoes();
    });

    // Carregar questões iniciais
    pesquisarQuestoes();
});

function adicionarAlternativa() {
    const container = document.getElementById('alternativas-list');
    const numAlternativas = container.children.length;
    
    if (numAlternativas >= 5) {
        alert('Máximo de 5 alternativas permitido');
        return;
    }

    const letra = String.fromCharCode(65 + numAlternativas); // A, B, C, D, E
    const div = document.createElement('div');
    div.className = 'input-group alternativa-input';
    div.innerHTML = `
        <span class="input-group-text">${letra}</span>
        <input type="text" class="form-control" required>
        <button type="button" class="btn btn-outline-danger btn-remove-alternativa" onclick="removerAlternativa(this)">
            <i class="bi bi-trash"></i>
        </button>
    `;
    
    container.appendChild(div);
}

function removerAlternativa(button) {
    const container = document.getElementById('alternativas-list');
    button.closest('.alternativa-input').remove();
    
    // Reordenar as letras
    container.querySelectorAll('.alternativa-input').forEach((div, index) => {
        div.querySelector('.input-group-text').textContent = String.fromCharCode(65 + index);
    });
}

function limparFormulario() {
    document.getElementById('questao-form').reset();
    document.getElementById('alternativas-list').innerHTML = '';
    $('.select2').val('').trigger('change');
}

async function pesquisarQuestoes(pagina = 1) {
    const filtros = {
        disciplina: document.getElementById('filtro-disciplina').value,
        assunto: document.getElementById('filtro-assunto').value,
        nivel: document.getElementById('filtro-nivel').value,
        tipo: document.getElementById('filtro-tipo').value,
        pagina: pagina
    };

    try {
        const response = await fetch('/professores/pesquisar-questoes?' + new URLSearchParams(filtros));
        const data = await response.json();
        
        if (data.success) {
            exibirResultados(data.questoes);
            atualizarPaginacao(data.total_paginas, pagina);
        } else {
            throw new Error(data.error || 'Erro ao pesquisar questões');
        }
    } catch (error) {
        console.error('Erro:', error);
        alert(error.message);
    }
}

function exibirResultados(questoes) {
    const container = document.getElementById('resultados');
    container.innerHTML = '';

    questoes.forEach(questao => {
        const div = document.createElement('div');
        div.className = 'questao-preview';
        div.innerHTML = `
            <div class="d-flex justify-content-between align-items-start mb-2">
                <div>
                    <span class="badge bg-primary">${questao.disciplina}</span>
                    <span class="badge bg-secondary">${questao.assunto}</span>
                    <span class="badge bg-info">${questao.nivel}</span>
                    <span class="badge bg-warning">${questao.tipo}</span>
                </div>
                <div class="btn-group">
                    <button class="btn btn-sm btn-outline-primary" onclick="editarQuestao(${questao.id})">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger" onclick="excluirQuestao(${questao.id})">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </div>
            <p class="mb-2"><strong>Enunciado:</strong> ${questao.enunciado}</p>
            ${questao.tipo === 'objetiva' ? renderizarAlternativas(questao.alternativas) : ''}
            <p class="mb-2"><strong>Resposta:</strong> ${questao.resposta}</p>
            ${questao.explicacao ? `<p class="mb-0"><strong>Explicação:</strong> ${questao.explicacao}</p>` : ''}
        `;
        container.appendChild(div);
    });

    if (questoes.length === 0) {
        container.innerHTML = '<p class="text-center text-muted">Nenhuma questão encontrada</p>';
    }
}

function renderizarAlternativas(alternativas) {
    return `
        <div class="mb-2">
            <strong>Alternativas:</strong>
            <ul class="list-unstyled mb-0">
                ${alternativas.map(alt => `
                    <li>${alt.letra}) ${alt.texto}</li>
                `).join('')}
            </ul>
        </div>
    `;
}

function atualizarPaginacao(totalPaginas, paginaAtual) {
    const container = document.getElementById('paginacao');
    container.innerHTML = '';

    // Anterior
    container.innerHTML += `
        <li class="page-item ${paginaAtual === 1 ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="pesquisarQuestoes(${paginaAtual - 1})">Anterior</a>
        </li>
    `;

    // Páginas
    for (let i = 1; i <= totalPaginas; i++) {
        container.innerHTML += `
            <li class="page-item ${i === paginaAtual ? 'active' : ''}">
                <a class="page-link" href="#" onclick="pesquisarQuestoes(${i})">${i}</a>
            </li>
        `;
    }

    // Próxima
    container.innerHTML += `
        <li class="page-item ${paginaAtual === totalPaginas ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="pesquisarQuestoes(${paginaAtual + 1})">Próxima</a>
        </li>
    `;
}

async function editarQuestao(id) {
    try {
        const response = await fetch(`/professores/questao/${id}`);
        const data = await response.json();
        
        if (data.success) {
            preencherFormulario(data.questao);
        } else {
            throw new Error(data.error || 'Erro ao carregar questão');
        }
    } catch (error) {
        console.error('Erro:', error);
        alert(error.message);
    }
}

function preencherFormulario(questao) {
    document.getElementById('disciplina').value = questao.disciplina;
    document.getElementById('assunto').value = questao.assunto;
    document.getElementById('nivel').value = questao.nivel;
    document.getElementById('tipo').value = questao.tipo;
    document.getElementById('enunciado').value = questao.enunciado;
    document.getElementById('resposta').value = questao.resposta;
    document.getElementById('explicacao').value = questao.explicacao;

    // Atualizar Select2
    $('.select2').trigger('change');

    // Preencher alternativas se for questão objetiva
    if (questao.tipo === 'objetiva') {
        document.getElementById('alternativas-container').style.display = 'block';
        document.getElementById('alternativas-list').innerHTML = '';
        questao.alternativas.forEach(alt => {
            adicionarAlternativa();
            const inputs = document.querySelectorAll('.alternativa-input input');
            inputs[inputs.length - 1].value = alt.texto;
        });
    }

    // Rolar até o formulário
    document.getElementById('questao-form').scrollIntoView({ behavior: 'smooth' });
}

async function excluirQuestao(id) {
    if (!confirm('Tem certeza que deseja excluir esta questão?')) {
        return;
    }

    try {
        const response = await fetch(`/professores/questao/${id}`, {
            method: 'DELETE'
        });
        const data = await response.json();
        
        if (data.success) {
            alert('Questão excluída com sucesso!');
            pesquisarQuestoes();
        } else {
            throw new Error(data.error || 'Erro ao excluir questão');
        }
    } catch (error) {
        console.error('Erro:', error);
        alert(error.message);
    }
}
