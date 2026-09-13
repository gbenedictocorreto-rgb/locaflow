"""Geração automática do contrato de locação de veículo em PDF (reportlab).

O texto do contrato pode ser personalizado por empresa através da tela de
Configurações (tabela `configuracoes`): logo, dados da empresa, cláusulas e
rodapé. Isso é o que permite vender o sistema para diferentes locadoras sem
precisar alterar código -- cada instalação define o contrato do seu jeito.
"""
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

CLAUSULAS_PADRAO = [
    "Utilizar o veículo com zelo, exclusivamente para fins lícitos, respeitando a legislação de trânsito vigente.",
    "Responsabilizar-se por todas as multas de trânsito, infrações e pedágios gerados durante o período de locação.",
    "Comunicar imediatamente ao LOCADOR em caso de acidente, furto, roubo ou avaria do veículo.",
    "Não sublocar, ceder ou emprestar o veículo a terceiros sem autorização expressa e por escrito do LOCADOR.",
    "Devolver o veículo na data prevista, no mesmo estado de conservação em que foi recebido, salvo desgaste natural de uso.",
    "Permitir e colaborar com as vistorias periódicas do veículo realizadas pelo LOCADOR.",
    "Manter o veículo em local seguro e arcar com o abastecimento de combustível durante o período de uso.",
]

RODAPE_PADRAO = (
    "Documento gerado automaticamente pelo sistema de controle de locação. "
    "Revise as cláusulas com um profissional jurídico antes do uso definitivo."
)


def _fmt_moeda(v):
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "R$ 0,00"


