from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from functools import wraps
import os
from dotenv import load_dotenv
import psycopg2
from datetime import datetime, date
from config import servidores
from consultas import consultas
import csv
from pathlib import Path
import traceback

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "troque-esta-chave-por-uma-segura")

USUARIO_CORRETO = os.getenv("USUARIO_CORRETO")
SENHA_CORRETA = os.getenv("SENHA_CORRETA")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD_CAXUXA = os.getenv("DB_PASSWORD_CAXUXA")
DB_PASSWORD = os.getenv("DB_PASSWORD")

LIMITE_VISUALIZACAO = 1000

if os.name == "nt":
    DIRETORIO_CSV = Path(__file__).resolve().parent / "CSV"
else:
    DIRETORIO_CSV = Path("/pub/publico/API/Mutuca/CSV")


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "usuario_logado" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


@app.route("/login", methods=["GET", "POST"])
def login():
    if "usuario_logado" in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        usuario = request.form.get("usuario")
        senha = request.form.get("senha")

        if usuario == USUARIO_CORRETO and senha == SENHA_CORRETA:
            session["usuario_logado"] = usuario
            return redirect(url_for("index"))

        flash("Usuário ou senha incorretos!", "erro")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("usuario_logado", None)
    session.pop("arquivo_csv", None)
    return redirect(url_for("login"))


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    resultado = []
    colunas = []
    retorno = None

    servidores_ativos = {
        nome: dados
        for nome, dados in servidores.items()
        if dados.get("ativo", True)
    }

    if request.method == "POST":
        conn = None
        cursor = None
        servidor_nome = "Não informado"
        nome_consulta = "Não informado"
        sql = ""
        parametros_sql = None

        try:
            tipo_conexao = request.form.get("tipo_conexao", "servidor")

            if tipo_conexao == "servidor":
                servidor = request.form.get("servidor")

                if not servidor:
                    raise ValueError("Selecione um servidor.")
                if servidor not in servidores_ativos:
                    raise ValueError(f"Servidor '{servidor}' não cadastrado ou inativo.")

                conexao = servidores_ativos[servidor]
                servidor_nome = servidor

            elif tipo_conexao == "manual":
                host = request.form.get("host_manual", "").strip()
                port = request.form.get("port_manual", "5432").strip()
                database = request.form.get("database_manual", "").strip()
                user = DB_USER
                password = DB_PASSWORD

                if not host:
                    raise ValueError("Informe o Host/IP.")
                if not database:
                    raise ValueError("Informe o banco de dados.")
                if not user:
                    raise ValueError("Informe o usuário.")
                if not password:
                    raise ValueError("Informe a senha do banco.")

                conexao = {
                    "host": host,
                    "port": int(port),
                    "database": database,
                    "user": user,
                    "password": password,
                }
                servidor_nome = f"MANUAL - {host}:{port}/{database}"
            else:
                raise ValueError("Tipo de conexão inválido.")

            consulta_predefinida = request.form.get("consulta_predefinida", "")
            consulta_manual = request.form.get("consulta_manual", "").strip()
            commit = request.form.get("commit")

            if consulta_manual:
                sql = consulta_manual
                nome_consulta = "MANUAL"
            else:
                if not consulta_predefinida:
                    raise ValueError("Selecione uma consulta ou digite um SQL manual.")
                if consulta_predefinida not in consultas:
                    raise ValueError(f"Consulta '{consulta_predefinida}' não cadastrada.")
                sql = consultas[consulta_predefinida]
                nome_consulta = consulta_predefinida

            if isinstance(sql, dict):
                sql = sql.get("sql", "")

            if not isinstance(sql, str) or not sql.strip():
                raise ValueError("SQL da consulta está vazio ou inválido.")

            if nome_consulta == "Abastecimentos":
                inicio = request.form.get("data_inicial", "").strip()
                fim = request.form.get("data_final", "").strip()
                cpf_cliente = request.form.get("cpf_cliente", "").strip()
                if not cpf_cliente:
                    cpf_cliente = request.form.get("codigo_cliente", "").strip()
                posto = request.form.get("codigo_posto", "").strip()

                try:
                    data_inicio = date.fromisoformat(inicio)
                    data_fim = date.fromisoformat(fim)
                except ValueError as exc:
                    raise ValueError("Informe datas inicial e final válidas.") from exc

                if data_inicio > data_fim:
                    raise ValueError("A data inicial não pode ser maior que a final.")

                cpf_cliente = "".join(c for c in cpf_cliente if c.isdigit())
                if len(cpf_cliente) not in (11, 14):
                    raise ValueError("Informe um CPF (11 dígitos) ou CNPJ (14 dígitos).")

                if not posto.isdecimal() or len(posto) > 5:
                    raise ValueError("Informe um código de posto numérico de até 5 dígitos.")

                parametros_sql = {
                    "data_inicial": data_inicio,
                    "data_final": data_fim,
                    "cpf_cliente": cpf_cliente,
                    "codigo_posto": posto,
                }

            print("SERVIDOR:", servidor_nome)
            print("CONSULTA:", nome_consulta)

            conn = psycopg2.connect(
                host=conexao["host"],
                port=conexao["port"],
                database=conexao["database"],
                user=conexao["user"],
                password=conexao["password"],
            )
            conn.set_client_encoding("LATIN1")
            cursor = conn.cursor()

            if parametros_sql is not None:
                cursor.execute(sql, parametros_sql)
            else:
                cursor.execute(sql)

            csv_gerado = False
            if cursor.description:
                colunas = [descricao[0] for descricao in cursor.description]
                resultado_completo = cursor.fetchall()
                registros = len(resultado_completo)
                resultado = resultado_completo[:LIMITE_VISUALIZACAO]
                session.pop("arquivo_csv", None)

                try:
                    DIRETORIO_CSV.mkdir(parents=True, exist_ok=True)
                    nome_arquivo = datetime.now().strftime(
                        "resultado_%Y-%m-%d_%H-%M-%S-%f.csv"
                    )
                    caminho_arquivo = DIRETORIO_CSV / nome_arquivo

                    with open(caminho_arquivo, "w", newline="", encoding="utf-8-sig") as arquivo:
                        escritor = csv.writer(
                            arquivo,
                            delimiter=";",
                            quoting=csv.QUOTE_MINIMAL,
                        )
                        escritor.writerow(colunas)
                        escritor.writerows(resultado_completo)

                    session["arquivo_csv"] = nome_arquivo
                    csv_gerado = True
                    print("Registros encontrados:", registros)
                    print("Registros exibidos:", len(resultado))
                    print("CSV:", caminho_arquivo)
                except Exception as erro_csv:
                    print("ERRO AO GERAR CSV:", erro_csv)
                    traceback.print_exc()
                    flash(f"Erro ao gerar CSV: {erro_csv}", "erro")
            else:
                registros = cursor.rowcount
                session.pop("arquivo_csv", None)

            if commit:
                conn.commit()
                mensagem = "Consulta executada e COMMIT realizado."
            else:
                conn.rollback()
                mensagem = "Consulta executada. Nenhum COMMIT foi realizado."

            if colunas and registros > LIMITE_VISUALIZACAO:
                mensagem += (
                    f" Exibindo os primeiros {LIMITE_VISUALIZACAO} de "
                    f"{registros} registros."
                )
                if csv_gerado:
                    mensagem += " O CSV contém o resultado completo."

            if colunas and not csv_gerado:
                mensagem += " O CSV não pôde ser gerado; verifique a mensagem de erro."

            retorno = {
                "status": "OK",
                "servidor": servidor_nome,
                "consulta": nome_consulta,
                "sql": cursor.mogrify(sql, parametros_sql).decode("latin1", errors="replace")
                       if parametros_sql is not None else sql,
                "registros": registros,
                "hora": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "mensagem": mensagem,
            }

        except Exception as erro:
            print("ERRO:", erro)
            traceback.print_exc()
            if conn is not None:
                try:
                    conn.rollback()
                except Exception:
                    pass

            retorno = {
                "status": "ERRO",
                "servidor": servidor_nome,
                "consulta": nome_consulta,
                "sql": sql,
                "registros": 0,
                "hora": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "mensagem": str(erro),
            }

        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()

    return render_template(
        "index.html",
        servidores=servidores_ativos,
        consultas=consultas,
        resultado=resultado,
        colunas=colunas,
        retorno=retorno,
        usuario=session.get("usuario_logado"),
    )


@app.route("/exportar_csv", methods=["POST"])
@login_required
def exportar_csv():
    nome_arquivo = session.get("arquivo_csv")

    if not nome_arquivo:
        flash("Não existe resultado para exportar.", "erro")
        return redirect(url_for("index"))

    nome_arquivo = Path(nome_arquivo).name
    caminho_arquivo = DIRETORIO_CSV / nome_arquivo

    if not caminho_arquivo.exists():
        flash("Arquivo CSV não encontrado.", "erro")
        return redirect(url_for("index"))

    try:
        return send_file(
            caminho_arquivo,
            mimetype="text/csv; charset=utf-8",
            as_attachment=True,
            download_name=nome_arquivo,
        )
    except Exception as erro:
        print("ERRO AO BAIXAR CSV:", erro)
        flash(f"Erro ao baixar CSV: {erro}", "erro")
        return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5020, debug=True)
