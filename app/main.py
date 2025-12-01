import boto3
import sys
import getpass
import re
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr

# config inicial
dynamodb = boto3.resource(
    'dynamodb',
    endpoint_url='http://localhost:8000',
    region_name='us-west-2',
    aws_access_key_id='local',
    aws_secret_access_key='local'
)

# autenticaçao
def authenticate():
    print("\n=== SQL DYNAMODB FINAL (SELECT, INSERT, UPDATE, DELETE) ===")
    username = input("Login: ").strip()
    password = getpass.getpass("Senha: ").strip()

    users_table = dynamodb.Table('users')
    roles_table = dynamodb.Table('roles')

    response = users_table.get_item(Key={'username': username})
    user = response.get('Item')

    if not user or user['password'] != password:
        print("❌ Login ou senha inválidos.")
        return None

    role_name = user.get('role', 'NENHUMA')
    permissions = []

    if role_name != 'NENHUMA':
        role_resp = roles_table.get_item(Key={'role_name': role_name})
        if 'Item' in role_resp:
            permissions = role_resp['Item'].get('permissions', [])

    print(f"✅ Usuário: {username} | Role: {role_name}")
    return {'username': username, 'role': role_name, 'permissions': permissions}

# imprime itens
def print_items(items):
    if not items:
        print("0 rows returned.")
        return

    all_keys = set()
    for item in items:
        all_keys.update(item.keys())
    
    headers = list(all_keys)
    headers.sort()

    header_str = " | ".join([f"{h:<15}" for h in headers])
    separator = "-" * len(header_str)
    
    print(f"\n{separator}")
    print(header_str)
    print(separator)

    for item in items:
        row = []
        for h in headers:
            val = str(item.get(h, "NULL"))
            if len(val) > 15: val = val[:12] + "..."
            row.append(f"{val:<15}")
        print(" | ".join(row))
    
    print(separator)
    print(f"Total: {len(items)} rows.\n")


# parse
def execute_select(session, command):
    if 'READ' not in session['permissions']:
        print(f"🚫 ERRO: Role '{session['role']}' sem permissão READ.")
        return

    match = re.search(r"SELECT\s+\*\s+FROM\s+(\w+)(\s+WHERE\s+(.*))?", command, re.IGNORECASE)
    
    if match:
        table_name = match.group(1)
        where_clause = match.group(3)
        table = dynamodb.Table(table_name)
        items = []

        try:
            if where_clause:
                cond = re.search(r"(\w+)\s*=\s*'([^']*)'", where_clause)
                if cond:
                    key, val = cond.group(1), cond.group(2)
           
                    try:
                        resp = table.get_item(Key={key: val})
                        if 'Item' in resp:
                            items = [resp['Item']]
                        else:
                            items = []

                    except ClientError as e:
                        if e.response['Error']['Code'] == 'ValidationException':
                            print(f"ℹ️ Buscando por atributo não-chave '{key}' (modo SCAN)...")
                            resp = table.scan(FilterExpression=Attr(key).eq(val))
                            items = resp.get('Items', [])
                        else:
                            raise e
                else:
                    print("⚠️ WHERE complexo não suportado. Use: WHERE chave='valor'")
                    return
            
            else:
                resp = table.scan()
                items = resp.get('Items', [])

            print_items(items)

        except Exception as e:
            print(f"❌ Erro: {e}")
    else:
        print("❌ Sintaxe inválida.")

def execute_insert(session, command):
    if 'INSERT' not in session['permissions']:
        print(f"🚫 ERRO: Role '{session['role']}' sem permissão INSERT.")
        return

    match = re.search(r"INSERT\s+INTO\s+(\w+)\s+VALUES\s*\((.+)\)", command, re.IGNORECASE)
    
    if match:
        table_name = match.group(1)
        raw_args = match.group(2)
        item = {}
        
        try:
            pairs = raw_args.split(',')
            for pair in pairs:
                if '=' not in pair: raise ValueError("Formato key=val esperado")
                k, v = pair.split('=', 1)
                k = k.strip()
                v = v.strip()
                
                if (v.startswith("'") and v.endswith("'")) or (v.startswith('"') and v.endswith('"')):
                    v = v[1:-1]
                elif v.isdigit():
                    v = int(v)
                
                item[k] = v
            
            dynamodb.Table(table_name).put_item(Item=item)
            print("✅ Query OK, 1 row affected.")
            
        except Exception as e:
            print(f"❌ Erro na inserção: {e}")
    else:
        print("❌ Sintaxe inválida.")

