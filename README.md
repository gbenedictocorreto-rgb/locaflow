# LocaFlow — Gestão inteligente para locadoras

Sistema web para controlar a locação dos seus veículos: para quem cada carro
está alugado, quilometragem rodada, contrato (gerado automaticamente ou
enviado por upload), controle financeiro, caução, vistoria semanal com fotos,
dados do veículo (placa, renavam, chassi, cor, proprietário), link do
rastreador, seguradora com telefone de assistência 24h, inadimplência e score
do cliente, e campo de antecedentes criminais.

Desenvolvido por **Gilmar Alves**. O nome do produto, o rodapé de crédito e o
texto de "solicite uma demonstração" da tela de login vêm de `config.py`
(constantes `APP_NAME`, `APP_TAGLINE`, `DEVELOPER_NAME`, `DEMO_CONTATO_TEXTO`
e `DEMO_CONTATO_LINK`) — ajuste ali se um dia quiser vender sob outra marca.

## Tecnologia usada

- **Python + Flask** (backend e páginas), sem necessidade de Node/npm.
- **SQLite** como banco de dados (um único arquivo, sem servidor de banco
  separado para começar).
- **ReportLab** para gerar o PDF do contrato automaticamente.
- HTML/CSS próprio, sem dependência de internet para funcionar (nenhuma
  biblioteca externa é carregada via CDN).

Não é necessário instalar Node.js nem `npm` para rodar este sistema.

## Como rodar na sua máquina

