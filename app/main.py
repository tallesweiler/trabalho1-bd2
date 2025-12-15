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

# --- UTILITÁRIOS DE VISUALIZAÇÃO ---

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return int(o) if o % 1 == 0 else float(o)
        return super(DecimalEncoder, self).default(o)

def print_json(data):
    print(json.dumps(data, indent=2, cls=DecimalEncoder, ensure_ascii=False))

def print_table(items):
    if not items:
        print(" (Nenhum item encontrado)")
        return

    headers = set()
    for item in items:
        headers.update(item.keys())
    headers = sorted(list(headers))

    processed_rows = []
    for item in items:
        row = {}
        for h in headers:
            val = item.get(h, "NULL")
            if isinstance(val, Decimal):
                val = int(val) if val % 1 == 0 else float(val)
            val_str = str(val)
            if len(val_str) > 20:
                val_str = val_str[:17] + "..."
            row[h] = val_str
        processed_rows.append(row)

    col_widths = {}
    for h in headers:
        max_len = len(h)
        for row in processed_rows:
            max_len = max(max_len, len(row[h]))
        col_widths[h] = max_len + 2

    header_str = "".join([f"{h:<{col_widths[h]}}" for h in headers])
    print("-" * len(header_str))
    print(header_str)
    print("-" * len(header_str))

    for row in processed_rows:
        row_str = "".join([f"{row[h]:<{col_widths[h]}}" for h in headers])
        print(row_str)
    print("-" * len(header_str))
    print(f"Total: {len(items)} registros.\n")


# --- AUTENTICAÇÃO ---
def authenticate():
    print(f"\n=== DYNAMODB SHELL (Conectado em {ENDPOINT}) ===")
    print("Digite suas credenciais.")
    username = input("Login: ").strip()
    password = input("Senha: ").strip()

    try:
        users_table = dynamodb.Table('users')
        roles_table = dynamodb.Table('roles')
        
        response = users_table.get_item(Key={'username': username})
        user = response.get('Item')

        if not user or user['password'] != password:
            print("❌ Acesso Negado: Login ou senha inválidos.")
            return None

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

# --- UI HELPER ---
def show_help(session):
    perms = session['permissions']
    print("\nComandos Disponíveis (Baseado na sua Role):")
    
    if 'READ' in perms:
        print("  list-tables")
        print("  scan <tabela>")
        print("  get-item <tabela> {\"pk\": \"valor\"}")
    
    if 'INSERT' in perms:
        print("  put-item <tabela> <json> (Cria/Substitui item completo)")

    # --- NOVO COMANDO NA AJUDA ---
    if 'UPDATE' in perms:
        print("  update-item <tabela> <json> (Atualiza apenas campos informados)")
    
    if 'DELETE' in perms:
        print("  delete-item <tabela> {\"pk\": \"valor\"}")

    print("  help")
    print("  exit")

# --- OPERAÇÕES ---

def do_list_tables(session):
    if 'READ' not in session['permissions']:
        print(f"🚫 ERRO: Role '{session['role']}' não pode listar tabelas (Requer READ).")
        return
    try:
        print("\n--- Tabelas Disponíveis ---")
        count = 0
        for table in dynamodb.tables.all():
            print(f" 📂 {table.name}")
            count += 1
        if count == 0: print(" (Nenhuma tabela encontrada)")
        else: print(f"\n Total: {count} tabelas.")
    except Exception as e:
        print(f"❌ Erro no DynamoDB: {e}")

def do_put_item(session, table_name, data_str):
    if 'INSERT' not in session['permissions']:
        print(f"🚫 ERRO: Role '{session['role']}' não pode inserir (Requer INSERT).")
        return
    try:
        item_data = json.loads(data_str)
        dynamodb.Table(table_name).put_item(Item=item_data)
        print("✅ Item salvo/substituído com sucesso (PutItem).")
    except json.JSONDecodeError: print("❌ Erro: JSON inválido. Use aspas duplas.")
    except Exception as e: print(f"❌ Erro no DynamoDB: {e}")

