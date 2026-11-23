# Bônus em PDF do curso Minha Marca Registrada (Hotmart)
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table,
                                TableStyle, PageBreak, KeepTogether)
from reportlab.lib.styles import ParagraphStyle

AQUI = os.path.dirname(os.path.abspath(__file__))
F = os.path.join(AQUI, 'fontes')
pdfmetrics.registerFont(TTFont('Serif', os.path.join(F, 'Fraunces.ttf')))
pdfmetrics.registerFont(TTFont('Sans', os.path.join(F, 'Jost.ttf')))
SYM = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
pdfmetrics.registerFont(TTFont('Sym', SYM if os.path.exists(SYM) else os.path.join(F, 'Jost.ttf')))
LOGO = os.path.join(AQUI, 'logo.png')

ROXO = colors.HexColor('#1c1328'); OURO = colors.HexColor('#c9a24a'); VERDE = colors.HexColor('#2f9e6b')
TINTA = colors.HexColor('#24182f'); CINZA = colors.HexColor('#5d5468'); CLARO = colors.HexColor('#f5f0e6')

S = {
    'h1': ParagraphStyle('h1', fontName='Serif', fontSize=24, leading=29, textColor=TINTA, spaceAfter=6),
    'sub': ParagraphStyle('sub', fontName='Sans', fontSize=11.5, leading=16, textColor=CINZA, spaceAfter=14),
    'h2': ParagraphStyle('h2', fontName='Serif', fontSize=15, leading=19, textColor=TINTA, spaceBefore=12, spaceAfter=6),
    'p': ParagraphStyle('p', fontName='Sans', fontSize=10.5, leading=15, textColor=TINTA, spaceAfter=5),
    'li': ParagraphStyle('li', fontName='Sans', fontSize=10.5, leading=15, textColor=TINTA, leftIndent=16, bulletIndent=2, spaceAfter=3, bulletFontName='Sym', bulletFontSize=10),
    'nota': ParagraphStyle('nota', fontName='Sans', fontSize=9, leading=12.5, textColor=CINZA, spaceBefore=8),
    'cel': ParagraphStyle('cel', fontName='Sans', fontSize=9.5, leading=12.5, textColor=TINTA),
    'celb': ParagraphStyle('celb', fontName='Sans', fontSize=9.5, leading=12.5, textColor=colors.white),
}

def capa_e_rodape(titulo):
    def desenhar(c, doc):
        w, h = A4
        c.saveState()
        c.setFillColor(ROXO); c.rect(0, h - 22 * mm, w, 22 * mm, stroke=0, fill=1)
        if os.path.exists(LOGO):
            c.drawImage(LOGO, 16 * mm, h - 17 * mm, 12 * mm, 12 * mm, mask='auto')
        c.setFillColor(colors.white); c.setFont('Serif', 12); c.drawString(31 * mm, h - 12.5 * mm, 'MAGYSTIC')
        c.setFillColor(OURO); c.setFont('Sans', 8.5); c.drawRightString(w - 16 * mm, h - 12.5 * mm, 'CURSO MINHA MARCA REGISTRADA · BÔNUS')
        c.setFillColor(CINZA); c.setFont('Sans', 8)
        c.drawString(16 * mm, 10 * mm, titulo)
        c.drawRightString(w - 16 * mm, 10 * mm, f'magystic.com/curso  ·  página {doc.page}')
        c.restoreState()
    return desenhar

def doc(arq, titulo, story):
    d = BaseDocTemplate(arq, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=32 * mm, bottomMargin=20 * mm,
                        title=titulo, author='Roberto Carrer · MAGYSTIC')
    fr = Frame(d.leftMargin, d.bottomMargin, d.width, d.height, id='f')
    d.addPageTemplates([PageTemplate(id='p', frames=[fr], onPage=capa_e_rodape(titulo))])
    d.build(story)

def P(t, s='p'): return Paragraph(t, S[s])
def L(itens, marca='•'): return [Paragraph(i, S['li'], bulletText=marca) for i in itens]
def caixas(itens): return [Paragraph(i, S['li'], bulletText='☐') for i in itens]

def tabela(linhas, larg, cab=True):
    alt=[None if any(str(c) for c in l) else 20 for l in linhas]
    dados = [[Paragraph(str(c), S['celb'] if (cab and i == 0) else S['cel']) for c in l] for i, l in enumerate(linhas)]
    t = Table(dados, colWidths=larg, rowHeights=alt, repeatRows=1 if cab else 0)
    est = [('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#d9cfe0')), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
           ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 5)]
    if cab:
        est += [('BACKGROUND', (0, 0), (-1, 0), ROXO)]
    for i in range(1 if cab else 0, len(linhas)):
        if i % 2 == 0: est.append(('BACKGROUND', (0, i), (-1, i), CLARO))
    t.setStyle(TableStyle(est)); return t

