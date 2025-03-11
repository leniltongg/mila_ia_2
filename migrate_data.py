import sqlite3
import pymysql
from app_db import app
import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

load_dotenv()

# Conectar ao SQLite
sqlite_conn = sqlite3.connect('educacional.db')
sqlite_cursor = sqlite_conn.cursor()

# Configurar conexão MySQL
mysql_conn = pymysql.connect(
    host='127.0.0.1',
    user='mila_user',
    password='31952814Gg@',
    database='mila_educacional'
)
mysql_cursor = mysql_conn.cursor()

# Mapeamento de colunas antigas para novas
column_mappings = {
    'cidades': {
        'old_columns': ['id', 'codigo_ibge', 'nome', 'estado', 'codigo_inep'],
        'new_columns': ['id', 'codigo_ibge', 'nome', 'estado', 'codigo_inep']
    },
    'usuarios': {
        'old_columns': ['id', 'tipo_registro', 'codigo_inep_escola', 'cpf', 'email', 'senha', 'nome', 'data_nascimento', 'mae', 'pai', 'sexo', 'codigo_ibge', 'cep', 'escola_id', 'tipo_ensino_id', 'ano_escolar_id', 'turma_id', 'tipo_usuario_id', 'cidade_id'],
        'new_columns': ['id', 'tipo_registro', 'codigo_inep_escola', 'cpf', 'email', 'senha', 'nome', 'data_nascimento', 'mae', 'pai', 'sexo', 'codigo_ibge', 'cep', 'escola_id', 'tipo_ensino_id', 'ano_escolar_id', 'turma_id', 'tipo_usuario_id', 'cidade_id'],
        'required_columns': ['id', 'tipo_registro', 'nome', 'tipo_usuario_id', 'cidade_id']  # Apenas estas colunas não podem ser nulas
    },
    'escolas': {
        'old_columns': ['id', 'tipo_de_registro', 'codigo_inep', 'nome_da_escola', 'cep', 'codigo_ibge', 'endereco', 'numero', 'complemento', 'bairro', 'ddd', 'telefone', 'telefone_2', 'email', 'ensino_fundamental'],
        'new_columns': ['id', 'tipo_de_registro', 'codigo_inep', 'nome_da_escola', 'cep', 'codigo_ibge', 'endereco', 'numero', 'complemento', 'bairro', 'ddd', 'telefone', 'telefone_2', 'email', 'ensino_fundamental']
    },
    'Ano_escolar': {
        'old_columns': ['id', 'nome'],
        'new_columns': ['id', 'nome']
    },
    'turmas': {
        'old_columns': ['id', 'tipo_de_registro', 'codigo_inep', 'escola_id', 'tipo_ensino_id', 'ano_escolar_id', 'turma'],
        'new_columns': ['id', 'tipo_de_registro', 'codigo_inep', 'escola_id', 'tipo_ensino_id', 'ano_escolar_id', 'turma']
    },
    'simulado_questoes': {
        'old_columns': ['id', 'simulado_id', 'questao_id'],
        'new_columns': ['id', 'simulado_id', 'questao_id'],
        'required_columns': ['id', 'simulado_id']  # Apenas id e simulado_id são obrigatórios
    }
}

