# DynamoDB RBAC & SQL Simulator

Este projeto implementa uma camada de segurança e abstração sobre o **DynamoDB Local**, simulando um sistema de gerenciamento de banco de dados relacional (RDBMS). O sistema oferece autenticação de usuários, Controle de Acesso Baseado em Papéis (RBAC) e um interpretador de comandos SQL (SELECT, INSERT, UPDATE, DELETE).

## 🎯 Objetivo
Demonstrar como implementar autenticação e autorização manual em bancos NoSQL, onde tais recursos não são nativos ou dependem de serviços de nuvem externos (como AWS IAM), focando em ambientes de desenvolvimento local.

## 🚀 Funcionalidades
* **Autenticação:** Login seguro com ocultação de senha.
* **Autorização RBAC:**
    * **Admin:** Acesso total.
    * **Writer:** Leitura e Escrita.
    * **Reader:** Apenas Leitura.
* **SQL Parser:** Permite interagir com o DynamoDB usando sintaxe SQL padrão.
* **Inicialização Automática:** Scripts que criam tabelas e populam dados via Docker.

## 🛠️ Tecnologias
* Python 3 + Boto3
* Docker & Docker Compose
* Amazon DynamoDB Local
* AWS CLI & jq

## ⚙️ Como Executar

### 1. Pré-requisitos
* Docker e Docker Compose instalados.
* Python 3 instalado (para rodar o cliente CLI).

### 2. Subindo o Banco de Dados
Execute o comando abaixo na raiz do projeto para iniciar o DynamoDB e popular as tabelas:

```bash
docker-compose up --build
```

### 3. Rodando o Código
Execute o comando abaixo na raiz do projeto para iniciar a função de SQL Parser para testar as funcionalidades:

```bash
python app/main.py
```