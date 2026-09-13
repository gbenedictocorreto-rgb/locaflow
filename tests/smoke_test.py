"""Teste rápido de fumaça (smoke test) usando o test_client do Flask,
percorrendo o fluxo principal do sistema. Não faz parte da aplicação entregue
ao usuário -- é apenas para verificação nesta sessão."""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app

app = create_app()
app.testing = True
client = app.test_client()

with app.app_context():
    from werkzeug.security import generate_password_hash
    from db import query_one, execute
    if not query_one("SELECT id FROM usuarios WHERE email = ?", ("admin@teste.com",)):
        execute(
            "INSERT INTO usuarios (nome, email, senha_hash, papel) VALUES (?,?,?,?)",
            ("Admin Teste", "admin@teste.com", generate_password_hash("senha123"), "admin"),
        )


def check(nome, resp, esperado=200):
    status = resp.status_code
    ok = status == esperado
    print(f"{'OK ' if ok else 'FALHOU'} [{status}] {nome}")
    if not ok:
        print(resp.data[:2000].decode(errors="replace"))
        sys.exit(1)
    return resp


# 1. Login
check("GET /login", client.get("/login"))
check("POST /login", client.post("/login", data={"email": "admin@teste.com", "senha": "senha123"}, follow_redirects=False), 302)

# 2. Dashboard
check("GET / (dashboard)", client.get("/"))

# 3. Proprietário
check("POST proprietario novo", client.post("/proprietarios/novo", data={
    "nome": "Carlos Proprietário", "documento": "111.111.111-11", "telefone": "11999990000",
    "email": "carlos@example.com", "chave_pix": "carlos@example.com", "percentual_repasse": "70",
    "observacoes": "teste",
}, follow_redirects=False), 302)
check("GET proprietarios listar", client.get("/proprietarios/"))

# 4. Veículo
resp = check("POST veiculo novo", client.post("/veiculos/novo", data={
    "placa": "ABC1D23", "renavam": "12345678901", "chassi": "9BWZZZ377VT004251",
    "marca": "Fiat", "modelo": "Argo", "ano_fabricacao": "2022", "ano_modelo": "2023",
    "cor": "Branco", "km_atual": "15000", "valor_diaria_padrao": "120.00",
    "proprietario_id": "1", "rastreador_link": "https://rastreador.example.com/abc1d23",
    "rastreador_login": "user/pass", "seguradora_nome": "Porto Seguro",
    "seguradora_apolice": "PS-9999", "seguradora_telefone_24h": "0800 727 2794",
    "status": "disponivel", "observacoes": "teste",
}, follow_redirects=False), 302)
check("GET veiculos listar", client.get("/veiculos/"))
check("GET veiculo detalhe", client.get("/veiculos/1"))

# 5. Cliente
check("POST cliente novo", client.post("/clientes/novo", data={
    "nome": "João da Silva", "cpf": "123.456.789-00", "rg": "1234567", "cnh": "987654321",
    "cnh_validade": "2028-01-01", "telefone": "11988887777", "email": "joao@example.com",
    "endereco": "Rua Exemplo, 123", "antecedentes_verificado": "on",
    "antecedentes_data": "2026-09-01", "antecedentes_link": "https://www.gov.br/pt-br",
    "antecedentes_observacao": "nada consta", "score_manual": "", "observacoes": "cliente teste",
}, follow_redirects=False), 302)
check("GET clientes listar", client.get("/clientes/"))
check("GET cliente detalhe", client.get("/clientes/1"))

# 6. Locação
resp = check("POST locacao nova", client.post("/locacoes/nova", data={
    "cliente_id": "1", "veiculo_id": "1", "data_inicio": "2026-09-10",
    "data_fim_prevista": "2026-09-20", "km_inicial": "15000", "valor_diaria": "120.00",
    "caucao_valor": "500.00", "observacoes": "locacao teste",
}, follow_redirects=False), 302)
check("GET locacao detalhe", client.get("/locacoes/1"))
check("GET veiculo agora alugado", client.get("/veiculos/1"))

