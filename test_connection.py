import pymysql

try:
    connection = pymysql.connect(
        host='127.0.0.1',
        port=3306,
        user='mila_user',
        password='31952814Gg@',
        database='mila_educacional'
    )
    print("Conexão bem sucedida!")
    connection.close()
except Exception as e:
    print(f"Erro ao conectar: {e}")