def execute_update(session, command):
    if 'UPDATE' not in session['permissions']:
        print(f"🚫 ERRO: Role '{session['role']}' sem permissão UPDATE.")
        return

    regex = r"UPDATE\s+(\w+)\s+SET\s+(.+)\s+WHERE\s+(\w+)\s*=\s*'([^']*)'"
    match = re.search(regex, command, re.IGNORECASE)

    if match:
        table_name = match.group(1)
        set_clause = match.group(2)
        pk_key = match.group(3)
        pk_val = match.group(4)
        
        table = dynamodb.Table(table_name)
        
        update_parts = []
        expr_names = {}
        expr_values = {}
        
        try:
            updates = set_clause.split(',')
            for i, update in enumerate(updates):
                if '=' not in update: raise ValueError(f"Erro no SET: {update}")
                
                k, v = update.split('=', 1)
                k = k.strip()
                v = v.strip()

                if (v.startswith("'") and v.endswith("'")) or (v.startswith('"') and v.endswith('"')):
                    v = v[1:-1]
                elif v.isdigit():
                    v = int(v)
                
                attr_alias = f"#attr{i}"
                val_alias = f":val{i}"
                
                update_parts.append(f"{attr_alias} = {val_alias}")
                expr_names[attr_alias] = k
                expr_values[val_alias] = v

            update_expression = "SET " + ", ".join(update_parts)
            
            table.update_item(
                Key={pk_key: pk_val},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expr_names,
                ExpressionAttributeValues=expr_values,
                ConditionExpression=f"attribute_exists({pk_key})" 
            )
            print(f"✅ Query OK, 1 row updated ({pk_val}).")

        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                print(f"❌ Erro: O registro com {pk_key}='{pk_val}' não existe.")
            else:
                print(f"❌ Erro DynamoDB: {e.response['Error']['Message']}")
        except ValueError as ve:
            print(f"❌ Erro de Sintaxe: {ve}")

    else:
        print("❌ Sintaxe inválida. Use: UPDATE tabela SET col=val WHERE pk='id'")

def execute_delete(session, command):
    if 'DELETE' not in session['permissions']:
        print(f"🚫 ERRO: Role '{session['role']}' sem permissão DELETE.")
        return

    match = re.search(r"DELETE\s+FROM\s+(\w+)\s+WHERE\s+(\w+)\s*=\s*'([^']*)'", command, re.IGNORECASE)
    if match:
        table_name, key, val = match.groups()
        try:
            dynamodb.Table(table_name).delete_item(Key={key: val})
            print("✅ Query OK, 1 row deleted.")
        except Exception as e:
            print(f"❌ Erro: {e}")
    else:
        print("❌ Sintaxe inválida.")

# main
def main_loop():
    session = authenticate()
    if not session: return

    print("\nComandos Suportados:")
    print("  SELECT * FROM table (WHERE key='value')")
    print("  INSERT INTO table VALUES (key1='value1', key2='value2'...)")
    print("  UPDATE table SET key1='value1', key2='value2' WHERE key='value'")
    print("  DELETE FROM table WHERE key='value'")
    print("  EXIT")

    while True:
        try:
            sql = input(f"\nSQL> ").strip()
            if not sql: continue
            
            upper = sql.upper()
            if upper in ['EXIT', 'QUIT']: break
            
            if upper.startswith('SELECT'): execute_select(session, sql)
            elif upper.startswith('INSERT'): execute_insert(session, sql)
            elif upper.startswith('UPDATE'): execute_update(session, sql)
            elif upper.startswith('DELETE'): execute_delete(session, sql)
            else: print("❓ Comando desconhecido.")
            
        except KeyboardInterrupt: break
        except Exception as e: print(f"Erro fatal: {e}")

if __name__ == '__main__':
    main_loop()