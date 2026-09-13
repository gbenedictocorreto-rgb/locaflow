"""Cálculo do score (classificação) do cliente com base no histórico financeiro."""
from flask import current_app
from db import query_all


def atualizar_atrasados(execute_fn):
    """Marca como 'atrasado' qualquer lançamento financeiro pendente cujo vencimento já passou."""
    execute_fn(
        """
        UPDATE financeiro
        SET status = 'atrasado'
        WHERE status = 'pendente' AND date(vencimento) < date('now')
        """
    )


def calcular_score_cliente(cliente_id, score_manual=None):
    """Retorna dict com classificacao (bom/regular/ruim), motivo e contadores.

    Se score_manual estiver definido (bom/regular/ruim), ele prevalece, mas os
    contadores automáticos continuam sendo calculados para referência.
    """
    linhas = query_all(
        "SELECT status, valor, vencimento, data_pagamento FROM financeiro WHERE cliente_id = ?",
        (cliente_id,),
    )

    total_lancamentos = len(linhas)
    atrasados = [l for l in linhas if l["status"] == "atrasado"]
    qtd_atrasados = len(atrasados)
    valor_em_aberto = sum(l["valor"] for l in linhas if l["status"] in ("pendente", "atrasado"))
    valor_atrasado = sum(l["valor"] for l in atrasados)

    min_regular = current_app.config["SCORE_REGULAR_MIN_ATRASOS"]
    min_ruim = current_app.config["SCORE_RUIM_MIN_ATRASOS"]

    if qtd_atrasados >= min_ruim:
        automatico = "ruim"
    elif qtd_atrasados >= min_regular:
        automatico = "regular"
    else:
        automatico = "bom"

    final = score_manual if score_manual in ("bom", "regular", "ruim") else automatico

    return {
        "classificacao": final,
        "automatico": automatico,
        "ajustado_manualmente": bool(score_manual),
        "total_lancamentos": total_lancamentos,
        "qtd_atrasados": qtd_atrasados,
        "valor_em_aberto": valor_em_aberto,
        "valor_atrasado": valor_atrasado,
    }


SCORE_LABELS = {
    "bom": {"texto": "Bom pagador", "cor": "score-bom"},
    "regular": {"texto": "Atenção", "cor": "score-regular"},
    "ruim": {"texto": "Inadimplente", "cor": "score-ruim"},
}