# --- NOVA FUNÇÃO DE UPDATE ---
def do_update_item(session, table_name, data_str):
    if 'UPDATE' not in session['permissions']:
        print(f"🚫 ERRO: Role '{session['role']}' não pode atualizar (Requer UPDATE).")
        return

    try:
        input_data = json.loads(data_str)
        table = dynamodb.Table(table_name)
        
        # 1. Descobrir dinamicamente qual é a Chave Primária (PK) da tabela
        # table.key_schema retorna algo como [{'AttributeName': 'username', 'KeyType': 'HASH'}]
        pk_names = [k['AttributeName'] for k in table.key_schema]
        
        key_dict = {}
        update_attrs = {}

        # 2. Separar o que é Chave do que é Atributo para atualizar
        for k, v in input_data.items():
            if k in pk_names:
                key_dict[k] = v
            else:
                update_attrs[k] = v

        if not key_dict:
            print(f"❌ Erro: O JSON deve conter a chave primária da tabela {pk_names}.")
            return

        if not update_attrs:
            print("⚠️ Aviso: Nenhum atributo para atualizar fornecido.")
            return

        # 3. Construir a UpdateExpression (SET #a=:v, #b=:v2)
        # Usamos ExpressionAttributeNames (#) para evitar conflito com palavras reservadas (ex: 'role', 'name')
        update_expr_parts = []
        expr_names = {}
        expr_values = {}

        for i, (k, v) in enumerate(update_attrs.items()):
            key_alias = f"#attr{i}"
            val_alias = f":val{i}"
            
            update_expr_parts.append(f"{key_alias} = {val_alias}")
            expr_names[key_alias] = k
            expr_values[val_alias] = v

        update_expression = "SET " + ", ".join(update_expr_parts)

        # 4. Executar
        table.update_item(
            Key=key_dict,
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values
        )
        print("✅ Item atualizado com sucesso (UpdateItem).")

    except json.JSONDecodeError: print("❌ Erro: JSON inválido.")
    except Exception as e: print(f"❌ Erro no DynamoDB: {e}")
# -----------------------------

def do_get_item(session, table_name, data_str):
    if 'READ' not in session['permissions']:
        print(f"🚫 ERRO: Role '{session['role']}' não pode ler (READ).")
        return
    try:
        key_data = json.loads(data_str)
        response = dynamodb.Table(table_name).get_item(Key=key_data)
        if 'Item' in response:
            print("\n--- Item Encontrado ---")
            print_json(response['Item'])
        else: print("ℹ️ Item não encontrado.")
    except json.JSONDecodeError: print("❌ Erro: JSON da chave inválido.")
    except Exception as e: print(f"❌ Erro no DynamoDB: {e}")

def do_delete_item(session, table_name, data_str):
    if 'DELETE' not in session['permissions']:
        print(f"🚫 ERRO: Role '{session['role']}' não pode deletar (DELETE).")
        return
    try:
        key_data = json.loads(data_str)
        dynamodb.Table(table_name).delete_item(Key=key_data)
        print("✅ Item deletado (DeleteItem).")
    except json.JSONDecodeError: print("❌ Erro: JSON da chave inválido.")
    except Exception as e: print(f"❌ Erro no DynamoDB: {e}")

def do_scan(session, table_name):
    if 'READ' not in session['permissions']:
        print(f"🚫 ERRO: Role '{session['role']}' não pode ler (READ).")
        return
    try:
        response = dynamodb.Table(table_name).scan()
        print_table(response.get('Items', []))
    except Exception as e: print(f"❌ Erro no DynamoDB: {e}")

# --- LOOP PRINCIPAL ---
def main_loop():
    session = authenticate()
    if not session: return

    show_help(session)

    while True:
        try:
            command_line = input(f"\nDynamoDB:{session['role']}> ").strip()
            if not command_line: continue

            parts = command_line.split(' ', 2)
            cmd = parts[0].lower()

            if cmd in ['exit', 'quit']: break
            
            if cmd == 'help':
                show_help(session)
                continue

            if cmd == 'list-tables':
                do_list_tables(session)
                continue

            if cmd == 'scan':
                if len(parts) < 2: print("Uso: scan <tabela>")
                else: do_scan(session, parts[1])
                continue

            if len(parts) < 3:
                print(f"Uso incorreto. Exemplo: {cmd} tabela {{\"chave\": \"valor\"}}")
                continue

            table_name = parts[1]
            json_payload = parts[2]

            if cmd == 'put-item': do_put_item(session, table_name, json_payload)
            elif cmd == 'update-item': do_update_item(session, table_name, json_payload) # <--- Novo
            elif cmd == 'get-item': do_get_item(session, table_name, json_payload)
            elif cmd == 'delete-item': do_delete_item(session, table_name, json_payload)
            else: print("❓ Comando desconhecido. Digite 'help'.")

        except KeyboardInterrupt: break
        except Exception as e: print(f"Erro fatal no loop: {e}")

if __name__ == '__main__':
    main_loop()