# 6b. Configurações da empresa (personalização do contrato)
check("GET configuracoes", client.get("/configuracoes/"))
check("POST configuracoes salvar", client.post("/configuracoes/", data={
    "nome_empresa": "Locadora Exemplo LTDA", "cnpj": "12.345.678/0001-90",
    "endereco": "Av. Teste, 1000 - Centro", "telefone": "(11) 4000-0000",
    "email": "contato@locadoraexemplo.com",
    "contrato_clausulas": "Cláusula personalizada de teste sobre limite de KM diário.\nCláusula personalizada sobre taxa de limpeza.",
    "contrato_texto_extra": "Condição extra de teste.",
    "contrato_rodape": "Rodapé personalizado de teste.",
}, follow_redirects=False), 302)

# 6c. Upload de logo (garante que a geração de PDF com imagem não quebra)
_logo_bytes = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
    b"\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x03\x01\x01\x00\x18\xdd\x8d\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)
check("POST configuracoes com logo", client.post("/configuracoes/", data={
    "nome_empresa": "Locadora Exemplo LTDA", "cnpj": "12.345.678/0001-90",
    "endereco": "Av. Teste, 1000 - Centro", "telefone": "(11) 4000-0000",
    "email": "contato@locadoraexemplo.com",
    "contrato_clausulas": "Cláusula personalizada de teste sobre limite de KM diário.\nCláusula personalizada sobre taxa de limpeza.",
    "contrato_texto_extra": "Condição extra de teste.",
    "contrato_rodape": "Rodapé personalizado de teste.",
    "logo": (io.BytesIO(_logo_bytes), "logo.png"),
}, content_type="multipart/form-data", follow_redirects=False), 302)

# 7. Contrato - gerar PDF
check("POST gerar contrato", client.post("/contratos/locacao/1/gerar", follow_redirects=False), 302)

# 7a. Confirma que a personalização de fato entrou no PDF gerado
from pypdf import PdfReader  # noqa: E402 (import tardio só para esta checagem)
_pdf_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "uploads", "contratos", "contrato_locacao_1.pdf")
_texto_pdf = "".join(p.extract_text() or "" for p in PdfReader(_pdf_path).pages)
for trecho in ("Locadora Exemplo LTDA", "12.345.678/0001-90", "limite de KM diário", "Rodapé personalizado de teste"):
    assert trecho in _texto_pdf, f"Personalização não encontrada no PDF: {trecho!r}"
print("OK  Confirmado: contrato gerado reflete a personalização da empresa")

# 7b. Contrato - upload manual
data = {"arquivo": (io.BytesIO(b"%PDF-1.4 fake pdf content"), "contrato_assinado.pdf")}
check("POST upload contrato", client.post("/contratos/locacao/1/upload", data=data, content_type="multipart/form-data", follow_redirects=False), 302)

# 8. Financeiro - listar e marcar pago
check("GET financeiro listar", client.get("/financeiro/"))
check("POST financeiro pagar (id=1)", client.post("/financeiro/1/pagar", data={"forma_pagamento": "pix"}, follow_redirects=False), 302)

# 9. Vistoria com foto
img_bytes = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
    b"\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x03\x01\x01\x00\x18\xdd\x8d\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)
data = {
    "veiculo_id": "1", "tipo": "semanal", "data": "2026-09-12", "km": "15100",
    "condicao_geral": "ok", "observacoes": "tudo certo",
    "fotos": (io.BytesIO(img_bytes), "foto1.png"),
}
check("POST vistoria nova", client.post("/vistorias/nova", data=data, content_type="multipart/form-data", follow_redirects=False), 302)
check("GET vistoria detalhe", client.get("/vistorias/1"))
check("GET vistorias listar", client.get("/vistorias/"))

# 10. Finalizar locação
check("POST finalizar locacao", client.post("/locacoes/1/finalizar", data={
    "data_fim_real": "2026-09-19", "km_final": "15400", "caucao_status": "devolvido",
}, follow_redirects=False), 302)
check("GET locacao finalizada", client.get("/locacoes/1"))
check("GET veiculo disponivel novamente", client.get("/veiculos/1"))

# 11. Dashboard final
check("GET / dashboard final", client.get("/"))