try:
    # Desabilitar verificação de chave estrangeira
    mysql_cursor.execute("SET FOREIGN_KEY_CHECKS=0")
    
    # Limpar todas as tabelas
    mysql_cursor.execute("SHOW TABLES")
    tables = mysql_cursor.fetchall()
    
    for table in tables:
        table_name = table[0]
        if table_name != 'alembic_version':
            print(f"Limpando tabela: {table_name}")
            mysql_cursor.execute(f"TRUNCATE TABLE {table_name}")
    
    # Primeiro, inserir dados nas tabelas base
    base_tables = ['tipos_usuarios', 'tipos_ensino', 'meses', 'disciplinas']
    
    for table in base_tables:
        print(f"Migrando tabela: {table}")
        
        # Pegar os dados do SQLite
        sqlite_cursor.execute(f"SELECT * FROM {table}")
        rows = sqlite_cursor.fetchall()
        
        if not rows:
            print(f"Tabela {table} está vazia")
            continue
            
        # Pegar os nomes das colunas
        sqlite_cursor.execute(f"PRAGMA table_info({table})")
        columns = sqlite_cursor.fetchall()
        column_names = [column[1] for column in columns]
        
        # Preparar a query de inserção
        placeholders = ', '.join(['%s'] * len(column_names))
        columns_str = ', '.join(column_names)
        insert_query = f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})"
        
        # Inserir os dados no MySQL
        try:
            mysql_cursor.executemany(insert_query, rows)
            mysql_conn.commit()
            print(f"Migrados {len(rows)} registros para {table}")
        except Exception as e:
            print(f"Erro ao migrar {table}: {str(e)}")
            mysql_conn.rollback()

    # Depois, migrar as tabelas com mapeamento especial
    for table, mapping in column_mappings.items():
        print(f"Migrando tabela: {table}")
        
        # Pegar os dados do SQLite
        old_columns = ', '.join(mapping['old_columns'])
        try:
            # Verificar se todas as colunas existem
            for col in mapping['old_columns']:
                sqlite_cursor.execute(f"PRAGMA table_info({table})")
                columns = sqlite_cursor.fetchall()
                column_names = [column[1] for column in columns]
                if col not in column_names:
                    print(f"Aviso: Coluna {col} não encontrada na tabela {table} do SQLite")
                    continue

            sqlite_cursor.execute(f"SELECT {old_columns} FROM {table}")
            rows = sqlite_cursor.fetchall()
            
            if not rows:
                print(f"Tabela {table} está vazia")
                continue
            
            # Preparar a query de inserção
            new_columns = mapping['new_columns']
            placeholders = ', '.join(['%s'] * len(new_columns))
            columns_str = ', '.join(new_columns)
            insert_query = f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})"
            
            # Filtrar linhas com valores nulos em colunas obrigatórias
            filtered_rows = []
            required_columns = mapping.get('required_columns', new_columns)  # Se não especificado, todas são obrigatórias
            required_indices = [mapping['old_columns'].index(col) for col in required_columns]
            
            for row in rows:
                # Verifica apenas as colunas obrigatórias
                if all(row[idx] is not None for idx in required_indices):
                    # Substitui None por valores padrão para outras colunas
                    row_list = list(row)
                    for i in range(len(row_list)):
                        val = row_list[i]
                        if val is None or val == 'null' or val == '':  # Tratar 'null' e string vazia como None
                            if i not in required_indices:
                                row_list[i] = None  # Sempre usar None para campos opcionais
                    filtered_rows.append(tuple(row_list))
            
            if filtered_rows:
                # Inserir os dados no MySQL
                mysql_cursor.executemany(insert_query, filtered_rows)
                mysql_conn.commit()
                print(f"Migrados {len(filtered_rows)} registros para {table}")
            else:
                print(f"Nenhum registro válido para migrar em {table}")
        except Exception as e:
            print(f"Erro ao migrar {table}: {str(e)}")
            mysql_conn.rollback()

    # Por fim, migrar as tabelas de relacionamento
    relation_tables = [
        'professor_disciplina',
        'professor_turma_escola',
        'escola_tipos_ensino',
        'assuntos',
        'banco_questoes',
        'simulado_questoes',
        'simulado_questoes_professor',
        'simulados_gerados',
        'simulados_gerados_professor',
        'simulados_enviados',
        'aluno_simulado',
        'desempenho_simulado'
    ]

    for table in relation_tables:
        print(f"Migrando tabela: {table}")
        
        try:
            # Pegar os dados do SQLite
            sqlite_cursor.execute(f"SELECT * FROM {table}")
            rows = sqlite_cursor.fetchall()
            
            if not rows:
                print(f"Tabela {table} está vazia")
                continue
                
            # Pegar os nomes das colunas
            sqlite_cursor.execute(f"PRAGMA table_info({table})")
            columns = sqlite_cursor.fetchall()
            column_names = [column[1] for column in columns]
            
            # Preparar a query de inserção
            placeholders = ', '.join(['%s'] * len(column_names))
            columns_str = ', '.join(column_names)
            insert_query = f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})"
            
            # Inserir os dados no MySQL
            mysql_cursor.executemany(insert_query, rows)
            mysql_conn.commit()
            print(f"Migrados {len(rows)} registros para {table}")
        except Exception as e:
            print(f"Erro ao migrar {table}: {str(e)}")
            mysql_conn.rollback()

    # Reabilitar verificação de chave estrangeira
    mysql_cursor.execute("SET FOREIGN_KEY_CHECKS=1")

except Exception as e:
    print(f"Erro: {str(e)}")

finally:
    # Fechar conexões
    sqlite_cursor.close()
    sqlite_conn.close()
    mysql_cursor.close()
    mysql_conn.close()

print("Migração concluída!")
