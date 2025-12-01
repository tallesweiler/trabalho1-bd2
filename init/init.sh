#!/bin/bash

ENDPOINT="http://dynamodb-local:8000"
REGION="us-west-2"
DATA_DIR="/init/data"
TABLES_FILE="$DATA_DIR/tables.json"

echo "⏳ Aguardando DynamoDB em $ENDPOINT..."
until aws dynamodb list-tables --endpoint-url $ENDPOINT --region $REGION --no-cli-pager > /dev/null 2>&1; do
  sleep 2
done
echo "✅ DynamoDB online!"

# criando tabelas
if [ -f "$TABLES_FILE" ]; then
    echo "📂 Processando arquivo de estrutura: $TABLES_FILE"
    
    COUNT=$(jq '. | length' "$TABLES_FILE")
    
    for ((i=0; i<$COUNT; i++)); do
        TABLE_NAME=$(jq -r ".[$i].name" "$TABLES_FILE")
        ATTR_DEFS=$(jq -c ".[$i].attributeDefinitions" "$TABLES_FILE")
        KEY_SCHEMA=$(jq -c ".[$i].keySchema" "$TABLES_FILE")
        BILLING_MODE=$(jq -r ".[$i].billingMode" "$TABLES_FILE")

        echo "🔨 Criando tabela: $TABLE_NAME..."

        aws dynamodb create-table \
            --endpoint-url $ENDPOINT \
            --region $REGION \
            --table-name "$TABLE_NAME" \
            --attribute-definitions "$ATTR_DEFS" \
            --key-schema "$KEY_SCHEMA" \
            --billing-mode "$BILLING_MODE" \
            --no-cli-pager || echo "⚠️ Tabela $TABLE_NAME já existe ou erro."
    done
else
    echo "❌ Arquivo $TABLES_FILE não encontrado."
fi

# inserindo os dados
echo "📥 Iniciando carga de dados..."

for file in "$DATA_DIR"/*_batch.json; do
    if [ -f "$file" ]; then
        echo "💾 Inserindo dados de: $file"
        
        aws dynamodb batch-write-item \
            --endpoint-url $ENDPOINT \
            --region $REGION \
            --request-items "file://$file" \
            --no-cli-pager
            
        echo "✅ Lote processado."
    fi
done

echo "🚀 Inicialização completa!"