AVISO = ('As telas e as taxas do INPI mudam com o tempo. Antes de pagar ou protocolar, confira a página oficial de '
         'custos do INPI (gov.br/inpi) e o Manual de Marcas. Este material é educativo e não substitui orientação '
         'jurídica para casos específicos.')

OUT = os.path.join(AQUI, 'export', 'bonus'); os.makedirs(OUT, exist_ok=True)

# ------------------------------------------------------------------ 1. Guia do pedido no e-INPI
s = [P('Guia do pedido no e-INPI', 'h1'),
     P('O passo a passo do Módulo 6 numa folha de consulta: do cadastro ao número do processo.', 'sub'),
     P('Antes de começar: separe numa pasta', 'h2')]
s += caixas(['CPF ou CNPJ do titular (o mesmo em tudo: cadastro, GRU e formulário).',
             'Nome da marca escrito exatamente como você quer proteger (com ou sem acento, junto ou separado).',
             'Apresentação (nominativa, mista, figurativa) e natureza (produto ou serviço).',
             'Logo em JPG, se a marca for mista ou figurativa (regras na etapa 4).',
             'Classe principal e a lista de itens da especificação pré-aprovada.',
             'Relatório da busca de anterioridade (Módulo 5).'])
etapas = [
    ('1. Cadastro no e-INPI (uma vez só)', [
        'No site do INPI, abra o "Cadastro no e-INPI" e escolha a modalidade <b>Cliente</b>.',
        'Preencha nome, CPF ou CNPJ, endereço e um e-mail que você lê sempre.',
        'Informe a <b>natureza jurídica</b> certa (pessoa física, MEI, ME etc.): é ela que define o desconto.',
        'Senha de 6 a 10 caracteres, sem espaços e sem caracteres especiais. Cada CPF/CNPJ tem um cadastro só.']),
    ('2. Emitir a GRU', [
        'No módulo de GRU, entre com o login do e-INPI e escolha a unidade <b>Marcas</b>.',
        'Código <b>389</b>: especificação pré-aprovada (o caminho do curso). Código <b>394</b>: especificação livre.',
        'Informe apresentação e natureza e anote o <b>"Nosso Número"</b> da guia.',
        'Uma GRU vale para um serviço e uma classe. Mais classes = mais pedidos, cada um com a sua GRU.']),
    ('3. Pagar e esperar a conciliação', [
        'Pague de verdade antes do protocolo: agendamento não vale.',
        'A conciliação bancária costuma sair no dia seguinte. Preencha o pedido depois disso.',
        'Salve o comprovante em PDF na pasta da marca.',
        'O INPI não envia boletos nem cobranças. Emita a GRU sempre você mesmo.']),
    ('4. Abrir o e-Marcas', [
        'Entre com o mesmo login e digite o "Nosso Número" da GRU paga.',
        'A sessão dura 30 minutos: tenha tudo separado antes de abrir.',
        'A opção "Alterar" (apresentação/natureza) apaga o que já foi preenchido.',
        'Logo: JPG, mínimo 945 x 945 px, 300 dpi, até 2 MB, fundo liso, uma figura só, sem ® ou ™.']),
    ('5. Preencher e revisar', [
        'Titular: nome igual ao documento, CPF/CNPJ igual ao da GRU.',
        'Marca: nome exato; imagem certa se for mista ou figurativa.',
        'Classe: uma por pedido. Marque só os itens que você faz ou tem plano concreto de fazer.',
        'Não marque a classe inteira "por garantia".']),
    ('6. Protocolar e guardar', [
        'Marque a declaração de veracidade, clique em Avançar e depois em Protocolar.',
        'Salve o recibo em PDF e anote o <b>número do processo (9 dígitos)</b> e o número do protocolo.',
        'A data do envio é a data de depósito: a partir dela, a sua prioridade está garantida.',
        'A partir de agora: "Marca com pedido de registro no INPI" (o ® só depois da concessão).']),
]
for t, itens in etapas:
    s.append(KeepTogether([P(t, 'h2')] + caixas(itens)))
