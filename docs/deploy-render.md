# Ambiente de testes: Render + Neon

Esta publicação usa um banco Neon separado do PostgreSQL local. Não envie o
`.env` local, dados pessoais ou backups para o Git. Selecione o plano **Free**
nas duas plataformas. O serviço pode suspender por inatividade ou limites.

## Render

- Repositório: `gabbrielsilva/meu-financeiro`, branch `codex/foundation`.
- Runtime: Python 3; variável `PYTHON_VERSION=3.12.14`.
- Região: Ohio, a mesma do projeto Neon.
- Build: `bash scripts/render-build.sh`.
- Start: `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 1 --threads 2 --timeout 60`.
- Health check: `/entrar/`.

O build aplica migrações no banco online. Não usa o banco local. Antes de futuras
migrações com dados importantes, faça backup e revise compatibilidade com a versão
anterior. O plano gratuito não dispõe de comando separado de pré-deploy.

## Variáveis no painel (nunca no Git)

- `DJANGO_ENV=production`, `DJANGO_DEBUG=false`.
- `DJANGO_SECRET_KEY`: gerar uma chave exclusiva com pelo menos 50 caracteres.
- `DJANGO_ALLOWED_HOSTS`: hostname exato atribuído pelo Render, sem protocolo.
- `DJANGO_CSRF_TRUSTED_ORIGINS`: endereço HTTPS desse hostname.
- `DJANGO_TRUST_PROXY_HEADERS=true`: somente no serviço atrás do proxy Render.
- `DJANGO_HSTS_SECONDS=0` inicialmente; elevar após verificar HTTPS.
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST` e
  `POSTGRES_PORT`: conexão do projeto Neon `meu-financeiro-teste`.
- `POSTGRES_SSLMODE=verify-full` e
  `POSTGRES_SSLROOTCERT=.local/ca-bundle.pem`. O build copia as autoridades
  certificadoras do pacote certifi fixado nas dependências de deploy, sem depender
  do bundle antigo da imagem de hospedagem. A validação completa permanece ativa.

Não adivinhe IPs de proxy nem use curingas para confiar em cabeçalhos. Enquanto
`DJANGO_TRUSTED_PROXY_IPS` não estiver configurado com IPs verificados, o limite
de login usa o endereço do proxy e pode ser compartilhado entre visitantes.

## Verificação antes de considerar concluído

Confirmar migrações e a collation `und-x-icu` no Neon; abrir o endereço HTTPS;
verificar estáticos, CSRF, cookies Secure, cadastro, login, isolamento entre duas
contas, criação/edição/exclusão de movimento e logout. Verificar redirecionamento
HTTP e que cabeçalhos enviados pelo visitante não burlam a proteção do proxy.

O cadastro continua público. Usar dados fictícios nesta fase. Não tratar este
ambiente como repositório único de dados financeiros: backup externo e restauração
validada ainda precisam ser configurados antes de uso cotidiano.
