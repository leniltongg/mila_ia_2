from functools import wraps
from flask import make_response, request

def add_security_headers(response):
    """Adiciona headers de segurança a todas as respostas"""
    
    # Previne que o navegador faça MIME-sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'
    
    # Previne clickjacking
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    
    # Ativa a proteção XSS do navegador
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # Content Security Policy
    csp = (
        "default-src 'self' https:; "
        "script-src 'self' https: 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' https: 'unsafe-inline'; "
        "img-src 'self' https: data:; "
        "font-src 'self' https:; "
        "frame-ancestors 'self'"
    )
    response.headers['Content-Security-Policy'] = csp
    
    # Referrer Policy
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # Previne cache de dados sensíveis
    if request.path.startswith('/admin') or request.path.startswith('/api'):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    
    return response

def init_security_middleware(app):
    """Inicializa o middleware de segurança"""
    app.after_request(add_security_headers)
    
    # Adiciona proteção contra manipulação do DOM
    @app.after_request
    def add_security_script(response):
        if response.content_type.startswith('text/html'):
            # Adiciona nonce único para cada resposta
            from secrets import token_urlsafe
            nonce = token_urlsafe(16)
            
            # Adiciona script de proteção inline com nonce
            script = f"""
                <script nonce="{nonce}">
                    // Detecta DevTools
                    let devtools = function() {{}};
                    devtools.toString = function() {{
                        document.body.classList.add('devtools-open');
                        return '';
                    }};
                    
                    // Desabilita teclas de atalho do DevTools
                    document.addEventListener('keydown', function(e) {{
                        if ((e.ctrlKey && e.shiftKey && (e.keyCode === 73 || e.keyCode === 74 || e.keyCode === 67)) || e.keyCode === 123) {{
                            e.preventDefault();
                        }}
                    }});
                    
                    // Desabilita clique direito
                    document.addEventListener('contextmenu', function(e) {{
                        e.preventDefault();
                    }});
                    
                    // Protege elementos sensíveis
                    document.addEventListener('DOMContentLoaded', function() {{
                        const sensiveElements = document.querySelectorAll('.sensitive-data, input[type="password"], .user-info');
                        sensiveElements.forEach(function(element) {{
                            element.setAttribute('data-protected', 'true');
                            element.classList.add('protected');
                        }});
                    }});
                </script>
            """
            
            # Insere o script antes do </body>
            response.data = response.data.replace(
                b'</body>',
                f'{script}</body>'.encode()
            )
            
            # Atualiza o CSP para permitir o script inline com nonce
            csp = response.headers.get('Content-Security-Policy', '')
            csp = csp.replace(
                "script-src",
                f"script-src 'nonce-{nonce}'"
            )
            response.headers['Content-Security-Policy'] = csp
            
        return response
