#!/usr/bin/env python3
"""Smoke-test the local Bibliotecas Conectadas API routes."""

import argparse
import getpass
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROUTES = (
    "/gestor/livros/",
    "/gestor/unidades/",
    "/gestor/livro-unidades/",
    "/gestor/usuarios/",
    "/gestor/emprestimos/",
    "/gestor/dados-iniciais/",
    "/gestor/analytics/resumo/",
    "/gestor/analytics/territorio/",
    "/gestor/analytics/powerbi/",
)


def request_json(url, *, method="GET", token=None, payload=None):
    headers = {"Accept": "application/json"}
    body = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload).encode("utf-8")
    if token:
        headers["Authorization"] = f"Token {token}"

    request = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=15) as response:
            return json.load(response)
    except HTTPError as error:
        raise RuntimeError(f"HTTP {error.code} ao chamar {method} {url}") from None
    except URLError as error:
        raise RuntimeError(f"Falha de conexão com {url}: {error.reason}") from None
    except json.JSONDecodeError:
        raise RuntimeError(f"Resposta não é JSON: {method} {url}") from None


def response_count(path, data):
    if path == "/gestor/analytics/territorio/":
        neighborhoods = data.get("bairros")
        if not isinstance(neighborhoods, list):
            raise RuntimeError("Resposta territorial não contém a lista 'bairros'.")
        return f"{len(neighborhoods)} bairros"

    if path == "/gestor/analytics/powerbi/":
        tables = (
            "dim_bairro",
            "dim_unidade",
            "fato_acervo",
            "fato_circulacao_mensal",
            "fato_devolucoes_mensal",
            "fato_titulos",
        )
        counts = {}
        for table in tables:
            rows = data.get(table)
            if not isinstance(rows, list):
                raise RuntimeError(f"Dataset Power BI sem lista válida '{table}'.")
            counts[table] = len(rows)
        return f"tabelas {counts}"

    if isinstance(data, list):
        return f"{len(data)} registros"

    if not isinstance(data, dict):
        raise RuntimeError(f"Formato inesperado na resposta de {path}.")
    return "JSON válido"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="URL base da API (padrão: http://localhost:8000).",
    )
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    username = input("Usuário da API: ").strip()
    password = getpass.getpass("Senha da API: ")

    try:
        login = request_json(
            f"{base_url}/gestor/auth/login/",
            method="POST",
            payload={"username": username, "password": password},
        )
        token = login.get("token")
        if not token:
            raise RuntimeError("Login não retornou um token de autenticação.")
        print("POST /gestor/auth/login/ ... OK")

        for path in ROUTES:
            data = request_json(f"{base_url}{path}", token=token)
            details = response_count(path, data)
            print(f"GET {path} ... OK ({details})")
    except (RuntimeError, KeyError) as error:
        print(f"ERRO: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())