s.append(P('Valores de referência (tabela usada no curso, por classe)', 'h2'))
s.append(tabela([['Serviço', 'Valor cheio', 'Com desconto de 50%'],
                 ['389 · pedido com especificação pré-aprovada', 'R$ 880', 'R$ 440'],
                 ['394 · pedido com especificação livre', 'R$ 1.720', 'R$ 860']], [80 * mm, 40 * mm, 54 * mm]))
s.append(P('O desconto vale para pessoa física (com condições), MEI, ME, EPP e outros casos. Pessoas no CadÚnico e '
           'pessoas com deficiência podem ter isenção, com comprovação. ' + AVISO, 'nota'))
doc(os.path.join(OUT, '01-guia-do-pedido-no-e-INPI.pdf'), 'Guia do pedido no e-INPI', s)

# ------------------------------------------------------------------ 2. Checklist de busca de anterioridade
s = [P('Checklist de busca de anterioridade', 'h1'),
     P('Use antes de pagar a GRU. A taxa não volta se o pedido for negado por colidência.', 'sub'),
     P('Nome pesquisado: ______________________________   Classe principal: ______', 'p'),
     P('1. Busca no INPI (pePI, gratuita)', 'h2')]
s += caixas(['Abri busca.inpi.gov.br/pePI › Marcas (dá para entrar sem login, clicando em Continuar).',
             '<b>Busca exata</b> só com o núcleo do nome, sem palavras do ramo, com a classe em branco.',
             '<b>Busca por radical</b>, com e sem a classe principal. Se o nome junta palavras, pesquisei cada parte.',
             '<b>Variações fonéticas</b>: C/K, S/Z, I/Y, com e sem H, letras dobradas, plural.',
             'Abri cada resultado parecido e li a classe, a situação e os produtos/serviços.',
             'Conferi também as <b>classes afins</b> (o cliente acharia que vem da mesma empresa?).'])
s.append(P('2. Busca fora do INPI', 'h2'))
s += caixas(['Google (nome entre aspas + ramo).', 'Instagram, TikTok, Facebook e YouTube.',
             'Marketplaces (Mercado Livre, Shopee, Amazon, iFood quando fizer sentido).',
             'Domínios .com.br (Registro.br) e .com.', 'Nomes de empresas (Junta Comercial / consulta de CNPJ).',
             'Lembrete: quem usa o nome de boa-fé há pelo menos 6 meses pode ter preferência e pode se opor.'])
s.append(P('3. Anote os resultados relevantes', 'h2'))
s.append(tabela([['Marca encontrada', 'Processo', 'Classe', 'Situação', 'Ramo é igual ou afim?']] + [[''] * 5 for _ in range(7)],
                [45 * mm, 28 * mm, 18 * mm, 30 * mm, 53 * mm]))
s.append(P('4. Decisão (matriz de risco do Módulo 5)', 'h2'))
s.append(tabela([['Sinal', 'O que encontrei', 'O que fazer'],
                 ['Vermelho', 'Marca igual ou muito parecida, em vigor ou em andamento, no mesmo ramo ou ramo afim.', 'Troque o nome.'],
                 ['Amarelo', 'Conflitos fracos ou duvidosos: parecida em ramo distante, só parte do nome igual, uso informal.', 'Ajuste o nome com cuidado e refaça a busca.'],
                 ['Verde', 'Nada relevante no INPI nem fora dele.', 'Siga para o pedido (Módulo 6).']],
                [24 * mm, 100 * mm, 50 * mm]))
s.append(P('Minha decisão: <font name="Sym">☐</font> Verde, sigo   <font name="Sym">☐</font> Amarelo, ajusto para: ____________________   <font name="Sym">☐</font> Vermelho, troco', 'p'))
s.append(P('A busca reduz o risco, mas não dá 100% de certeza: pedidos recentes podem ainda não aparecer na base.', 'nota'))
doc(os.path.join(OUT, '02-checklist-busca-de-anterioridade.pdf'), 'Checklist de busca de anterioridade', s)

# ------------------------------------------------------------------ 3. Mapa de classes de Nice
s = [P('Mapa de classes para negócios comuns', 'h1'),
     P('Ponto de partida para escolher a classe. Confirme sempre os itens na lista oficial do INPI.', 'sub')]
