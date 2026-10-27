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

## Estrutura JSON das rotas analíticas

Os exemplos abaixo mostram as chaves retornadas. Os valores são ilustrativos; listas
podem estar vazias conforme os dados cadastrados.

### `GET /gestor/analytics/resumo/`

```json
{
	"meta": {
		"escopo": "dados agregados da plataforma Bibliotecas Conectadas",
		"contém_dados_pessoais": false,
		"observacao": "Indicadores de acervo e circulação."
	},
	"resumo": {
		"titulos": 100,
		"exemplares": 965,
		"unidades": 6,
		"usuarios_ativos": 0,
		"emprestimos_total": 0,
		"emprestimos_abertos": 0,
		"emprestimos_devolvidos": 0
	},
	"acervo_por_genero": [
		{"genero": "Ficção", "titulos": 20, "exemplares": 120}
	],
	"acervo_por_tipo": [
		{"tipo_obra": "Livro", "titulos": 100, "exemplares": 965}
	],
	"por_unidade": [
		{
			"unidade_id": 1,
			"unidade": "Biblioteca Central",
			"ibge_bairro_codigo": "3548500005",
			"ibge_bairro_nome": "Aparecida",
			"latitude": "-23.979587",
			"longitude": "-46.314403",
			"titulos": 40,
			"exemplares": 210,
			"emprestimos_total": 0,
			"emprestimos_abertos": 0,
			"emprestimos_devolvidos": 0
		}
	]
}
```

`resumo` contém totais operacionais. `acervo_por_genero` e `acervo_por_tipo`
agrupam títulos e exemplares; `por_unidade` acrescenta localização territorial e
quantidades de empréstimos. Coordenadas e dados territoriais podem ser `null` quando
não cadastrados.

### `GET /gestor/analytics/territorio/`

```json
{
	"meta": {
		"fonte": "IBGE — Censo Demográfico 2022",
		"municipio": "Santos",
		"uf": "SP",
		"codigo_municipio_ibge": "3548500",
		"nivel_territorial": "bairro",
		"gerado_de_fontes_oficiais_em": "2026-10-08",
		"contem_dados_pessoais": false,
		"observacao": "Dados territoriais descritivos."
	},
	"cobertura": {
		"bairros_total": 55,
		"bairros_com_demografia": 55,
		"bairros_com_alfabetizacao": 55,
		"bairros_com_renda": 55,
		"bairros_com_faixas_etarias_completas": 55,
		"bairros_com_taxa_alfabetizacao": 55,
		"bairros_sem_renda": 0
	},
	"validacao": {
		"diferencas_total_basico_demografia": 0,
		"diferencas_total_demografia_faixas_etarias": 0,
		"renda_ausente_eh_zero": false
	},
	"bairros": [
		{
			"cd_bairro": "3548500005",
			"bairro": "Aparecida",
			"area_km2": 3.2,
			"populacao_total": 12345,
			"populacao_demografia": 12345,
			"idade_0_14": 1800,
			"idade_15_29": 2200,
			"idade_30_59": 5000,
			"idade_60_mais": 3000,
			"populacao_idade_classificada": 12000,
			"populacao_15_mais_alfabetizacao": 10000,
			"alfabetizados_15_mais": 9900,
			"taxa_alfabetizacao_15_mais_pct": 99.0,
			"responsaveis_dpp_ocupados": 4000,
			"renda_responsavel_media": 5000.0,
			"renda_responsavel_mediana": 3500.0,
			"renda_disponivel": true
		}
	]
}
```

`cobertura` resume quantos bairros possuem cada conjunto de indicadores; `validacao`
registra diferenças entre universos e informa que renda ausente não significa zero.
Cada item de `bairros` contém população, faixas etárias, alfabetização e rendimento
da pessoa responsável pelo domicílio. Valores suprimidos ou indisponíveis são `null`.
Filtros opcionais: `?codigo=<código IBGE>` e `?bairro=<trecho do nome>`.

### `GET /gestor/analytics/powerbi/`

