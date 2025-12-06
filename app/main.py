import boto3
import sys
import getpass
import json
import os
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr
from decimal import Decimal

# --- CONFIGURAÇÃO ---
ENDPOINT = os.getenv('DYNAMO_ENDPOINT', 'http://localhost:8000')

dynamodb = boto3.resource(
    'dynamodb',
    endpoint_url=ENDPOINT,
    region_name='us-west-2',
    aws_access_key_id='local',
    aws_secret_access_key='local'
)

# --- UTILITÁRIOS ---
# Helper para converter Decimal do DynamoDB em float/int para visualização
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return int(o) if o % 1 == 0 else float(o)
        return super(DecimalEncoder, self).default(o)

def print_json(data):
    print(json.dumps(data, indent=2, cls=DecimalEncoder, ensure_ascii=False))

# --- AUTENTICAÇÃO ---
def authenticate():
    print(f"\n=== DYNAMODB SHELL (Conectado em {ENDPOINT}) ===")
    print("Digite suas credenciais.")
    username = input("Login: ").strip()
    password = input("Senha: ").strip() # Input simples para evitar problemas de buffer

    try:
        users_table = dynamodb.Table('users')
        roles_table = dynamodb.Table('roles')
        
        # Busca usuário
        response = users_table.get_item(Key={'username': username})
        user = response.get('Item')

        # Verifica senha (Texto plano conforme seu setup atual)
        if not user or user['password'] != password:
            print("❌ Acesso Negado: Login ou senha inválidos.")
            return None

        # Busca Role e Permissões
        role_name = user.get('role', 'NENHUMA')
        permissions = []
        if role_name != 'NENHUMA':
            role_resp = roles_table.get_item(Key={'role_name': role_name})
            if 'Item' in role_resp:
                permissions = role_resp['Item'].get('permissions', [])

        print(f"✅ Logado como: {username} | Role: {role_name}")
        return {'username': username, 'role': role_name, 'permissions': permissions}
    
    except Exception as e:
        print(f"❌ Erro de conexão ao autenticar: {e}")
        return None

# --- OPERAÇÕES ---

def do_put_item(session, table_name, data_str):
    if 'INSERT' not in session['permissions'] and 'UPDATE' not in session['permissions']:
        print(f"🚫 ERRO: Role '{session['role']}' não pode escrever (INSERT/UPDATE).")
        return

    try:
        item_data = json.loads(data_str)
        table = dynamodb.Table(table_name)
        table.put_item(Item=item_data)
        print("✅ Item salvo com sucesso (PutItem).")
    except json.JSONDecodeError:
        print("❌ Erro: JSON inválido. Use aspas duplas. Ex: {\"pk\": \"1\"}")
    except Exception as e:
        print(f"❌ Erro no DynamoDB: {e}")

def do_get_item(session, table_name, data_str):
    if 'READ' not in session['permissions']:
        print(f"🚫 ERRO: Role '{session['role']}' não pode ler (READ).")
        return

    try:
        key_data = json.loads(data_str)
        table = dynamodb.Table(table_name)
        response = table.get_item(Key=key_data)
        
        if 'Item' in response:
            print_json(response['Item'])
        else:
            print("ℹ️ Item não encontrado.")
            
    except json.JSONDecodeError:
        print("❌ Erro: JSON da chave inválido.")
    except Exception as e:
        print(f"❌ Erro no DynamoDB: {e}")

def do_delete_item(session, table_name, data_str):
    if 'DELETE' not in session['permissions']:
        print(f"🚫 ERRO: Role '{session['role']}' não pode deletar (DELETE).")
        return

    try:
        key_data = json.loads(data_str)
        table = dynamodb.Table(table_name)
        table.delete_item(Key=key_data)
        print("✅ Item deletado (DeleteItem).")
    except json.JSONDecodeError:
        print("❌ Erro: JSON da chave inválido.")
    except Exception as e:
        print(f"❌ Erro no DynamoDB: {e}")

def do_scan(session, table_name):
    if 'READ' not in session['permissions']:
        print(f"🚫 ERRO: Role '{session['role']}' não pode ler (READ).")
        return

    try:
        table = dynamodb.Table(table_name)
        response = table.scan()
        items = response.get('Items', [])
        print(f"--- Scan: {len(items)} itens encontrados ---")
        print_json(items)
    except Exception as e:
        print(f"❌ Erro no DynamoDB: {e}")

# --- LOOP PRINCIPAL ---
def main_loop():
    session = authenticate()
    if not session: return

    print("\nComandos Disponíveis (Sintaxe JSON):")
    print("  put-item <tabela> {\"chave\": \"valor\", \"attr\": 123}")
    print("  get-item <tabela> {\"pk\": \"valor\"}")
    print("  delete-item <tabela> {\"pk\": \"valor\"}")
    print("  scan <tabela>")
    print("  exit")

    while True:
        try:
            command_line = input(f"\nDynamoDB:{session['role']}> ").strip()
            if not command_line: continue

            parts = command_line.split(' ', 2)
            cmd = parts[0].lower()

            if cmd in ['exit', 'quit']:
                break

            if cmd == 'scan':
                if len(parts) < 2:
                    print("Uso: scan <tabela>")
                else:
                    do_scan(session, parts[1])
                continue

            # Para comandos que exigem JSON (put, get, delete)
            if len(parts) < 3:
                print(f"Uso incorreto. Exemplo: {cmd} tabela {{\"chave\": \"valor\"}}")
                continue

            table_name = parts[1]
            json_payload = parts[2]

            if cmd == 'put-item':
                do_put_item(session, table_name, json_payload)
            elif cmd == 'get-item':
                do_get_item(session, table_name, json_payload)
            elif cmd == 'delete-item':
                do_delete_item(session, table_name, json_payload)
            else:
                print("❓ Comando desconhecido.")

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Erro fatal no loop: {e}")

if __name__ == '__main__':
    main_loop()