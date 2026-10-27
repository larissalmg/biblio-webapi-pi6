# Teste das rotas da API

O script `test_api_routes.py` faz um smoke test das principais rotas HTTP da API. Ele autentica pelo endpoint de login e usa o token recebido para consultar as rotas protegidas.

## Pré-requisitos

- Python 3 instalado. O script usa apenas a biblioteca padrão do Python, sem pacotes adicionais.
- API em execução e acessível pela máquina. Com a configuração Docker deste projeto, a URL padrão é `http://localhost:8000`.
- Usuário e senha válidos para acessar a API.

## Como executar

Na raiz do repositório, rode:

```bash
python test/test_api_routes.py
```

O script solicitará o usuário e a senha. A senha é digitada sem aparecer na tela e não é gravada pelo script.

Para usar outra URL base:

```bash
python test/test_api_routes.py --base-url http://localhost:8000
```

Também é possível consultar as opções com:

```bash
python test/test_api_routes.py --help
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

O resultado informa se cada chamada teve sucesso e mostra contagens, sem imprimir os registros de usuários ou empréstimos.

## Interpretação de erros

- `HTTP 401` ou `HTTP 403`: credenciais inválidas ou conta sem permissão para alguma rota.
- `Falha de conexão`: confirme se os containers estão ativos e se a API está acessível na URL informada.
- `HTTP 5xx`: a API respondeu, mas ocorreu um erro no servidor; confira os logs do container `api`.

O script só faz login e requisições `GET`; não cria, altera ou exclui dados.