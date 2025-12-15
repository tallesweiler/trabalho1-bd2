# Implementação de Autenticação e Autorização (RBAC) para DynamoDB Local

Este projeto implementa uma solução de **Middleware de Segurança** para o DynamoDB Local.

Em ambientes de produção na AWS, o controle de acesso é gerenciado pelo IAM. No entanto, o **DynamoDB Local** (usado para desenvolvimento e testes) não impõe restrições de acesso nativamente. Este projeto resolve essa lacuna implementando uma camada de aplicação em Python que simula um sistema de **Autenticação (Login)** e **Controle de Acesso Baseado em Papéis (RBAC)**.

## 📋 Funcionalidades

- **Autenticação de Usuários:** Sistema de login simulado verificando credenciais em uma tabela de usuários.
- **Controle de Acesso (RBAC):** Verificação de permissões baseada na *Role* do usuário (`ADMIN`, `GUEST`, etc.) antes de autorizar operações no banco.
- **CLI Interativo:** Interface de linha de comando que aceita instruções no formato JSON, similar à API nativa do DynamoDB.
- **Ambiente Dockerizado:** Infraestrutura completa (Banco, Inicializador e Aplicação) orquestrada via Docker Compose.
- **Persistência de Dados:** Uso de volumes Docker para garantir que os dados não sejam perdidos ao reiniciar os contêineres.

## 🛠️ Tecnologias Utilizadas

- **Linguagem:** Python 3.9
- **SDK AWS:** Boto3
- **Banco de Dados:** Amazon DynamoDB Local
- **Infraestrutura:** Docker & Docker Compose
- **Utilitários:** AWS CLI & JQ (para scripts de inicialização)

## 📂 Estrutura do Projeto

```text
/
├── docker-compose.yml   # Orquestração dos serviços
├── app/
│   ├── main.py          # Lógica principal (Middleware de Auth e CLI)
│   ├── Dockerfile       # Definição do container da aplicação Python
│   └── requirements.txt # Dependências (boto3)
├── init/
│   ├── init.sh          # Script de criação das tabelas e carga inicial
│   ├── Dockerfile       # Container temporário com AWS CLI
│   └── data/            # Arquivos JSON com dados de seed (users, roles)
└── dbdata/              # Volume persistente do banco (gerado automaticamente)
```

## 🚀 Como Executar

### Pré-requisitos

Certifique-se de ter o **Docker** e o **Docker Compose** instalados em sua máquina.

### Passo 1: Inicializar o Ambiente

Na raiz do projeto, execute o comando abaixo para construir as imagens e iniciar os serviços:

```bash
docker-compose up --build -d
```

> **Nota:** Na primeira execução, aguarde alguns segundos para que o container `dynamodb-init` configure as tabelas e insira os usuários padrão. Você pode verificar o progresso com `docker-compose logs -f dynamodb-init`.

### Passo 2: Acessar a Aplicação

O sistema não é acessado diretamente pelo host, mas sim através do container da aplicação (simulando um cliente remoto). Execute:

```bash
docker exec -it app-client python main.py
```

## 🔐 Credenciais de Teste

O banco de dados é inicializado com os seguintes usuários para validação das regras de negócio:

| Usuário     | Senha  | Role   | Permissões                                 |
|-------------|--------|--------|--------------------------------------------|
| admin  | 123 | admin  | read, insert, update, delete, manage_users |
| writer | 123 | writer | insert, update, delete                     |
| reader | 123 | reader | read                                       |
| comum  | 123 | none   |                                            |

## 📖 Guia de Comandos (Sintaxe)

A interface aceita comandos baseados na estrutura **JSON**.

> **⚠️ IMPORTANTE:** O formato JSON é estrito. Utilize **aspas duplas** (`"`) para chaves e strings.

### 1\. Listar Itens (Scan)

Varre a tabela inteira e lista os itens.
*Permissão Necessária: READ*

```bash
scan <tabela>
# Exemplo:
scan users
```

### 2\. Buscar Item Único (GetItem)

Busca um item específico pela sua Chave Primária.
*Permissão Necessária: READ*

```bash
get-item <tabela> <json_chave_primaria>
# Exemplo:
get-item users {"username": "admin_user"}
```

### 3\. Inserir ou Atualizar Item (PutItem)

Insere um novo item ou substitui um existente.
*Permissão Necessária: INSERT ou UPDATE*

```bash
put-item <tabela> <json_do_item>
# Exemplo:
put-item products {"id": "101", "nome": "Teclado", "preco": 150}
```

### 4\. Deletar Item (DeleteItem)

Remove um item do banco.
*Permissão Necessária: DELETE*

```bash
delete-item <tabela> <json_chave_primaria>
# Exemplo:
delete-item products {"id": "101"}
```

### 5\. Sair

Encerra a aplicação.

```bash
exit
```

## 🧪 Roteiro de Testes (Validação)

Para validar a robustez e a segurança da solução, execute os seguintes cenários:

1.  **Cenário de Bloqueio (Autorização Negada)**

      * Faça login com `guest_user`.
      * Tente executar um comando de escrita: `delete-item users {"username": "admin_user"}`.
      * **Resultado:** O sistema deve exibir `🚫 ERRO` informando que a Role GUEST não possui permissão `DELETE`.

2.  **Cenário de Sucesso (Autorização Concedida)**

      * Faça login com `admin_user`.
      * Execute um comando de escrita: `put-item roles {"role_name": "TESTER", "permissions": ["READ"]}`.
      * **Resultado:** O sistema deve exibir `✅ Item salvo com sucesso`.

3.  **Cenário de Persistência**

      * Insira um dado como Admin.
      * Saia do sistema e reinicie os containers (`docker-compose restart`).
      * Logue novamente e busque o dado inserido. Ele deve permanecer salvo.

-----

*Projeto desenvolvido para a disciplina de Bancos de Dados 2.*
