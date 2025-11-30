#========================================================================
# Copyright Universidade Federal do Espirito Santo (Ufes)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# 
# This program is released under license GNU GPL v3+ license.
#
#========================================================================

FROM amazon/dynamodb-local:latest

USER root

# Instalação de dependências
RUN yum install -y unzip jq
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
RUN unzip awscliv2.zip
RUN ./aws/install

# Copia scripts
COPY init/ /init/
RUN chmod +x /init/init.sh

# --- ADIÇÃO IMPOTANTE ---
# Cria o diretório de dados explicitamente e ajusta permissões
RUN mkdir -p /home/dynamodblocal/data && chmod 777 /home/dynamodblocal/data

# Define explicitamente o diretório de trabalho para garantir que o .jar seja encontrado
WORKDIR /home/dynamodblocal