s.append(tabela([
    ['Negócio', 'Classe principal', 'Pense também em'],
    ['Restaurante, lanchonete, bar, cafeteria', '43 · serviços de alimentação', 'Classe do produto, se vender embalado com a marca (ex.: 30, 32)'],
    ['Loja de roupas', '35 · comércio', '25 · se a marca vai nas próprias peças'],
    ['Marca de roupa (confecção)', '25 · vestuário, calçados, chapelaria', '35 · se tiver loja própria'],
    ['Aplicativo baixável', '9 · software e apps', '42 · SaaS e desenvolvimento; classe do serviço que o app presta (ex.: 39)'],
    ['Plataforma online (SaaS)', '42 · software como serviço', '9 · se também houver app para baixar'],
    ['Cosméticos e higiene', '3 · cosméticos, perfumes, sabonetes', '35 · loja própria'],
    ['Consultoria de negócios / marketing', '35', '42 · consultoria em tecnologia'],
    ['Serviços jurídicos', '45', '41 · se der cursos e palestras'],
    ['Salão de beleza, estética, clínica', '44', '3 · se tiver linha própria de produtos'],
    ['Escola, curso, evento, infoproduto', '41 · educação e entretenimento', '9 · conteúdo baixável; 16 · material impresso'],
    ['Padaria, doces, café', '30', '43 · se servir no local'],
    ['Cerveja e bebidas não alcoólicas', '32', '33 · vinhos e destilados; 43 · bar'],
    ['Vinhos e destilados', '33', '35 · loja'],
    ['Loja virtual / marketplace próprio', '35 · comércio', 'Classes dos produtos que levam a marca'],
], [55 * mm, 52 * mm, 67 * mm]))
s.append(P('Regras de ouro', 'h2'))
s += L(['Produtos ficam nas classes 1 a 34; serviços, nas classes 35 a 45.',
        'Uma classe por pedido. Precisa de mais? Faça outros pedidos, cada um com a sua GRU.',
        'Comece pela classe do que você vende hoje; planeje as próximas pelo que tem plano concreto de lançar.',
        'Classe 35 é "comércio e gestão": não protege o produto em si.',
        'Use os termos da lista pré-aprovada (GRU 389): eles dispensam análise de adequação.'])
s.append(P('Minha classe principal: ______   Próximas classes: ______  ______  ______', 'p'))
doc(os.path.join(OUT, '03-mapa-de-classes-de-nice.pdf'), 'Mapa de classes de Nice', s)

# ------------------------------------------------------------------ 4. Agenda de prazos do processo
s = [P('Agenda de prazos do processo', 'h1'),
     P('O INPI não avisa por carta: tudo é publicado na RPI (toda terça-feira) e os prazos contam da publicação.', 'sub')]
s.append(tabela([
    ['Etapa', 'Prazo', 'Se perder'],
    ['Exigência formal', '5 dias corridos', 'Pedido considerado inexistente'],
    ['Oposição de terceiros (art. 158)', '60 dias da publicação do pedido', '—'],
    ['Manifestação contra oposição', '60 dias', 'O examinador decide sem a sua defesa'],
    ['Exigência de mérito', '60 dias', 'Pedido arquivado'],
    ['Recurso contra indeferimento (art. 212)', '60 dias da publicação', 'Decisão fica definitiva'],
    ['Concessão após deferimento (art. 162)', '60 dias + 30 extraordinários', 'Pedido aprovado é arquivado'],
    ['Prorrogação do registro (art. 133)', 'Último ano de vigência, ou 6 meses depois com taxa maior', 'Registro extinto'],
    ['Uso da marca (art. 143)', 'Não ficar 5 anos sem usar', 'Registro pode caducar'],
], [62 * mm, 58 * mm, 54 * mm]))
s.append(P('Linha do tempo típica', 'h2'))
s += L(['Depósito, exame formal (cerca de 60 dias), publicação para oposição, exame de mérito, decisão e concessão.',
        'Segundo o INPI: cerca de 18 meses sem oposição e 22 meses com oposição.',
        'O certificado fica disponível cerca de 60 dias após a concessão. O registro vale 10 anos e pode ser prorrogado sempre.'])
s.append(P('Minha agenda', 'h2'))
s.append(tabela([['Data da RPI', 'Despacho / o que aconteceu', 'Prazo final', 'Feito?']] + [[''] * 4 for _ in range(6)],
                [30 * mm, 82 * mm, 34 * mm, 28 * mm]))
s.append(P('Rotina: toda terça, consulte o seu processo no pePI pelo número de 9 dígitos. Mensagens e boletos '
           'cobrando "taxas do INPI" são golpe. ' + AVISO, 'nota'))
doc(os.path.join(OUT, '04-agenda-de-prazos-do-processo.pdf'), 'Agenda de prazos do processo', s)
print(os.listdir(OUT))