# 12. Usuários e permissões
check("GET usuarios listar (admin)", client.get("/usuarios/"))
check("POST usuarios novo (operador)", client.post("/usuarios/novo", data={
    "nome": "Operador Teste", "email": "operador@teste.com", "senha": "senha123", "papel": "operador",
}, follow_redirects=False), 302)

# Loga como operador em um cliente separado (sem afetar a sessão do admin)
op_client = app.test_client()
check("POST login operador", op_client.post("/login", data={"email": "operador@teste.com", "senha": "senha123"}, follow_redirects=False), 302)
check("GET / como operador", op_client.get("/"))
check("GET /usuarios/ bloqueado para operador", op_client.get("/usuarios/", follow_redirects=False), 302)
check("POST excluir proprietario bloqueado para operador", op_client.post("/proprietarios/1/excluir", follow_redirects=False), 302)

# Confirma que o proprietário NÃO foi excluído (ação bloqueada de fato, não só redirecionada)
resp = check("GET proprietarios listar após tentativa bloqueada", client.get("/proprietarios/"))
assert b"Carlos Propriet" in resp.data, "Proprietario nao deveria ter sido excluido pelo operador"
print("OK  Confirmado: operador não conseguiu excluir o proprietário")

# 13. Páginas institucionais (públicas, sem login)
anon_client = app.test_client()
resp = check("GET /privacidade (sem login)", anon_client.get("/privacidade"))
assert b"Pol\xc3\xadtica de Privacidade" in resp.data or "Política de Privacidade".encode() in resp.data
resp = check("GET /termos (sem login)", anon_client.get("/termos"))
assert "Termos de Uso".encode() in resp.data
check("GET /privacidade (logado)", client.get("/privacidade"))
check("GET /termos (logado)", client.get("/termos"))
print("OK  Confirmado: páginas institucionais acessíveis logado e deslogado")

# 14. Tela de login redesenhada (branding + link de esqueci senha)
resp = check("GET /login (tela redesenhada)", anon_client.get("/login"))
assert b"LocaFlow" in resp.data
assert b"esqueci-senha" in resp.data or b"Esqueci minha senha" in resp.data
print("OK  Confirmado: tela de login traz marca LocaFlow e link de redefinição de senha")

# 15. Redefinição de senha (fluxo completo, sem SMTP configurado -> link exibido na tela)
check("GET /esqueci-senha", anon_client.get("/esqueci-senha"))
resp = check("POST /esqueci-senha (email existente)", anon_client.post(
    "/esqueci-senha", data={"email": "operador@teste.com"}, follow_redirects=False
))
assert b"redefinir-senha" in resp.data, "Sem SMTP configurado, o link deveria aparecer na tela"
import re
m = re.search(rb"/redefinir-senha/([\w\-]+)", resp.data)
assert m, "Token de redefinicao nao encontrado na resposta"
token = m.group(1).decode()
check("GET /redefinir-senha/<token> (valido)", anon_client.get(f"/redefinir-senha/{token}"))
check("POST /redefinir-senha/<token> (nova senha)", anon_client.post(
    f"/redefinir-senha/{token}", data={"senha_nova": "novaSenha123", "senha_confirmar": "novaSenha123"},
    follow_redirects=False,
), 302)
check("POST login com nova senha", anon_client.post(
    "/login", data={"email": "operador@teste.com", "senha": "novaSenha123"}, follow_redirects=False
), 302)
anon_client.get("/logout")  # sai da sessão para poder ver a página pública de novo
resp = check("GET /redefinir-senha/<token> (ja usado)", anon_client.get(f"/redefinir-senha/{token}"))
assert b"inv\xc3\xa1lido" in resp.data or "inválido".encode() in resp.data
print("OK  Confirmado: fluxo de redefinição de senha funciona de ponta a ponta")

# Email desconhecido não deve revelar se existe ou não (mensagem neutra, sem link)
resp = check("POST /esqueci-senha (email inexistente)", anon_client.post(
    "/esqueci-senha", data={"email": "naoexiste@teste.com"}, follow_redirects=False
))
assert b"redefinir-senha" not in resp.data
print("OK  Confirmado: e-mail inexistente não vaza informação nem gera link")

print("\nTODOS OS TESTES PASSARAM ✅")
