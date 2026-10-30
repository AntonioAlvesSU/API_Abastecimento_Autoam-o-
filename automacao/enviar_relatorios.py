
#!/usr/bin/env python3
import os
import sys
import csv
import ssl
import smtplib
import logging
from pathlib import Path
from datetime import datetime, timedelta, time
from email.message import EmailMessage
from zoneinfo import ZoneInfo

import psycopg2
from dotenv import load_dotenv

# Diretorio principal da API Mutuca
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Carregar variaveis de ambiente
load_dotenv(BASE_DIR / ".env", override=True)

from config import servidores
from consultas import consultas

PASTA_RELATORIOS = BASE_DIR / "automacao" / "relatorios"
PASTA_RELATORIOS.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger("mutuca-automacao")


def obter_consulta():
    nome = os.environ["RELATORIO_CONSULTA"]

    if nome not in consultas:
        raise ValueError(f"Consulta nao encontrada: {nome}")

    sql = consultas[nome]

    if not isinstance(sql, str):
        raise ValueError("A consulta precisa ser uma string SQL")

    return sql


def executar_consulta():
    nome_servidor = os.environ["RELATORIO_SERVIDOR"]

    if nome_servidor not in servidores:
        raise ValueError(f"Servidor nao encontrado: {nome_servidor}")

    config = servidores[nome_servidor].copy()

    # Evita enviar propriedades especificas da interface ao psycopg2
    config = {
        chave: config[chave]
        for chave in ("host", "port", "database", "user", "password")
        if chave in config
    }

    sql = obter_consulta()

     # Datas no fuso horario de Sao Paulo
    hoje = datetime.now(ZoneInfo("America/Sao_Paulo")).date()

    dias = int(os.getenv("DIAS_RELATORIO", "1"))

    if dias < 1:
        raise ValueError("DIAS_RELATORIO deve ser maior que zero")

    data_inicial = datetime.combine(
        hoje - timedelta(days=dias),
        time.min
    )

    # Limite exclusivo: inicio do dia atual
    data_final = datetime.combine(hoje, time.min)

    codigo_posto = os.getenv("CODIGO_POSTO", "").strip()
    cpf_cliente = os.getenv("CPF_CLIENTE", "").strip()

    if not codigo_posto:
        raise ValueError("CODIGO_POSTO nao configurado no .env")

    parametros = {
        "codigo_posto": codigo_posto,
        "data_inicial": data_inicial,
        "data_final": data_final,
        "cpf_cliente": cpf_cliente or None
    }

    logger.info("Executando consulta no servidor %s", nome_servidor)
    logger.info("Periodo inicial: %s", data_inicial)
    logger.info("Periodo final (exclusivo): %s", data_final)

    with psycopg2.connect(**config) as conexao:
        conexao.set_session(readonly=True, autocommit=False)

        with conexao.cursor() as cursor:
            cursor.execute("SET LOCAL statement_timeout = '120s'")
            cursor.execute(sql, parametros)

            if cursor.description is None:
                raise ValueError("Consulta nao retornou colunas")

            colunas = [coluna[0] for coluna in cursor.description]
            registros = cursor.fetchall()

    logger.info("Consulta finalizada: %s registros", len(registros))

    return colunas, registros


def gerar_csv(colunas, registros):
    agora = datetime.now(ZoneInfo("America/Sao_Paulo"))
    nome = f"relatorio_mutuca_{agora:%Y%m%d_%H%M%S}.csv"
    arquivo = PASTA_RELATORIOS / nome

    with arquivo.open("w", newline="", encoding="utf-8-sig") as f:
        escritor = csv.writer(f, delimiter=";")
        escritor.writerow(colunas)
        escritor.writerows(registros)

    logger.info("CSV gerado: %s", arquivo.name)
    return arquivo


def enviar_email(arquivo, quantidade):
    agora = datetime.now(ZoneInfo("America/Sao_Paulo"))

    smtp_host = os.environ["SMTP_HOST"]
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.environ["SMTP_USER"]
    smtp_password = os.environ["SMTP_PASSWORD"]
    remetente = os.getenv("SMTP_FROM", smtp_user)

    destinatarios = [
        email.strip()
        for email in os.environ["EMAIL_DESTINATARIOS"].split(",")
        if email.strip()
    ]

    if not destinatarios:
        raise ValueError("Nenhum destinatario configurado")

    url = os.getenv(
        "API_MUTUCA_URL",
        "http://mutuca.ddns.net:5020/login"
    )

    mensagem = EmailMessage()
    mensagem["From"] = remetente
    mensagem["To"] = ", ".join(destinatarios)
    mensagem["Subject"] = (
        f"API Mutuca - Relatorio Automatico - {agora:%d/%m/%Y}"
    )

    corpo = f"""Prezados,

Segue em anexo o relatorio gerado automaticamente pela API Mutuca.

INFORMACOES DA EXECUCAO

Servidor: {os.environ["RELATORIO_SERVIDOR"]}
Consulta: {os.environ["RELATORIO_CONSULTA"]}
Data/Hora: {agora:%d/%m/%Y %H:%M:%S}
Registros encontrados: {quantidade}
Arquivo: {arquivo.name}

ACESSO A API MUTUCA

{url}

Para acessar outras consultas, utilize suas credenciais autorizadas.

Atenciosamente,
Sistema de Consultas - API Mutuca

Mensagem enviada automaticamente.
"""

    mensagem.set_content(corpo)

    with arquivo.open("rb") as f:
        mensagem.add_attachment(
            f.read(),
            maintype="text",
            subtype="csv",
            filename=arquivo.name
        )

    contexto = ssl.create_default_context()

    with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as smtp:
        smtp.ehlo()
        smtp.starttls(context=contexto)
        smtp.ehlo()
        smtp.login(smtp_user, smtp_password)
        smtp.send_message(mensagem)

    logger.info("Relatorio enviado para %s destinatario(s)", len(destinatarios))


def main():
    try:
        logger.info("Iniciando Automacao API Mutuca")

        colunas, registros = executar_consulta()
        arquivo = gerar_csv(colunas, registros)
        enviar_email(arquivo, len(registros))

        logger.info("Automacao concluida com sucesso")

    except Exception:
        logger.exception("Falha na automacao")
        sys.exit(1)


if __name__ == "__main__":
    main()
