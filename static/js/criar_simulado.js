let questoesSelecionadas = new Map(); // id -> {questao, pontos, ordem}

document.addEventListener('DOMContentLoaded', function() {
    // Inicializar Select2
    $('.select2').select2({
        width: '100%',
        theme: 'bootstrap-5'
    });

    // Definir data mínima como hoje
    const hoje = new Date().toISOString().split('T')[0];
    document.getElementById('data_inicio').min = hoje + 'T00:00';
    document.getElementById('data_fim').min = hoje + 'T00:00';

    // Atualizar data fim quando data início mudar
    document.getElementById('data_inicio').addEventListener('change', function() {
        document.getElementById('data_fim').min = this.value;
    });

    // Form de pesquisa
    document.getElementById('pesquisa-form').addEventListener('submit', function(e) {
        e.preventDefault();
        pesquisarQuestoes();
    });

    // Sincronizar disciplina do simulado com filtro de questões
    document.getElementById('disciplina').addEventListener('change', function() {
        document.getElementById('filtro-disciplina').value = this.value;
        $('.select2').trigger('change');
        pesquisarQuestoes();
    });

    // Carregar questões iniciais
    pesquisarQuestoes();
});

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
        div.className = `questao-preview ${questoesSelecionadas.has(questao.id) ? 'questao-selecionada' : ''}`;
        div.innerHTML = `
            <div class="d-flex justify-content-between align-items-start mb-2">
                <div>
                    <span class="badge bg-primary">${questao.disciplina}</span>
                    <span class="badge bg-secondary">${questao.assunto}</span>
                    <span class="badge bg-info">${questao.nivel}</span>
                    <span class="badge bg-warning">${questao.tipo}</span>
                </div>
                <button class="btn btn-sm ${questoesSelecionadas.has(questao.id) ? 'btn-danger' : 'btn-success'}"
                        onclick="toggleQuestao(${questao.id}, ${JSON.stringify(questao).replace(/"/g, '&quot;')})">
                    <i class="bi bi-${questoesSelecionadas.has(questao.id) ? 'dash' : 'plus'}-lg"></i>
                </button>
            </div>
            <p class="mb-2"><strong>Enunciado:</strong> ${questao.enunciado}</p>
            ${questao.tipo === 'objetiva' ? renderizarAlternativas(questao.alternativas) : ''}
            <p class="mb-0"><strong>Resposta:</strong> ${questao.resposta}</p>
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

function toggleQuestao(id, questao) {
    if (questoesSelecionadas.has(id)) {
        questoesSelecionadas.delete(id);
    } else {
        questoesSelecionadas.set(id, {
            questao: questao,
            pontos: 1,
            ordem: questoesSelecionadas.size + 1
        });
    }
    
    atualizarQuestoesSelecionadas();
    pesquisarQuestoes(); // Atualizar visual das questões
}

function atualizarQuestoesSelecionadas() {
    const container = document.getElementById('questoes-selecionadas');
    container.innerHTML = '';

    if (questoesSelecionadas.size === 0) {
        container.innerHTML = '<p class="text-center text-muted">Arraste questões aqui</p>';
        atualizarTotalPontos();
        return;
    }

    // Converter para array e ordenar
    const questoesArray = Array.from(questoesSelecionadas.entries())
        .map(([id, data]) => ({id, ...data}))
        .sort((a, b) => a.ordem - b.ordem);

    questoesArray.forEach(({id, questao, pontos, ordem}) => {
        const div = document.createElement('div');
        div.className = 'questao-preview';
        div.draggable = true;
        div.dataset.id = id;
        
        div.innerHTML = `
            <div class="d-flex justify-content-between align-items-start mb-2">
                <div class="d-flex align-items-center">
                    <span class="ordem me-2">${ordem}</span>
                    <div>
                        <span class="badge bg-primary">${questao.disciplina}</span>
                        <span class="badge bg-secondary">${questao.assunto}</span>
                    </div>
                </div>
                <div class="d-flex align-items-center">
                    <input type="number" class="form-control form-control-sm pontos-input me-2" 
                           value="${pontos}" min="0" step="0.5" 
                           onchange="atualizarPontos(${id}, this.value)">
                    <button class="btn btn-sm btn-danger" onclick="removerQuestao(${id})">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </div>
            <p class="mb-0"><strong>Enunciado:</strong> ${questao.enunciado}</p>
        `;

        // Eventos de drag and drop
        div.addEventListener('dragstart', handleDragStart);
        div.addEventListener('dragover', handleDragOver);
        div.addEventListener('drop', handleDrop);
        div.addEventListener('dragend', handleDragEnd);
        
        container.appendChild(div);
    });

    atualizarTotalPontos();
}

function atualizarPontos(id, pontos) {
    if (questoesSelecionadas.has(id)) {
        questoesSelecionadas.get(id).pontos = Number(pontos);
        atualizarTotalPontos();
    }
}

function atualizarTotalPontos() {
    const total = Array.from(questoesSelecionadas.values())
        .reduce((sum, {pontos}) => sum + Number(pontos), 0);
    document.getElementById('total-pontos').textContent = `Total: ${total} pontos`;
}

function removerQuestao(id) {
    questoesSelecionadas.delete(id);
    atualizarQuestoesSelecionadas();
    pesquisarQuestoes();
}

// Drag and Drop
let dragSrcEl = null;

function handleDragStart(e) {
    dragSrcEl = this;
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', this.dataset.id);
    this.classList.add('dragging');
}

function handleDragOver(e) {
    if (e.preventDefault) {
        e.preventDefault();
    }
    e.dataTransfer.dropEffect = 'move';
    return false;
}

function handleDrop(e) {
    if (e.stopPropagation) {
        e.stopPropagation();
    }

    if (dragSrcEl !== this) {
        const srcId = Number(dragSrcEl.dataset.id);
        const destId = Number(this.dataset.id);
        
        const srcOrdem = questoesSelecionadas.get(srcId).ordem;
        const destOrdem = questoesSelecionadas.get(destId).ordem;

        // Atualizar ordens
        if (srcOrdem < destOrdem) {
            questoesSelecionadas.forEach((data, id) => {
                if (data.ordem > srcOrdem && data.ordem <= destOrdem) {
                    data.ordem--;
                }
            });
        } else {
            questoesSelecionadas.forEach((data, id) => {
                if (data.ordem >= destOrdem && data.ordem < srcOrdem) {
                    data.ordem++;
                }
            });
        }
        questoesSelecionadas.get(srcId).ordem = destOrdem;

        atualizarQuestoesSelecionadas();
    }

    return false;
}

function handleDragEnd() {
    this.classList.remove('dragging');
}

async function salvarSimulado(status) {
    if (questoesSelecionadas.size === 0) {
        alert('Adicione pelo menos uma questão ao simulado');
        return;
    }

    const form = document.getElementById('simulado-form');
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }

    const dataInicio = new Date(document.getElementById('data_inicio').value);
    const dataFim = new Date(document.getElementById('data_fim').value);

    if (dataFim <= dataInicio) {
        alert('A data de fim deve ser posterior à data de início');
        return;
    }

    const simulado = {
        titulo: document.getElementById('titulo').value,
        descricao: document.getElementById('descricao').value,
        disciplina: document.getElementById('disciplina').value,
        duracao: Number(document.getElementById('duracao').value),
        data_inicio: dataInicio.toISOString(),
        data_fim: dataFim.toISOString(),
        status: status,
        questoes: Array.from(questoesSelecionadas.entries()).map(([id, data]) => ({
            id: Number(id),
            ordem: data.ordem,
            pontos: Number(data.pontos)
        }))
    };

    try {
        const response = await fetch('/professores/salvar-simulado', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(simulado)
        });

        const data = await response.json();
        
        if (data.success) {
            alert(status === 'publicado' ? 'Simulado publicado com sucesso!' : 'Simulado salvo como rascunho!');
            window.location.href = '/professores/simulados';
        } else {
            throw new Error(data.error || 'Erro ao salvar simulado');
        }
    } catch (error) {
        console.error('Erro:', error);
        alert(error.message);
    }
}
