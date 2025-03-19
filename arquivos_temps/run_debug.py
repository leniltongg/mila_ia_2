from app import app
import sys

if __name__ == '__main__':
    # Forçar saída imediata
    sys.stdout.reconfigure(line_buffering=True)
    
    # Desabilitar buffering
    import functools
    print = functools.partial(print, flush=True)
    
    print("=== INICIANDO SERVIDOR EM MODO DEBUG ===")
    
    # Configurar app
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.config['DEBUG'] = True
    app.config['PROPAGATE_EXCEPTIONS'] = True
    
    # Executar
    app.run(debug=True, use_reloader=False)
