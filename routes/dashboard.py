from datetime import date, timedelta
from flask import Blueprint, render_template
from db import query_all, query_one, execute
from services.utils import login_required
from services.score import atualizar_atrasados

bp = Blueprint("dashboard", __name__)


@bp.route("/")
@login_required
def index():
    atualizar_atrasados(execute)
    execute(
        """UPDATE locacoes SET status = 'atrasada'
           WHERE status = 'ativa' AND data_fim_prevista IS NOT NULL
           AND date(data_fim_prevista) < date('now')"""
    )

    veiculos_status = {
        r["status"]: r["qtd"]
        for r in query_all("SELECT status, COUNT(*) as qtd FROM veiculos GROUP BY status")
    }
    total_veiculos = sum(veiculos_status.values())

    locacoes_status = {
        r["status"]: r["qtd"]
        for r in query_all("SELECT status, COUNT(*) as qtd FROM locacoes GROUP BY status")
    }

    financeiro_resumo = query_one(
        """SELECT
             SUM(CASE WHEN status='pendente' THEN valor ELSE 0 END) as a_receber,
             SUM(CASE WHEN status='atrasado' THEN valor ELSE 0 END) as atrasado,
             SUM(CASE WHEN status='pago' AND strftime('%Y-%m', data_pagamento) = strftime('%Y-%m','now') THEN valor ELSE 0 END) as recebido_mes
           FROM financeiro"""
    )

    clientes_inadimplentes = query_all(
        """SELECT c.id, c.nome, COUNT(*) as qtd_atrasados, SUM(f.valor) as valor_atrasado
           FROM financeiro f JOIN clientes c ON c.id = f.cliente_id
           WHERE f.status = 'atrasado' GROUP BY c.id ORDER BY valor_atrasado DESC LIMIT 8"""
    )

    proximas_locacoes_vencendo = query_all(
        """SELECT l.id, l.data_fim_prevista, c.nome as cliente_nome, v.placa
           FROM locacoes l JOIN clientes c ON c.id = l.cliente_id JOIN veiculos v ON v.id = l.veiculo_id
           WHERE l.status = 'ativa' AND l.data_fim_prevista IS NOT NULL
           AND date(l.data_fim_prevista) BETWEEN date('now') AND date('now', '+3 days')
           ORDER BY l.data_fim_prevista"""
    )

    limite_vistoria = (date.today() - timedelta(days=7)).isoformat()
    veiculos_sem_vistoria_recente = query_all(
        """SELECT v.id, v.placa, v.marca, v.modelo,
                  (SELECT MAX(data) FROM vistorias WHERE veiculo_id = v.id) as ultima_vistoria
           FROM veiculos v WHERE v.status = 'alugado'
           AND (
             (SELECT MAX(data) FROM vistorias WHERE veiculo_id = v.id) IS NULL
             OR (SELECT MAX(data) FROM vistorias WHERE veiculo_id = v.id) < ?
           )""",
        (limite_vistoria,),
    )

    ultimas_locacoes = query_all(
        """SELECT l.*, c.nome as cliente_nome, v.placa FROM locacoes l
           JOIN clientes c ON c.id = l.cliente_id JOIN veiculos v ON v.id = l.veiculo_id
           ORDER BY l.criado_em DESC LIMIT 6"""
    )

    return render_template(
        "dashboard.html",
        veiculos_status=veiculos_status,
        total_veiculos=total_veiculos,
        locacoes_status=locacoes_status,
        financeiro_resumo=financeiro_resumo,
        clientes_inadimplentes=clientes_inadimplentes,
        proximas_locacoes_vencendo=proximas_locacoes_vencendo,
        veiculos_sem_vistoria_recente=veiculos_sem_vistoria_recente,
        ultimas_locacoes=ultimas_locacoes,
    )
