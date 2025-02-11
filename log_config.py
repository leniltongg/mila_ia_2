import logging
import os
from logging.handlers import RotatingFileHandler
import traceback

def setup_logger(app):
    # Criar diretório de logs se não existir
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Configurar o arquivo de log
    log_file = os.path.join('logs', 'app.log')
    
    # Configurar o formato do log com mais detalhes
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    )
    
    # Configurar o handler do arquivo
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=10485760,  # 10MB
        backupCount=10
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    
    # Configurar o handler do console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG)
    
    # Remover handlers existentes
    del app.logger.handlers[:]
    
    # Adicionar os novos handlers
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(logging.DEBUG)
    
    # Configurar para mostrar erros completos
    app.debug = True
    
    def log_exception(exc_info):
        """Log exception with full traceback."""
        app.logger.error('Exception occurred:', exc_info=exc_info)
    
    # Registrar função para logging de exceções não tratadas
    app.log_exception = log_exception
    
    app.logger.info('Logger configurado com sucesso em modo DEBUG!')
