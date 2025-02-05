// Previne inspeção e manipulação do DOM
(function() {
    // Desabilita o clique direito
    document.addEventListener('contextmenu', function(e) {
        e.preventDefault();
    });

    // Desabilita atalhos de teclado comuns do DevTools
    document.addEventListener('keydown', function(e) {
        // Ctrl+Shift+I, Ctrl+Shift+J, Ctrl+Shift+C, F12
        if (
            (e.ctrlKey && e.shiftKey && (e.keyCode === 73 || e.keyCode === 74 || e.keyCode === 67)) ||
            (e.keyCode === 123)
        ) {
            e.preventDefault();
        }
    });

    // Detecta quando o DevTools é aberto
    let devtools = function() {};
    devtools.toString = function() {
        detectDevTools();
        return '';
    };

    // Monitora mudanças no DOM
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            // Se elementos foram adicionados, verifica se são manipulações maliciosas
            if (mutation.addedNodes.length) {
                mutation.addedNodes.forEach(function(node) {
                    // Verifica se o elemento adicionado é permitido
                    if (node.nodeType === 1 && !isAllowedElement(node)) {
                        node.remove();
                    }
                });
            }
            
            // Se atributos foram modificados
            if (mutation.type === 'attributes') {
                // Restaura o valor original se for um campo protegido
                if (isProtectedField(mutation.target)) {
                    mutation.target.value = mutation.target.getAttribute('data-original-value');
                }
            }
        });
    });

    // Configuração do observer
    const config = { 
        attributes: true, 
        childList: true, 
        subtree: true,
        attributeOldValue: true
    };

    // Inicia a observação do DOM
    observer.observe(document.body, config);

    // Lista de elementos permitidos para adição dinâmica
    function isAllowedElement(element) {
        const allowedTags = ['DIV', 'SPAN', 'P', 'A', 'IMG', 'INPUT', 'BUTTON', 'FORM'];
        return allowedTags.includes(element.tagName);
    }

    // Lista de campos protegidos contra modificação
    function isProtectedField(element) {
        return element.hasAttribute('data-protected');
    }

    // Função chamada quando o DevTools é detectado
    function detectDevTools() {
        // Você pode personalizar a ação aqui
        // Por exemplo, redirecionar para outra página ou mostrar um aviso
        document.body.innerHTML = '<h1>Inspeção não permitida</h1>';
        // Ou redirecionar
        // window.location.href = '/error';
    }

    // Proteção contra modificação de innerHTML
    const originalInnerHTML = Object.getOwnPropertyDescriptor(Element.prototype, 'innerHTML');
    Object.defineProperty(Element.prototype, 'innerHTML', {
        set: function(value) {
            // Apenas permite modificação se o elemento não for protegido
            if (!this.hasAttribute('data-protected')) {
                originalInnerHTML.set.call(this, value);
            }
        },
        get: function() {
            return originalInnerHTML.get.call(this);
        }
    });

    // Proteção contra modificação de value em inputs
    const originalInputValue = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value');
    Object.defineProperty(HTMLInputElement.prototype, 'value', {
        set: function(value) {
            // Apenas permite modificação se o input não for protegido
            if (!this.hasAttribute('data-protected')) {
                originalInputValue.set.call(this, value);
            }
        },
        get: function() {
            return originalInputValue.get.call(this);
        }
    });

    // Adiciona atributo data-protected a elementos que precisam ser protegidos
    document.addEventListener('DOMContentLoaded', function() {
        // Protege elementos específicos
        const protectedElements = document.querySelectorAll('.protected, [data-protected]');
        protectedElements.forEach(function(element) {
            element.setAttribute('data-protected', 'true');
            // Salva o valor original
            if (element.value) {
                element.setAttribute('data-original-value', element.value);
            }
        });
    });

    // Console.log personalizado para evitar debugging
    const consoleOutput = console.log;
    console.log = function() {
        consoleOutput.apply(console, ['🔒 Console bloqueado']);
    };

})();