```json
{
	"meta": {
		"dataset": "Bibliotecas Conectadas — PI4 — Power BI",
		"municipio": "Santos",
		"codigo_municipio_ibge": "3548500",
		"nivel_territorial": "bairro",
		"contem_dados_pessoais": false,
		"observacao": "Dataset agregado sem identificadores de leitores."
	},
	"periodo": {
		"primeiro_emprestimo": "2026-01-15",
		"ultimo_emprestimo": "2026-10-01",
		"ultima_devolucao": "2026-10-10"
	},
	"qualidade_ibge": {
		"bairros_total": 55,
		"bairros_com_renda": 55,
		"bairros_sem_renda": 0,
		"diferencas_total_basico_demografia": 0,
		"diferencas_total_demografia_faixas_etarias": 0
	},
	"dim_bairro": [],
	"dim_unidade": [],
	"fato_acervo": [],
	"fato_circulacao_mensal": [],
	"fato_devolucoes_mensal": [],
	"fato_titulos": []
}
```

As dimensões são listas de linhas analíticas. Cada objeto de `dim_bairro` tem as chaves
`cd_bairro`, `bairro`, `area_km2`, `populacao_total`, `populacao_demografia`,
`idade_0_14`, `idade_15_29`, `idade_30_59`, `idade_60_mais`,
`populacao_idade_classificada`, `populacao_15_mais_alfabetizacao`,
`alfabetizados_15_mais`, `taxa_alfabetizacao_15_mais_pct`,
`responsaveis_dpp_ocupados`, `renda_responsavel_media`,
`renda_responsavel_mediana` e `renda_disponivel`. Cada objeto de `dim_unidade` tem
`unidade_id`, `unidade`, `endereco`, `ibge_bairro_codigo`, `ibge_bairro_nome`,
`latitude` e `longitude`.

As linhas das tabelas fato têm estes campos:

- `fato_acervo`: `unidade_id`, `ibge_bairro_codigo`, `genero`, `tipo_obra`, `titulos`, `exemplares`, `emprestimos_abertos`, `exemplares_disponiveis`.
- `fato_circulacao_mensal`: `mes`, `unidade_id`, `ibge_bairro_codigo`, `genero`, `tipo_obra`, `emprestimos_iniciados`.
- `fato_devolucoes_mensal`: `mes`, `unidade_id`, `ibge_bairro_codigo`, `genero`, `tipo_obra`, `devolucoes`.
- `fato_titulos`: `unidade_id`, `ibge_bairro_codigo`, `livro_id`, `titulo`, `autor`, `isbn`, `genero`, `tipo_obra`, `emprestimos_total`, `emprestimos_abertos`, `exemplares_atuais`, `exemplares_disponiveis`.

Uma tabela fato pode vir vazia se ainda não houver registros, mas mantém a chave no
JSON. Nenhuma tabela contém nome, e-mail ou documento de leitor.

### `GET /gestor/analytics/gestao-livros/`

```json
{
	"meta": {
		"escopo": "indicadores agregados de livros e circulação",
		"contem_dados_pessoais": false,
		"filtros_aplicados": {
			"unidade_id": null,
			"genero_id": null,
			"ano_inicio": null,
			"ano_fim": null
		},
		"tendencia_de_cadastro_disponivel": false,
		"reservas_disponiveis": false,
		"observacao": "Evolução do acervo por publicação e circulação por mês."
	},
	"indicadores": {
		"titulos": 100,
		"autores_distintos": 90,
		"categorias": 12,
		"unidades_com_acervo": 6,
		"exemplares": 965,
		"emprestimos_abertos": 0
	},
	"situacao_exemplares": {
		"total": 965,
		"emprestados": 0,
		"disponiveis": 965,
		"reservados": null
	},
	"acervo_por_categoria": [],
	"acervo_por_unidade": [],
	"top_autores": [],
	"publicacoes_por_decada": [],
	"titulos_sem_data_publicacao": 0,
	"circulacao_mensal": [],
	"emprestimos_recentes": []
}
```

`indicadores` contém os cartões da dashboard; as listas agrupam o acervo por categoria
e unidade, os dez autores com mais títulos, publicações por década, circulação mensal
dos últimos 12 meses e até dez empréstimos recentes. Os itens recentes incluem dados
da obra, unidade, datas e status, mas não identificam o leitor. Filtros opcionais:
`unidade_id`, `genero_id`, `ano_inicio` e `ano_fim`; os anos se referem à publicação.
O modelo não registra data de cadastro nem reservas, portanto `reservados` é `null` e
a tendência de cadastro não é fornecida.

