import sqlite3
import re
from datetime import datetime

def is_valid_email(email):
    """Valida o formato do email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def is_valid_cpf(cpf):
    """Valida o formato do CPF"""
    if not cpf:
        return True  # CPF é opcional
    cpf = ''.join(filter(str.isdigit, cpf))
    return len(cpf) == 11

def enhance_security():
    """Implementa melhorias de segurança na tabela usuarios"""
    conn = sqlite3.connect('educacional.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Backup da tabela
        print("Criando backup da tabela usuarios...")
        cursor.execute("DROP TABLE IF EXISTS usuarios_backup")
        cursor.execute("CREATE TABLE usuarios_backup AS SELECT * FROM usuarios")
        
        # Adiciona novas colunas
        print("Adicionando novas colunas de segurança...")
        new_columns = [
            ("ultimo_login", "TIMESTAMP"),
            ("tentativas_login", "INTEGER DEFAULT 0"),
            ("data_atualizacao_senha", "TIMESTAMP"),
            ("bloqueado", "INTEGER DEFAULT 0"),
            ("token_reset_senha", "TEXT"),
            ("token_expiracao", "TIMESTAMP")
        ]
        
        for col_name, col_type in new_columns:
            try:
                cursor.execute(f"ALTER TABLE usuarios ADD COLUMN {col_name} {col_type}")
                print(f"Coluna {col_name} adicionada com sucesso")
            except sqlite3.OperationalError as e:
                if "duplicate column name" not in str(e):
                    print(f"Aviso: {str(e)}")
        
        # Adiciona índices
        print("\nCriando índices...")
        indices = [
            "CREATE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios(email)",
            "CREATE INDEX IF NOT EXISTS idx_usuarios_cpf ON usuarios(cpf)",
            "CREATE INDEX IF NOT EXISTS idx_usuarios_escola ON usuarios(escola_id)",
            "CREATE INDEX IF NOT EXISTS idx_usuarios_tipo ON usuarios(tipo_usuario_id)"
        ]
        
        for index in indices:
            try:
                cursor.execute(index)
                print(f"Índice criado: {index}")
            except sqlite3.OperationalError as e:
                print(f"Aviso ao criar índice: {str(e)}")
        
        # Adiciona triggers de validação
        print("\nAdicionando triggers de validação...")
        cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS validate_usuario_insert
        BEFORE INSERT ON usuarios
        BEGIN
            -- Verifica email único
            SELECT CASE 
                WHEN NEW.email IS NOT NULL AND EXISTS (
                    SELECT 1 FROM usuarios WHERE email = NEW.email AND id != NEW.id
                )
                THEN RAISE(ABORT, 'Email já existe')
            END;
            
            -- Verifica formato do email
            SELECT CASE 
                WHEN NEW.email IS NOT NULL AND NEW.email NOT LIKE '%_@_%._%'
                THEN RAISE(ABORT, 'Formato de email inválido')
            END;
            
            -- Verifica formato do CPF
            SELECT CASE 
                WHEN NEW.cpf IS NOT NULL AND length(replace(replace(NEW.cpf, '.', ''), '-', '')) != 11
                THEN RAISE(ABORT, 'Formato de CPF inválido')
            END;
        END;
        """)
        
        cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS validate_usuario_update
        BEFORE UPDATE ON usuarios
        BEGIN
            -- Verifica email único
            SELECT CASE 
                WHEN NEW.email IS NOT NULL AND EXISTS (
                    SELECT 1 FROM usuarios WHERE email = NEW.email AND id != NEW.id
                )
                THEN RAISE(ABORT, 'Email já existe')
            END;
            
            -- Verifica formato do email
            SELECT CASE 
                WHEN NEW.email IS NOT NULL AND NEW.email NOT LIKE '%_@_%._%'
                THEN RAISE(ABORT, 'Formato de email inválido')
            END;
            
            -- Verifica formato do CPF
            SELECT CASE 
                WHEN NEW.cpf IS NOT NULL AND length(replace(replace(NEW.cpf, '.', ''), '-', '')) != 11
                THEN RAISE(ABORT, 'Formato de CPF inválido')
            END;
            
            -- Atualiza data_atualizacao_senha se a senha foi alterada
            SELECT CASE 
                WHEN NEW.senha != OLD.senha
                THEN 
                    NEW.data_atualizacao_senha = CURRENT_TIMESTAMP
            END;
        END;
        """)
        print("Triggers de validação criados com sucesso")
        
        # Atualiza registros existentes
        print("\nAtualizando registros existentes...")
        try:
            cursor.execute("""
            UPDATE usuarios 
            SET data_atualizacao_senha = CURRENT_TIMESTAMP,
                tentativas_login = COALESCE(tentativas_login, 0),
                bloqueado = COALESCE(bloqueado, 0)
            """)
            print("Registros atualizados com sucesso")
        except Exception as e:
            print(f"Aviso ao atualizar registros: {str(e)}")
        
        conn.commit()
        print("Melhorias de segurança implementadas com sucesso!")
        
        # Verifica e reporta o status
        cursor.execute("PRAGMA index_list('usuarios')")
        indices = cursor.fetchall()
        print("\nÍndices ativos:")
        for idx in indices:
            print(f"- {idx[1]}")
        
        cursor.execute("SELECT * FROM usuarios LIMIT 1")
        colunas = [description[0] for description in cursor.description]
        print("\nColunas da tabela usuarios:")
        for col in colunas:
            print(f"- {col}")
            
    except Exception as e:
        conn.rollback()
        print(f"\nErro durante a atualização: {str(e)}")
        print("Restaurando backup...")
        try:
            cursor.execute("DROP TABLE IF EXISTS usuarios")
            cursor.execute("ALTER TABLE usuarios_backup RENAME TO usuarios")
            print("Backup restaurado com sucesso")
        except Exception as restore_error:
            print(f"Erro ao restaurar backup: {str(restore_error)}")
            print("IMPORTANTE: Verifique manualmente o estado do banco de dados!")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    enhance_security()
