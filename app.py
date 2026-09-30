from flask import Flask, render_template, request, jsonify, redirect, url_for
import sqlite3
from datetime import datetime
from pathlib import Path

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "fila.db"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS atendimentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            telefone TEXT,
            prioridade TEXT NOT NULL DEFAULT 'Normal',
            status TEXT NOT NULL DEFAULT 'Aguardando',
            chegada TEXT NOT NULL,
            chamada TEXT,
            inicio_atendimento TEXT,
            conclusao TEXT,
            cancelamento TEXT,
            observacao TEXT
        )
    """)

    conn.commit()
    conn.close()


def agora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def formatar_data(data):
    if not data:
        return ""

    try:
        return datetime.strptime(
            data, "%Y-%m-%d %H:%M:%S"
        ).strftime("%d/%m/%Y %H:%M:%S")
    except ValueError:
        return data


def cliente_para_dict(cliente):
    item = dict(cliente)

    for campo in [
        "chegada",
        "chamada",
        "inicio_atendimento",
        "conclusao",
        "cancelamento"
    ]:
        if item.get(campo):
            item[f"{campo}_formatado"] = formatar_data(item[campo])

    return item


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/historico")
def historico():
    conn = get_db()

    atendimentos = conn.execute("""
        SELECT *
        FROM atendimentos
        WHERE status IN ('Concluído', 'Cancelado')
        ORDER BY
            COALESCE(conclusao, cancelamento, chegada) DESC
    """).fetchall()

    conn.close()

    return render_template(
        "historico.html",
        atendimentos=atendimentos
    )


@app.route("/api/fila")
def api_fila():
    conn = get_db()

    fila = conn.execute("""
        SELECT *
        FROM atendimentos
        WHERE status IN ('Aguardando', 'Em atendimento')
        ORDER BY
            CASE
                WHEN prioridade = 'Preferencial' THEN 0
                ELSE 1
            END,
            chegada ASC,
            id ASC
    """).fetchall()

    conn.close()

    return jsonify([
        cliente_para_dict(cliente)
        for cliente in fila
    ])


@app.route("/api/dashboard")
def api_dashboard():
    conn = get_db()

    dados = conn.execute("""
        SELECT
            SUM(CASE WHEN status = 'Aguardando' THEN 1 ELSE 0 END) AS aguardando,
            SUM(CASE WHEN status = 'Em atendimento' THEN 1 ELSE 0 END) AS atendimento,
            SUM(CASE WHEN status = 'Concluído' THEN 1 ELSE 0 END) AS concluidos,
            SUM(CASE WHEN status = 'Cancelado' THEN 1 ELSE 0 END) AS cancelados
        FROM atendimentos
    """).fetchone()

    conn.close()

    return jsonify({
        "aguardando": dados["aguardando"] or 0,
        "atendimento": dados["atendimento"] or 0,
        "concluidos": dados["concluidos"] or 0,
        "cancelados": dados["cancelados"] or 0
    })


@app.route("/api/cadastrar", methods=["POST"])
def cadastrar():
    dados = request.get_json(silent=True) or request.form

    nome = str(dados.get("nome", "")).strip()
    telefone = str(dados.get("telefone", "")).strip()
    prioridade = str(dados.get("prioridade", "Normal")).strip()

    if not nome:
        return jsonify({
            "sucesso": False,
            "mensagem": "Informe o nome do cliente."
        }), 400

    if prioridade not in ("Normal", "Preferencial"):
        prioridade = "Normal"

    conn = get_db()

    cursor = conn.execute("""
        INSERT INTO atendimentos
        (nome, telefone, prioridade, status, chegada)
        VALUES (?, ?, ?, 'Aguardando', ?)
    """, (
        nome,
        telefone,
        prioridade,
        agora()
    ))

    conn.commit()

    cliente_id = cursor.lastrowid

    conn.close()

    return jsonify({
        "sucesso": True,
        "id": cliente_id,
        "mensagem": "Cliente cadastrado na fila."
    })


@app.route("/api/chamar-proximo", methods=["POST"])
def chamar_proximo():
    conn = get_db()

    cliente = conn.execute("""
        SELECT *
        FROM atendimentos
        WHERE status = 'Aguardando'
        ORDER BY
            CASE
                WHEN prioridade = 'Preferencial' THEN 0
                ELSE 1
            END,
            chegada ASC,
            id ASC
        LIMIT 1
    """).fetchone()

    if not cliente:
        conn.close()

        return jsonify({
            "sucesso": False,
            "mensagem": "Não existem clientes aguardando."
        }), 404

    data = agora()

    conn.execute("""
        UPDATE atendimentos
        SET
            status = 'Em atendimento',
            chamada = ?,
            inicio_atendimento = ?
        WHERE id = ?
    """, (
        data,
        data,
        cliente["id"]
    ))

    conn.commit()

    atualizado = conn.execute("""
        SELECT *
        FROM atendimentos
        WHERE id = ?
    """, (cliente["id"],)).fetchone()

    conn.close()

    return jsonify({
        "sucesso": True,
        "mensagem": f"Cliente {cliente['nome']} chamado.",
        "cliente": cliente_para_dict(atualizado)
    })


@app.route("/api/status/<int:cliente_id>", methods=["PUT", "POST"])
def alterar_status(cliente_id):
    dados = request.get_json(silent=True) or request.form

    novo_status = str(dados.get("status", "")).strip()

    status_validos = [
        "Aguardando",
        "Em atendimento",
        "Concluído",
        "Cancelado"
    ]

    if novo_status not in status_validos:
        return jsonify({
            "sucesso": False,
            "mensagem": "Status inválido."
        }), 400

    conn = get_db()

    cliente = conn.execute("""
        SELECT *
        FROM atendimentos
        WHERE id = ?
    """, (cliente_id,)).fetchone()

    if not cliente:
        conn.close()

        return jsonify({
            "sucesso": False,
            "mensagem": "Cliente não encontrado."
        }), 404

    data = agora()

    if novo_status == "Aguardando":
        conn.execute("""
            UPDATE atendimentos
            SET
                status = ?,
                chamada = NULL,
                inicio_atendimento = NULL
            WHERE id = ?
        """, (
            novo_status,
            cliente_id
        ))

    elif novo_status == "Em atendimento":
        conn.execute("""
            UPDATE atendimentos
            SET
                status = ?,
                chamada = COALESCE(chamada, ?),
                inicio_atendimento = COALESCE(inicio_atendimento, ?)
            WHERE id = ?
        """, (
            novo_status,
            data,
            data,
            cliente_id
        ))

    elif novo_status == "Concluído":
        conn.execute("""
            UPDATE atendimentos
            SET
                status = ?,
                conclusao = ?
            WHERE id = ?
        """, (
            novo_status,
            data,
            cliente_id
        ))

    elif novo_status == "Cancelado":
        conn.execute("""
            UPDATE atendimentos
            SET
                status = ?,
                cancelamento = ?
            WHERE id = ?
        """, (
            novo_status,
            data,
            cliente_id
        ))

    conn.commit()
    conn.close()

    return jsonify({
        "sucesso": True,
        "mensagem": f"Status alterado para {novo_status}."
    })


@app.route("/api/cancelar/<int:cliente_id>", methods=["POST"])
def cancelar(cliente_id):
    conn = get_db()

    cursor = conn.execute("""
        UPDATE atendimentos
        SET
            status = 'Cancelado',
            cancelamento = ?
        WHERE id = ?
        AND status NOT IN ('Concluído', 'Cancelado')
    """, (
        agora(),
        cliente_id
    ))

    conn.commit()

    alterado = cursor.rowcount > 0

    conn.close()

    if not alterado:
        return jsonify({
            "sucesso": False,
            "mensagem": "Atendimento não encontrado ou já finalizado."
        }), 404

    return jsonify({
        "sucesso": True,
        "mensagem": "Atendimento cancelado."
    })


@app.route("/api/limpar-historico", methods=["DELETE"])
def limpar_historico():
    conn = get_db()

    conn.execute("""
        DELETE FROM atendimentos
        WHERE status IN ('Concluído', 'Cancelado')
    """)

    conn.commit()
    conn.close()

    return jsonify({
        "sucesso": True,
        "mensagem": "Histórico removido."
    })


@app.context_processor
def utility_processor():
    return {
        "formatar_data": formatar_data
    }


if __name__ == "__main__":
    init_db()

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
