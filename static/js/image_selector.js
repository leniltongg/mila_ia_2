// Variável global para armazenar o campo atual
let campoImagemAtual = null;

// Handler para botões de adicionar imagem
function initImageSelector() {
    console.log('Inicializando seletor de imagens...');
    
    $('.btn-add-image').on('click', function(e) {
        console.log('Botão de adicionar imagem clicado');
        e.preventDefault();
        
        campoImagemAtual = $(this).data('field');
        console.log('Campo atual:', campoImagemAtual);
        
        // Força a abertura do modal
        var modal = new bootstrap.Modal(document.getElementById('modalSeletorImagens'));
        modal.show();
        
        // Carrega as imagens
        carregarImagens();
    });

    // Handlers para os filtros com debug
    $('#filtroDisciplina, #filtroAssunto, #filtroTipo, #busca').on('change keyup', function(e) {
        console.log('Filtro alterado:', e.target.id);
        carregarImagens();
    });
}

// Função para carregar imagens com mais logs
function carregarImagens() {
    console.log('Iniciando carregamento de imagens...');
    
    const params = {
        disciplina: $('#filtroDisciplina').val(),
        assunto: $('#filtroAssunto').val(),
        tipo: $('#filtroTipo').val(),
        busca: $('#busca').val()
    };
    
    console.log('Parâmetros da busca:', params);

    $.ajax({
        url: '/secretaria_educacao/filtrar_imagens',
        method: 'GET',
        data: params,
        success: function(response) {
            console.log('Resposta recebida:', response);
            if (response.success) {
                const grid = $('#modalImagensGrid');
                grid.empty();
                
                if (response.imagens.length === 0) {
                    grid.append('<p class="text-center">Nenhuma imagem encontrada</p>');
                    return;
                }
                
                response.imagens.forEach(function(imagem) {
                    console.log('Processando imagem:', imagem);
                    const item = $(`
                        <div class="imagem-item">
                            <img src="/static/${imagem.url}" alt="${imagem.descricao || imagem.nome}">
                            <div class="text-center">
                                <small class="d-block text-truncate">${imagem.nome}</small>
                            </div>
                        </div>
                    `);

                    item.on('click', function() {
                        console.log('Imagem clicada:', imagem);
                        const textarea = $(`#${campoImagemAtual}`);
                        const imgTag = `\n<img src="/static/${imagem.url}" alt="${imagem.descricao || imagem.nome}">\n`;
                        
                        textarea.val(textarea.val() + imgTag);
                        
                        const previewContainer = $(`#${campoImagemAtual}_preview`);
                        const previewImg = $('<img>', {
                            src: `/static/${imagem.url}`,
                            alt: 'Preview',
                            class: 'img-fluid mb-2'
                        });
                        previewContainer.append(previewImg);
                        
                        $('#modalSeletorImagens').modal('hide');
                    });
                    
                    grid.append(item);
                });
            } else {
                console.error('Erro ao carregar imagens:', response.message);
                $('#modalImagensGrid').html('<p class="text-center text-danger">Erro ao carregar imagens</p>');
            }
        },
        error: function(xhr, status, error) {
            console.error('Erro na requisição:', {xhr, status, error});
            $('#modalImagensGrid').html('<p class="text-center text-danger">Erro ao carregar imagens</p>');
        }
    });
}

// Inicializa quando o documento estiver pronto
$(document).ready(function() {
    console.log('Document ready - image_selector.js');
    initImageSelector();
});