def _fmt_data(v):
    if not v:
        return "-"
    try:
        return datetime.strptime(v[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return v


def _get(config, chave, default=""):
    """Lê uma chave de config (sqlite3.Row ou dict) com fallback seguro."""
    if config is None:
        return default
    try:
        valor = config[chave]
    except (KeyError, IndexError, TypeError):
        return default
    return valor if valor not in (None, "") else default


def gerar_contrato_pdf(destino_path, locacao, cliente, veiculo, proprietario=None, config=None, logo_abs_path=None):
    """Gera um PDF de contrato de locação preenchido com os dados fornecidos.

    locacao, cliente, veiculo, proprietario, config: dict-like (sqlite3.Row ou dict).
    logo_abs_path: caminho absoluto no disco para a logo da empresa (opcional).
    """
    os.makedirs(os.path.dirname(destino_path), exist_ok=True)

    doc = SimpleDocTemplate(
        destino_path, pagesize=A4,
        topMargin=2 * cm, bottomMargin=2 * cm,
        leftMargin=2 * cm, rightMargin=2 * cm,
        title="Contrato de Locação de Veículo",
    )

    styles = getSampleStyleSheet()
    titulo = ParagraphStyle("titulo", parent=styles["Heading1"], alignment=TA_CENTER, fontSize=15)
    subtitulo = ParagraphStyle("subtitulo", parent=styles["Heading2"], fontSize=11, spaceBefore=10, spaceAfter=4)
    corpo = ParagraphStyle("corpo", parent=styles["Normal"], fontSize=10, alignment=TA_JUSTIFY, leading=14)
    pequeno = ParagraphStyle("pequeno", parent=styles["Normal"], fontSize=9, textColor=colors.grey)
    empresa_estilo = ParagraphStyle("empresa", parent=styles["Normal"], fontSize=9, alignment=TA_CENTER, textColor=colors.HexColor("#374151"))

    nome_empresa = _get(config, "nome_empresa")
    cnpj_empresa = _get(config, "cnpj")
    endereco_empresa = _get(config, "endereco")
    telefone_empresa = _get(config, "telefone")
    email_empresa = _get(config, "email")

    story = []

    # Cabeçalho / timbre da empresa (se configurado)
    if logo_abs_path and os.path.exists(logo_abs_path):
        try:
            img = Image(logo_abs_path, width=3.5 * cm, height=3.5 * cm, kind="proportional")
            img.hAlign = "CENTER"
            story.append(img)
            story.append(Spacer(1, 6))
        except Exception:
            pass  # se a imagem não puder ser lida, segue sem logo

    story.append(Paragraph("CONTRATO DE LOCAÇÃO DE VEÍCULO", titulo))

    if nome_empresa:
        linha_empresa = f"<b>{nome_empresa}</b>"
        detalhes = " · ".join(filter(None, [
            f"CNPJ {cnpj_empresa}" if cnpj_empresa else "",
            endereco_empresa,
            f"Tel: {telefone_empresa}" if telefone_empresa else "",
            email_empresa,
        ]))
        story.append(Paragraph(linha_empresa, empresa_estilo))
        if detalhes:
            story.append(Paragraph(detalhes, empresa_estilo))

    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#2563eb"), thickness=1.2))
    story.append(Spacer(1, 12))

    story.append(Paragraph("1. PARTES CONTRATANTES", subtitulo))
    locador_nome = (proprietario["nome"] if proprietario and proprietario["nome"] else (nome_empresa or "Administradora do veículo"))
    story.append(Paragraph(
        f"<b>LOCADOR(A):</b> {locador_nome}, doravante denominado(a) LOCADOR.", corpo))
    story.append(Paragraph(
        f"<b>LOCATÁRIO(A):</b> {cliente['nome']}, portador(a) do CPF nº {cliente['cpf'] or '-'} "
        f"e RG nº {cliente['rg'] or '-'}, telefone {cliente['telefone'] or '-'}, "
        f"residente em {cliente['endereco'] or '-'}, doravante denominado(a) LOCATÁRIO.", corpo))

    story.append(Paragraph("2. OBJETO DO CONTRATO", subtitulo))
    story.append(Paragraph(
        "O presente contrato tem como objeto a locação do veículo abaixo descrito, "
        "que o LOCATÁRIO declara receber em perfeitas condições de uso e conservação:", corpo))
    story.append(Spacer(1, 6))

    dados_veiculo = [
        ["Marca / Modelo", f"{veiculo['marca'] or '-'} {veiculo['modelo'] or ''}".strip()],
        ["Placa", veiculo["placa"] or "-"],
        ["Renavam", veiculo["renavam"] or "-"],
        ["Chassi", veiculo["chassi"] or "-"],
        ["Cor", veiculo["cor"] or "-"],
        ["Ano", f"{veiculo['ano_fabricacao'] or '-'}/{veiculo['ano_modelo'] or '-'}"],
        ["KM na entrega", str(locacao["km_inicial"]) if locacao["km_inicial"] is not None else "-"],
    ]
    t = Table(dados_veiculo, colWidths=[5 * cm, 10.5 * cm])
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eff6ff")),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t)

    story.append(Paragraph("3. PRAZO E VALORES", subtitulo))
    story.append(Paragraph(
        f"A locação terá início em <b>{_fmt_data(locacao['data_inicio'])}</b> com previsão de "
        f"término em <b>{_fmt_data(locacao['data_fim_prevista'])}</b>, podendo ser prorrogada "
        f"mediante acordo entre as partes.", corpo))
    story.append(Paragraph(
        f"O valor da diária é de <b>{_fmt_moeda(locacao['valor_diaria'])}</b>, totalizando "
        f"estimativamente <b>{_fmt_moeda(locacao['valor_total_previsto'])}</b> para o período "
        f"contratado, a serem pagos conforme combinado entre as partes.", corpo))
    if locacao["caucao_valor"] and float(locacao["caucao_valor"]) > 0:
        story.append(Paragraph(
            f"Fica estabelecido o valor de caução (depósito de segurança) de "
            f"<b>{_fmt_moeda(locacao['caucao_valor'])}</b>, a ser devolvido ao LOCATÁRIO ao final "
            f"do contrato, descontadas eventuais multas, danos ou pendências financeiras.", corpo))

    story.append(Paragraph("4. OBRIGAÇÕES DO LOCATÁRIO", subtitulo))
    texto_clausulas = _get(config, "contrato_clausulas")
    if texto_clausulas:
        clausulas = [linha.strip() for linha in texto_clausulas.splitlines() if linha.strip()]
    else:
        clausulas = CLAUSULAS_PADRAO
    for c in clausulas:
        story.append(Paragraph(f"• {c}", corpo))

    story.append(Paragraph("5. SEGURO E ASSISTÊNCIA", subtitulo))
    seguradora = veiculo["seguradora_nome"] or "não informada"
    telefone_24h = veiculo["seguradora_telefone_24h"] or "não informado"
    story.append(Paragraph(
        f"O veículo está segurado pela seguradora <b>{seguradora}</b>. Em caso de necessidade de "
        f"acionamento de assistência 24h (reboque, pane, acidente), o LOCATÁRIO deverá entrar em "
        f"contato com o telefone <b>{telefone_24h}</b> e comunicar imediatamente o LOCADOR.", corpo))

    story.append(Paragraph("6. RESCISÃO E DISPOSIÇÕES GERAIS", subtitulo))
    story.append(Paragraph(
        "O presente contrato poderá ser rescindido a qualquer momento por acordo entre as partes, "
        "ou unilateralmente em caso de descumprimento de qualquer cláusula aqui prevista, "
        "especialmente inadimplência, uso indevido do veículo ou prática de infrações. "
        "As partes elegem o foro da comarca do LOCADOR para dirimir eventuais dúvidas oriundas "
        "deste contrato.", corpo))

    texto_extra = _get(config, "contrato_texto_extra")
    if texto_extra:
        story.append(Paragraph("7. CONDIÇÕES ESPECÍFICAS", subtitulo))
        for paragrafo in texto_extra.splitlines():
            if paragrafo.strip():
                story.append(Paragraph(paragrafo.strip(), corpo))

    story.append(Spacer(1, 30))
    story.append(Paragraph(f"Local e data: __________________________, {_fmt_data(datetime.now().strftime('%Y-%m-%d'))}", corpo))
    story.append(Spacer(1, 30))

    assinaturas = [
        ["_________________________________", "_________________________________"],
        [f"LOCADOR: {locador_nome}", f"LOCATÁRIO: {cliente['nome']}"],
    ]
    ta = Table(assinaturas, colWidths=[7.75 * cm, 7.75 * cm])
    ta.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("TOPPADDING", (0, 1), (-1, 1), 4),
    ]))
    story.append(ta)

    story.append(Spacer(1, 20))
    story.append(Paragraph(_get(config, "contrato_rodape", RODAPE_PADRAO), pequeno))

    doc.build(story)
    return destino_path
