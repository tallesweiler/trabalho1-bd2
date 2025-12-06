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

FROM amazon/aws-cli:latest

# Instala jq E dos2unix
RUN yum install -y jq dos2unix

COPY init.sh /init.sh
COPY data /data

# Converte o arquivo de Windows para Unix e torna executável
RUN dos2unix /init.sh && chmod +x /init.sh

WORKDIR /

ENTRYPOINT ["/bin/bash", "/init.sh"]