1. Tenha o Python 3.10+ instalado.
2. Dentro da pasta do projeto, crie um ambiente virtual e instale as
   dependências:

   ```bash
   python3 -m venv venv
   source venv/bin/activate        # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Rode o sistema:

   ```bash
   python app.py
   ```

4. Acesse **http://localhost:5000** no navegador.

Na primeira execução, o sistema cria automaticamente o banco de dados
(`instance/locacao.db`) e um usuário administrador padrão:

- **E-mail:** `admin@locacao.com`
- **Senha:** `admin123`

**Troque essa senha assim que possível** pelo menu "Alterar senha" na barra
lateral, ou crie outro usuário administrador pelo terminal:

```bash
flask --app app.py criar-usuario "Seu Nome" seuemail@exemplo.com suasenha123
```

## Estrutura do sistema

- **Painel** — visão geral: veículos disponíveis/alugados, valores a
  receber, inadimplência, devoluções próximas e veículos sem vistoria
  recente.
- **Locações** — vincula cliente + veículo, controla datas, KM inicial/final,
  valor da diária, caução e status (ativa, atrasada, finalizada, cancelada).
  Ao criar uma locação, o veículo muda automaticamente para "alugado" e um
  lançamento financeiro do aluguel (e da caução, se houver) é criado.
- **Veículos** — placa, renavam, chassi, cor, marca/modelo/ano, KM atual,
  proprietário responsável, link do rastreador, seguradora e telefone de
  assistência 24h (reboque), foto do veículo.
- **Clientes** — dados pessoais, CNH, campo de antecedentes criminais
  (verificado sim/não + link de consulta pública, ex.: emissão de certidão no
  gov.br — você pode trocar por um site do estado do cliente) e **score**
  (Bom pagador / Atenção / Inadimplente), calculado automaticamente pelo
  histórico de pagamentos em atraso, com opção de ajuste manual.
- **Financeiro** — lançamentos a receber (aluguel, caução, multa, dano,
  outro), marcação de pago/atrasado, atualizado automaticamente quando o
  vencimento passa.
- **Contratos** — dentro de cada locação, é possível **gerar automaticamente**
  um contrato em PDF já preenchido com os dados do cliente, veículo e
  condições da locação, ou **enviar** um contrato próprio (PDF, Word ou
  imagem).
- **Vistorias** — registro semanal (ou de entrada/saída) do veículo, com
  KM, condição geral e upload de várias fotos.
- **Proprietários** — donos dos veículos administrados por você, para saber
  de quem é cada carro.
- **Usuários** (menu visível só para administradores) — permite cadastrar
  mais de uma pessoa com acesso ao sistema, cada uma com um papel:
  - **Administrador**: acesso total, incluindo excluir registros e
    gerenciar outros usuários.
  - **Operador**: usa o dia a dia do sistema (cadastros, locações,
    vistorias, gerar contrato, marcar pagamentos) mas não pode excluir
    registros nem gerenciar usuários.

  Crie o primeiro operador pela tela "Usuários" (como administrador) ou
  pelo terminal:

  ```bash
  flask --app app.py criar-usuario "Nome do Funcionário" funcionario@exemplo.com senha123 operador
  ```

- **Configurações** (menu visível só para administradores) — nome da
  empresa/locadora, CNPJ, endereço, telefone, e-mail, logo, e o **modelo do
  contrato** (cláusulas, condições específicas e rodapé), tudo editável pela
  tela, sem mexer em código. Isso é o que permite usar este mesmo sistema
  para diferentes clientes/locadoras — cada instalação (cada cópia do
  sistema) tem sua própria configuração e seu próprio modelo de contrato.
- **Tela de login** — traz a marca LocaFlow, uma ilustração própria (SVG
  desenhado no próprio código, sem imagem externa) e uma chamada para quem
  ainda não é cliente ("Solicite uma demonstração", configurável em
  `config.py`). Inclui o link **"Esqueci minha senha"**.
- **Redefinição de senha** — fluxo próprio de "esqueci minha senha"
  (`/esqueci-senha` → link por e-mail → `/redefinir-senha/<token>`), com
  token de uso único e validade de 60 minutos. Veja a seção
  [E-mail (redefinição de senha)](#e-mail-redefinição-de-senha) abaixo.
- **Política de Privacidade e Termos de Uso** — páginas públicas
  (`/privacidade` e `/termos`), acessíveis com ou sem login, linkadas no
  rodapé de todas as telas. São um **modelo inicial** (ver aviso na própria
  página) — revise com um advogado antes de usar com clientes reais.

## Vendendo este sistema para outras locadoras

Este sistema foi feito para funcionar como **uma instalação isolada por
cliente**: cada locadora que usar o sistema tem sua própria cópia rodando,
com seu próprio banco de dados, login e configuração — não há dados
compartilhados entre clientes diferentes. Para atender um novo cliente:

1. Faça uma nova implantação (deploy) separada — repositório, hospedagem e
   banco de dados próprios para aquele cliente (veja a seção abaixo).
2. No primeiro acesso, entre em **Configurações** e preencha os dados
   daquela empresa (nome, CNPJ, logo, cláusulas do contrato).
3. Crie o(s) usuário(s) daquele cliente pela tela **Usuários**.

Não misture a instalação de um cliente com a de outro, nem com o seu
próprio uso pessoal do sistema (se você também usar para o seu negócio) —
mantenha repositórios, contas de hospedagem e bancos de dados separados
para cada um.

## Sobre a consulta de antecedentes criminais

Por não existir uma API pública nacional única e gratuita para isso, o
sistema guarda um campo "verificado" (sim/não), a data da verificação, uma
observação livre e um **link de consulta** (pré-preenchido com o serviço de
emissão de certidão de antecedentes do gov.br, mas você pode trocar por um
link do Tribunal de Justiça do estado do cliente). Você consulta pelo link e
marca o resultado manualmente no cadastro do cliente.

## E-mail (redefinição de senha)

Por padrão, o sistema **não exige** um servidor de e-mail configurado: se um
usuário clicar em "Esqueci minha senha" e a variável `MAIL_SERVER` não
estiver definida, o link de redefinição aparece diretamente na tela (útil
para testar ou para uso interno/local). Isso é intencional para simplificar
o primeiro uso, mas em produção com clientes reais, configure um SMTP de
verdade para que o link só seja recebido por quem realmente é dono daquele
e-mail. Defina estas variáveis de ambiente:

```
MAIL_SERVER=smtp.seuservico.com
MAIL_PORT=587
MAIL_USERNAME=seu-usuario
MAIL_PASSWORD=sua-senha
MAIL_FROM=LocaFlow <no-reply@suaempresa.com.br>
SITE_URL=https://sualocadora.onrender.com
```

(Qualquer provedor SMTP funciona — Gmail, SendGrid, Amazon SES, etc.)

### Recomendado: Brevo (gratuito, feito para esse tipo de e-mail)

Um serviço de e-mail transacional (em vez do SMTP comum do Gmail) chega com
menos chance de cair em spam e não tem o limite baixo de envios diários do
Gmail. O [Brevo](https://www.brevo.com) (antigo Sendinblue) tem plano
gratuito que cobre bem esse uso:

1. Crie uma conta no Brevo com o e-mail do LocaFlow (separado da sua conta
   pessoal/do CRM).
2. Em **Configurações → SMTP e API → SMTP**, gere uma "chave SMTP" — é um
   login e senha específicos para envio, diferentes da senha da sua conta.
3. Em **Expedidores** (Senders), cadastre e verifique o e-mail que vai
   aparecer como remetente (ex.: `contato@locaflow.com.br` ou o e-mail que
   você criou para o LocaFlow) — sem isso, o envio pode falhar ou cair em
   spam.
4. Configure as variáveis de ambiente na sua hospedagem (Render/Railway):

   ```
   MAIL_SERVER=smtp-relay.brevo.com
   MAIL_PORT=587
   MAIL_USERNAME=<login SMTP gerado no Brevo>
   MAIL_PASSWORD=<chave SMTP gerada no Brevo>
   MAIL_FROM=LocaFlow <e-mail verificado no passo 3>
   SITE_URL=<URL pública do seu sistema em produção>
   ```

Nenhuma mudança de código é necessária — o sistema já lê essas variáveis
automaticamente e passa a enviar o link de redefinição por e-mail de verdade
assim que `MAIL_SERVER` estiver definido.

## Levar para produção / acessar de qualquer lugar

O jeito mais simples de deixar o sistema acessível pela internet (para você
acessar do celular, por exemplo) é publicar em um serviço como Render,
Railway ou uma VPS simples:

1. Suba este projeto para um repositório no GitHub.
2. Em serviços como Render/Railway, aponte para o repositório e use o
   comando de start: `gunicorn app:app` (o `gunicorn` já está no
   `requirements.txt`).
3. Defina a variável de ambiente `SECRET_KEY` com um valor aleatório e
   seguro (não deixe o valor padrão do `config.py` em produção).

**Sobre o banco de dados:** o SQLite (um arquivo `.db`) funciona bem para
começar e para uso de uma pessoa/pequena equipe. Se no futuro você quiser
múltiplos usuários simultâneos, mais robustez ou fazer backup em nuvem, o
código está organizado em `db.py` de forma que trocar para PostgreSQL (por
exemplo, um banco Supabase, como no seu CRM Nexo Gestão) exige mudanças
pontuais, sem precisar reescrever as telas.

**Fotos e contratos enviados** ficam salvos em `static/uploads/`. Se for
hospedar em um serviço com disco temporário (como certas configurações do
Render/Railway), vale configurar um "disco persistente" para essa pasta, ou
migrar futuramente para um serviço de armazenamento em nuvem.

## Testando o sistema

Existe um teste automatizado que percorre o fluxo completo (login,
cadastro de proprietário/veículo/cliente, criação de locação, geração de
contrato, upload de contrato, lançamento financeiro, vistoria com foto,
finalização da locação, usuários/permissões, páginas institucionais e o
fluxo de redefinição de senha de ponta a ponta):

```bash
python tests/smoke_test.py
```

(Rode com o banco ainda vazio ou apague `instance/locacao.db` antes, já que
o teste cria registros de exemplo com CPF/placa fixos.)
