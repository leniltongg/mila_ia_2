from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

def limpar_banco():
    try:
        # Configurar conexão
        password = quote_plus("31952814Gg@")
        engine = create_engine(f'mysql+pymysql://mila_user:{password}@127.0.0.1/mila_educacional')
        
        with engine.begin() as conn:  # Usar begin() para gerenciar a transação
            print("\nIniciando limpeza do banco...")
            
            # Desabilitar verificação de chaves estrangeiras
            conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
            
            try:
                # Excluir registros de simulados_enviados
                result = conn.execute(text(
                    "DELETE FROM simulados_enviados"
                ))
                print(f"Excluídos {result.rowcount} registros de simulados_enviados")
                
                # Excluir registros de simulados_gerados_professor
                result = conn.execute(text(
                    "DELETE FROM simulados_gerados_professor"
                ))
                print(f"Excluídos {result.rowcount} registros de simulados_gerados_professor")
                
                # Excluir usuários (exceto admin)
                result = conn.execute(text(
                    "DELETE FROM usuarios WHERE id != 1"
                ))
                print(f"Excluídos {result.rowcount} usuários")
                
                # Excluir todas as turmas
                result = conn.execute(text("DELETE FROM turmas"))
                print(f"Excluídas {result.rowcount} turmas")
                
                # Excluir todas as escolas
                result = conn.execute(text("DELETE FROM escolas"))
                print(f"Excluídas {result.rowcount} escolas")
                
                # Reabilitar verificação de chaves estrangeiras
                conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))
                
                print("\nLimpeza concluída com sucesso!")
                
            except Exception as e:
                print(f"\nERRO: {str(e)}")
                raise
            
            finally:
                # Garantir que a verificação de chaves estrangeiras seja reabilitada
                conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))
                
    except Exception as e:
        print(f"\nERRO na conexão: {str(e)}")

if __name__ == '__main__':
    limpar_banco()
