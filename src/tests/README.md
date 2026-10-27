# Teste das rotas da API

O script `test_api_routes.py` faz um smoke test das principais rotas HTTP da API.
Ele solicita as credenciais, autentica pelo endpoint de login e só então consulta
as rotas protegidas usando o token recebido.

## Pré-requisitos

- Python 3 instalado. O script usa apenas a biblioteca padrão do Python, sem pacotes adicionais.
- API em execução e acessível pela máquina. Com a configuração Docker deste projeto, a URL padrão é `http://localhost:8000`.
- Usuário e senha válidos para acessar a API.

## Como executar

Na raiz do repositório, rode:

```bash
python3 -m src.tests.test_api_routes
```

O script solicitará o usuário e a senha. A senha é digitada sem aparecer na tela e não é gravada pelo script.

Para usar outra URL base:

```bash
python3 -m src.tests.test_api_routes --base-url http://localhost:8000
```

Também é possível consultar as opções com:

```bash
python3 -m src.tests.test_api_routes --help
```

## Rotas verificadas

Após autenticar, o script consulta:

- `GET /gestor/livros/`
- `GET /gestor/unidades/`
- `GET /gestor/livro-unidades/`
- `GET /gestor/usuarios/`
- `GET /gestor/emprestimos/`
- `GET /gestor/dados-iniciais/`
- `GET /gestor/analytics/resumo/`
- `GET /gestor/analytics/territorio/`
- `GET /gestor/analytics/powerbi/`
- `GET /gestor/analytics/gestao-livros/`
- `GET /gestor/analytics/gestao-livros/filtros/`

O resultado informa se cada chamada teve sucesso e mostra contagens, sem imprimir
os registros de usuários ou empréstimos. As rotas de analytics são chamadas somente
depois da autenticação bem-sucedida.

## Interpretação de erros

- `HTTP 401` ou `HTTP 403`: credenciais inválidas ou conta sem permissão para alguma rota.
- `Falha de conexão`: confirme se os containers estão ativos e se a API está acessível na URL informada.
- `HTTP 5xx`: a API respondeu, mas ocorreu um erro no servidor; confira os logs do container `api`.

O script só faz login e requisições `GET`; não cria, altera ou exclui dados.
