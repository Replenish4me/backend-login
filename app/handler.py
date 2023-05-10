import boto3
import json
import pymysql
import uuid
import hashlib
import datetime

def lambda_handler(event, context):
    
    # Leitura dos parâmetros da requisição
    email = event['email']
    senha = event['senha']
    senha = hashlib.sha256(bytes(senha, 'utf-8')).hexdigest()

    secretsmanager = boto3.client('secretsmanager')
    response = secretsmanager.get_secret_value(SecretId=f'replenish4me-db-password-{os.environ.get("env", "dev")}')
    db_password = response['SecretString']
    rds = boto3.client('rds')
    response = rds.describe_db_instances(DBInstanceIdentifier=f'replenish4medatabase{os.environ.get("env", "dev")}')
    endpoint = response['DBInstances'][0]['Endpoint']['Address']
    # Conexão com o banco de dados
    with pymysql.connect(
        host=endpoint,
        user='admin',
        password=db_password,
        database='replenish4me'
    ) as conn:
    
        # Verificação das credenciais do usuário
        with conn.cursor() as cursor:
            sql = "SELECT id, nome, senha FROM Usuarios WHERE email = %s"
            cursor.execute(sql, (email,))
            result = cursor.fetchone()
            
            if result is None:
                conn.close()
                response = {
                    "statusCode": 401,
                    "headers": {
                        "Content-Type": "application/json",
                        "Access-Control-Allow-Origin": "*",
                    },
                    "body": json.dumps({"message": "Credenciais inválidas"})
                }
                return response
            
            usuario_id, nome, senha_hash = result
            
            if senha != senha_hash:
                conn.close()
                response = {
                    "statusCode": 401,
                    "headers": {
                        "Content-Type": "application/json",
                        "Access-Control-Allow-Origin": "*",
                    },
                    "body": json.dumps({"message": "Credenciais inválidas"})
                }
                return response
    
        # Geração de um token de sessão
        token = str(uuid.uuid4())
        
        with conn.cursor() as cursor:
            # Remoção de sessões antigas do mesmo usuário
            sql = "DELETE FROM SessoesAtivas WHERE usuario_id = %s"
            cursor.execute(sql, (usuario_id,))
            conn.commit()
            
            # Inserção da nova sessão
            ultima_atividade = datetime.datetime.now()
            sql = "INSERT INTO SessoesAtivas (id, usuario_id, ultima_atividade) VALUES (%s, %s, %s)"
            cursor.execute(sql, (token, usuario_id, ultima_atividade))
            conn.commit()

    # Retorno da resposta da função
    response = {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps({"token": token, "nome": nome})
    }
    return response
