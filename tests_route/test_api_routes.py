#!/usr/bin/env python3
"""Smoke-test the local Bibliotecas Conectadas API routes."""

import argparse
import getpass
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


AUTHENTICATED_JSON_ROUTES = (
    "/api/schema/",
    "/gestor/",
    "/gestor/auth/me/",
    "/gestor/livros/",
    "/gestor/unidades/",
    "/gestor/livro-unidades/",
    "/gestor/usuarios/",
    "/gestor/emprestimos/",
    "/gestor/acessos/",
    "/gestor/dados-iniciais/",
    "/gestor/analytics/resumo/",
    "/gestor/analytics/territorio/",
    "/gestor/analytics/powerbi/",
    "/gestor/analytics/gestao-livros/",
    "/gestor/analytics/gestao-livros/filtros/",
)

AUTHENTICATED_HTML_ROUTES = ("/api/docs/", "/api/redoc/")
RESOURCE_ROUTES = {
    "/gestor/livros/",
    "/gestor/unidades/",
    "/gestor/livro-unidades/",
    "/gestor/usuarios/",
    "/gestor/emprestimos/",
    "/gestor/acessos/",
}


def request_response(url, *, method="GET", token=None, payload=None):
    headers = {"Accept": "application/json, text/html"}
    body = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload).encode("utf-8")
    if token:
        headers["Authorization"] = f"Token {token}"

    request = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=15) as response:
            return (
                response.status,
                response.headers.get_content_type(),
                response.read(),
            )
    except HTTPError as error:
        return error.code, error.headers.get_content_type(), error.read()
    except URLError as error:
        raise RuntimeError(f"Falha de conexão com {url}: {error.reason}") from None


def request_json(url, *, method="GET", token=None, payload=None):
    status_code, _, body = request_response(
        url,
        method=method,
        token=token,
        payload=payload,
    )
    if not 200 <= status_code < 300:
        raise RuntimeError(f"HTTP {status_code} ao chamar {method} {url}")
    try:
        return json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise RuntimeError(f"Resposta não é JSON: {method} {url}") from None


def check_status(base_url, path, *, expected_status, token=None, content_type=None):
    status_code, response_type, _ = request_response(
        f"{base_url}{path}",
        token=token,
    )
    if status_code != expected_status:
        raise RuntimeError(
            f"HTTP {status_code} ao chamar GET {path}; esperado {expected_status}"
        )
    if content_type and not response_type.startswith(content_type):
        raise RuntimeError(
            f"Content-Type inesperado ao chamar GET {path}: {response_type}"
        )
    return status_code


def check_validation_error(
    base_url,
    path,
    *,
    token,
    method="GET",
    payload=None,
    expected_status=400,
):
    status_code, _, body = request_response(
        f"{base_url}{path}",
        method=method,
        token=token,
        payload=payload,
    )
    if status_code != expected_status:
        raise RuntimeError(
            f"HTTP {status_code} ao validar {method} {path}; "
            f"esperado {expected_status}"
        )
    try:
        response_data = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise RuntimeError(f"Resposta de validação não é JSON: {method} {path}") from None
    if not isinstance(response_data, dict):
        raise RuntimeError(f"Resposta de validação inesperada: {method} {path}")


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

    if path == "/gestor/analytics/gestao-livros/":
        indicators = data.get("indicadores")
        if not isinstance(indicators, dict):
            raise RuntimeError("Dashboard sem objeto válido 'indicadores'.")
        return f"{indicators.get('titulos', 0)} títulos"

    if path == "/gestor/analytics/gestao-livros/filtros/":
        units = data.get("unidades")
        categories = data.get("categorias")
        if not isinstance(units, list) or not isinstance(categories, list):
            raise RuntimeError("Filtros da dashboard sem listas válidas.")
        return f"{len(units)} unidades, {len(categories)} categorias"

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

    try:
        request_json(f"{base_url}/")
        print("GET / ... OK (JSON válido)")

        check_status(base_url, "/healthz", expected_status=204)
        print("GET /healthz ... OK (HTTP 204)")

        check_status(
            base_url,
            "/admin/",
            expected_status=200,
            content_type="text/html",
        )
        print("GET /admin/ ... OK (HTML)")

        username = input("Usuário da API: ").strip()
        password = getpass.getpass("Senha da API: ")
        login = request_json(
            f"{base_url}/gestor/auth/login/",
            method="POST",
            payload={"username": username, "password": password},
        )
        token = login.get("token")
        if not token:
            raise RuntimeError("Login não retornou um token de autenticação.")
        print("POST /gestor/auth/login/ ... OK")

        is_admin = login.get("user", {}).get("role") == "admin"
        for path in AUTHENTICATED_JSON_ROUTES:
            if path == "/gestor/acessos/" and not is_admin:
                print(f"GET {path} ... IGNORADO (requer administrador)")
                continue
            data = request_json(f"{base_url}{path}", token=token)
            details = response_count(path, data)
            print(f"GET {path} ... OK ({details})")

            if path in RESOURCE_ROUTES and isinstance(data, list) and data:
                identifier = data[0].get("id")
                if identifier is not None:
                    detail_path = f"{path}{identifier}/"
                    detail_data = request_json(
                        f"{base_url}{detail_path}",
                        token=token,
                    )
                    response_count(detail_path, detail_data)
                    print(f"GET {detail_path} ... OK (JSON válido)")

        for path in AUTHENTICATED_HTML_ROUTES:
            check_status(
                base_url,
                path,
                expected_status=200,
                token=token,
                content_type="text/html",
            )
            print(f"GET {path} ... OK (HTML)")

        check_validation_error(
            base_url,
            "/gestor/livros/isbn-lookup/?isbn=1234567890123",
            token=token,
        )
        print(
            "GET /gestor/livros/isbn-lookup/?isbn=1234567890123 ... OK (HTTP 400)"
        )

        check_validation_error(
            base_url,
            "/gestor/auth/change-password/",
            method="POST",
            token=token,
            payload={},
        )
        print("POST /gestor/auth/change-password/ (payload inválido) ... OK (HTTP 400)")

        status_code, _, _ = request_response(
            f"{base_url}/gestor/auth/logout/",
            method="POST",
            token=token,
        )
        if status_code != 204:
            raise RuntimeError(
                f"HTTP {status_code} ao chamar POST /gestor/auth/logout/; "
                "esperado 204"
            )
        print("POST /gestor/auth/logout/ ... OK (HTTP 204)")
    except (RuntimeError, KeyError) as error:
        print(f"ERRO: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())