Campos dos objetos das listas: `acervo_por_categoria` contém `genero_id`, `categoria`,
`titulos` e `exemplares`; `acervo_por_unidade` contém `unidade_id`, `unidade`,
`titulos` e `exemplares`; `top_autores` contém `autor` e `titulos`;
`publicacoes_por_decada` contém `ano_inicio`, `ano_fim`, `faixa` e `titulos`;
`circulacao_mensal` contém `mes`, `emprestimos_iniciados` e `devolucoes`;
`emprestimos_recentes` contém `id`, `titulo`, `autor`, `unidade`, `data_emprestimo`,
`data_prevista_devolucao`, `data_devolucao` e `status`.

### `GET /gestor/analytics/gestao-livros/filtros/`

```json
{
	"unidades": [{"id": 1, "nome": "Biblioteca Central"}],
	"categorias": [{"id": 1, "nome": "Ficção"}],
	"anos_publicacao": {"inicio": 1899, "fim": 2025}
}
```

`unidades` e `categorias` fornecem ID e nome para preencher os seletores. `inicio` e
`fim` são o menor e o maior ano de publicação cadastrados; ambos podem ser `null` se
nenhum livro tiver data de publicação.

## Viabilidade da dashboard

A tabela compara os componentes do mockup da dashboard com os dados oferecidos pelas
rotas analíticas. “Parcial” indica que é necessário adaptar o componente ou combinar
os dados com outra fonte.

| Componente da dashboard | Rota/dados disponíveis | Viabilidade e limitações |
| --- | --- | --- |
| Totais de livros, autores, categorias e exemplares | `gestao-livros`: `indicadores` | Sim. `unidades_com_acervo` conta apenas unidades com acervo. |
| Acervo por categoria e por biblioteca | `gestao-livros`: `acervo_por_categoria`, `acervo_por_unidade` | Sim. |
| Principais autores | `gestao-livros`: `top_autores` | Sim. Retorna até dez autores e suas quantidades de títulos. |
| Distribuição por ano de publicação | `gestao-livros`: `publicacoes_por_decada` | Parcial. Os dados são agrupados por década, não nas faixas específicas do mockup. |
| Empréstimos recentes | `gestao-livros`: `emprestimos_recentes` | Parcial. Retorna até dez empréstimos, sem identificar o leitor e sem imagem/capa do livro. |
| Situação dos exemplares | `gestao-livros`: `situacao_exemplares` | Parcial. Informa total, emprestados e disponíveis; reservas não são suportadas e `reservados` é `null`. |
| Evolução do acervo e crescimento percentual | `gestao-livros`: `circulacao_mensal` | Parcial. Há empréstimos e devoluções nos últimos 12 meses, mas não novos títulos cadastrados nem comparação de crescimento entre períodos. |
| Insights: categoria mais representada | `gestao-livros`: `acervo_por_categoria` | Sim, pode ser derivada da distribuição do acervo. |
| Insights: cobertura dos registros | `territorio`: `cobertura`; `powerbi`: `qualidade_ibge` | Parcial. Mede cobertura e qualidade dos dados territoriais do IBGE, não a completude dos registros da biblioteca. |
| Insights: oportunidade/demanda por categoria | Nenhuma rota oferece demanda literária por categoria | Não diretamente. A API não tem dados para fundamentar uma recomendação de demanda. |
| Tabela de livros em destaque | `powerbi`: `fato_titulos` | Parcial. Contém títulos que aparecem em empréstimos; não é uma lista completa do acervo. Para listar todo o acervo, é preciso combinar com rotas de livros/acervo ou criar um endpoint específico. |
| Filtros de biblioteca, categoria e período | `gestao-livros/filtros/` e parâmetros de `gestao-livros` | Parcial. Biblioteca, categoria e ano de publicação são suportados. A circulação permanece fixa nos últimos 12 meses; não há filtro de período de circulação. |

Assim, as rotas atuais permitem montar boa parte da dashboard, desde que os gráficos
e indicadores sem suporte sejam adaptados. Para reproduzir integralmente o mockup,
faltam principalmente histórico de cadastro de livros, reservas, métricas de
completude do acervo e uma listagem completa de livros em destaque.

## Interpretação de erros

- `HTTP 401` ou `HTTP 403`: credenciais inválidas ou conta sem permissão para alguma rota.
- `Falha de conexão`: confirme se os containers estão ativos e se a API está acessível na URL informada.
- `HTTP 5xx`: a API respondeu, mas ocorreu um erro no servidor; confira os logs do container `api`.

O script só faz login e requisições `GET`; não cria, altera ou exclui dados.
