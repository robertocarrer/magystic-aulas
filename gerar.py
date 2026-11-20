#!/usr/bin/env python3
"""Gera o vídeo narrado (9:16) de uma aula do curso grátis da MAGYSTIC e envia para magystic.com.

Uso:
  python gerar.py              -> gera as aulas pendentes (até MAX_VIDEOS)
  python gerar.py 0 1          -> gera aulas específicas
Variáveis: GEMINI_API_KEY (narração), SEM_VOZ=1 (teste sem narração), NAO_ENVIAR=1 (não envia ao site)
"""
import os, sys, json, re, time, wave, base64, struct, subprocess, urllib.request, urllib.error
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SITE = os.environ.get('SITE', 'https://magystic.com')
KEY = os.environ.get('GEMINI_API_KEY', '').strip()
SEM_VOZ = os.environ.get('SEM_VOZ') == '1' or not KEY
NAO_ENVIAR = os.environ.get('NAO_ENVIAR') == '1'
MAX_VIDEOS = int(os.environ.get('MAX_VIDEOS', '9'))
SO_CAPA = os.environ.get('SO_CAPA', '').strip().lower() in ('1', 'true', 'sim')
VOZ = os.environ.get('VOZ', 'Kore')
AQUI = os.path.dirname(os.path.abspath(__file__))
FONTES = os.environ.get('FONTES', os.path.join(AQUI, 'fontes'))
SAIDA = os.environ.get('SAIDA', os.path.join(AQUI, 'saida'))
UA = 'Mozilla/5.0 (compatible; magystic-aulas/1.0; +https://magystic.com/curso)'
GAPI = 'https://generativelanguage.googleapis.com/v1beta'

W, H, FPS = 1080, 1920, 30
FUNDO = (21, 13, 31); SUPER = (34, 23, 50); OURO = (217, 180, 104); VERDE = (95, 209, 148)
TINTA = (243, 238, 247); DIM = (197, 186, 210); APAGADO = (146, 137, 162); VERDE_TINTA = (16, 40, 28)
PAUSA = 0.45

# ---------------------------------------------------------------- rede

def http(url, data=None, headers=None, timeout=180, method=None):
    h = {'user-agent': UA}
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

class CotaDiaria(Exception):
    pass

def gemini(modelo, corpo, tentativas=7):
    for i in range(tentativas):
        try:
            return json.loads(http(f'{GAPI}/models/{modelo}:generateContent', json.dumps(corpo).encode(),
                                   {'content-type': 'application/json', 'x-goog-api-key': KEY}))
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors='replace')[:400]
            if e.code == 429 and ('PerDay' in msg or 'per day' in msg.lower() or 'free_tier_requests' in msg):
                raise CotaDiaria(msg)
            if e.code in (429, 500, 502, 503, 504) and i < tentativas - 1:
                espera = 25 * (i + 1)
                print(f'  Gemini {e.code}, tentando de novo em {espera}s')
                time.sleep(espera)
                continue
            raise RuntimeError(f'Gemini {e.code}: {msg}')

def escolher_modelos():
    txt = os.environ.get('MODELO_TEXTO'); tts = os.environ.get('MODELO_VOZ')
    if txt and tts:
        return txt, tts
    j = json.loads(http(f'{GAPI}/models?pageSize=300', headers={'x-goog-api-key': KEY}))
    nomes = [m['name'].split('/')[-1] for m in j.get('models', [])
             if 'generateContent' in m.get('supportedGenerationMethods', [])]
    vozes = [n for n in nomes if 'tts' in n]
    textos = [n for n in nomes if 'flash' in n and not any(x in n for x in ('tts', 'image', 'lite', 'audio', 'live', 'exp'))]
    def pref(lista, ordem):
        for p in ordem:
            if p in lista:
                return p
        return lista[0] if lista else None
    return (txt or pref(textos, ['gemini-3.8-flash', 'gemini-flash-latest', 'gemini-2.5-flash']),
            tts or pref(vozes, ['gemini-2.5-flash-preview-tts', 'gemini-2.5-flash-tts']))

# ---------------------------------------------------------------- roteiro e voz

def roteiro(a, modelo):
    prox = a.get('proxima')
    fim = 'A aula completa, com texto e teste, está grátis em magystic ponto com, barra curso.'
    if prox:
        fim += f" Na próxima aula: Aula {prox['num']}, {prox['titulo']}."
    padrao = {'abertura': f"Aula {a['num']} do curso Minha Marca Registrada. {a['titulo']}.",
              'pontos': a['pontos'][:3], 'fechamento': fim}
    if SEM_VOZ or not modelo:
        return padrao
    pedido = f"""Você escreve a narração de um vídeo curto (Reels de uns 60 segundos) da Aula {a['num']} do curso Minha Marca Registrada, um curso grátis da MAGYSTIC que ensina empreendedores a registrar a própria marca no INPI.
Regras:
- Use SOMENTE as informações da aula abaixo. Não invente números, prazos, valores, exemplos reais ou artigos de lei que não estejam nela.
- Português do Brasil, frases curtas, tom animado e claro, falando direto com o empreendedor ("você").
- Devolva JSON com:
  "abertura": 1 ou 2 frases, até 30 palavras, começando exatamente com "Aula {a['num']}." e apresentando o tema de um jeito que prenda a atenção.
  "pontos": lista com exatamente 3 textos, um para cada ponto-chave abaixo, na mesma ordem, cada um com 20 a 40 palavras.

AULA {a['num']}: {a['titulo']}
Resumo: {a['resumo']}
Pontos-chave:
1. {a['pontos'][0]}
2. {a['pontos'][1]}
3. {a['pontos'][2]}
Texto da aula:
{a['texto']}"""
    corpo = {'contents': [{'role': 'user', 'parts': [{'text': pedido}]}],
             'generationConfig': {'responseMimeType': 'application/json', 'temperature': 0.5}}
    try:
        r = gemini(modelo, corpo)
        t = ''.join(p.get('text', '') for p in r['candidates'][0]['content']['parts'])
        j = json.loads(t[t.index('{'):t.rindex('}') + 1])
        pts = [str(x).strip() for x in j.get('pontos', [])][:3]
        if len(pts) == 3 and str(j.get('abertura', '')).startswith(f"Aula {a['num']}"):
            return {'abertura': j['abertura'].strip(), 'pontos': pts, 'fechamento': fim}
        print('  roteiro fora do formato, usando o padrão')
    except Exception as e:
        print('  roteiro padrão:', e)
    return padrao

def falar(modelo, texto, arq):
    corpo = {'contents': [{'parts': [{'text': 'Diga em português do Brasil, com voz animada, clara e acolhedora, '
                                              'como um professor num vídeo curto: ' + texto}]}],
             'generationConfig': {'responseModalities': ['AUDIO'],
                                  'speechConfig': {'voiceConfig': {'prebuiltVoiceConfig': {'voiceName': VOZ}}}}}
    r = gemini(modelo, corpo)
    parte = next(p['inlineData'] for p in r['candidates'][0]['content']['parts'] if 'inlineData' in p)
    pcm = base64.b64decode(parte['data'])
    m = re.search(r'rate=(\d+)', parte.get('mimeType', ''))
    taxa = int(m.group(1)) if m else 24000
    with wave.open(arq, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(taxa); w.writeframes(pcm)
    return len(pcm) / 2 / taxa

def falar_tudo(modelo, falas, pasta):
    """Uma só chamada de voz para o vídeo inteiro; corta nas pausas entre as partes."""
    roteiro_txt = '\n\n'.join(falas)
    corpo = {'contents': [{'parts': [{'text': 'Diga em português do Brasil, com voz animada, clara e acolhedora, '
                                              'como um professor num vídeo curto. Faça uma pausa curta entre os parágrafos.\n\n' + roteiro_txt}]}],
             'generationConfig': {'responseModalities': ['AUDIO'],
                                  'speechConfig': {'voiceConfig': {'prebuiltVoiceConfig': {'voiceName': VOZ}}}}}
    r = gemini(modelo, corpo)
    parte = next(p['inlineData'] for p in r['candidates'][0]['content']['parts'] if 'inlineData' in p)
    pcm = base64.b64decode(parte['data'])
    m = re.search(r'rate=(\d+)', parte.get('mimeType', ''))
    taxa = int(m.group(1)) if m else 24000
    amostras = struct.unpack('<%dh' % (len(pcm) // 2), pcm[:len(pcm) // 2 * 2])
    total = len(amostras)
    # energia em janelas de 20 ms
    jan = int(taxa * 0.02); quiet = []
    for i in range(0, total - jan, jan):
        seg = amostras[i:i + jan]
        quiet.append(max(abs(x) for x in seg) < 900)
    pausas = []  # (inicio, fim) em amostras, só pausas >= 240 ms
    i = 0
    while i < len(quiet):
        if quiet[i]:
            j = i
            while j < len(quiet) and quiet[j]:
                j += 1
            if (j - i) * 0.02 >= 0.24 and i > 0 and j < len(quiet):
                pausas.append((i * jan, j * jan))
            i = j
        else:
            i += 1
    tam = [len(f) for f in falas]
    cortes, acum = [], 0
    for k in range(len(falas) - 1):
        acum += tam[k]
        alvo = total * acum / sum(tam)
        cand = [p for p in pausas if all(abs((p[0] + p[1]) / 2 - c) > taxa * 0.8 for c in cortes)]
        if cand:
            p = min(cand, key=lambda p: abs((p[0] + p[1]) / 2 - alvo))
            meio = (p[0] + p[1]) // 2 if abs((p[0] + p[1]) / 2 - alvo) < taxa * 3 else int(alvo)
        else:
            meio = int(alvo)
        cortes.append(meio)
    cortes = sorted(cortes)
    lim = [0] + cortes + [total]
    saida = []
    for k in range(len(falas)):
        a, b = lim[k], lim[k + 1]
        arq = os.path.join(pasta, f'fala-{k}.wav')
        with wave.open(arq, 'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(taxa)
            w.writeframes(struct.pack('<%dh' % (b - a), *amostras[a:b]))
        saida.append((arq, (b - a) / taxa))
    return saida

def silencio(segundos, arq, taxa=24000):
    with wave.open(arq, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(taxa); w.writeframes(b'\x00\x00' * int(segundos * taxa))
    return segundos

def juntar_wavs(arqs, pausa, destino):
    taxa = None; dados = b''
    for i, a in enumerate(arqs):
        with wave.open(a) as w:
            taxa = taxa or w.getframerate()
            if w.getframerate() != taxa:
                raise RuntimeError('taxas de áudio diferentes')
            dados += w.readframes(w.getnframes())
        dados += b'\x00\x00' * int(pausa * taxa)
    dados = b'\x00\x00' * int(0.3 * taxa) + dados + b'\x00\x00' * int(0.6 * taxa)
    with wave.open(destino, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(taxa); w.writeframes(dados)

# ---------------------------------------------------------------- desenho

_cache = {}
def fonte(nome, tam, peso=400):
    k = (nome, tam, peso)
    if k in _cache:
        return _cache[k]
    arq = {'serif': 'Fraunces.ttf', 'sans': 'Jost.ttf'}[nome]
    f = ImageFont.truetype(os.path.join(FONTES, arq), tam)
    try:
        vals = []
        for ax in f.get_variation_axes():
            n = str(ax.get('name', '')).lower()
            if 'weight' in n: vals.append(peso)
            elif 'optical' in n: vals.append(max(ax['minimum'], min(ax['maximum'], 144 if tam > 120 else tam)))
            elif 'soft' in n: vals.append(0)
            elif 'wonk' in n: vals.append(0)
            else: vals.append(ax['default'])
        f.set_variation_by_axes(vals)
    except Exception:
        pass
    _cache[k] = f
    return f

def quebrar(texto, f, largura):
    linhas, atual = [], ''
    for p in texto.split():
        t = (atual + ' ' + p).strip()
        if f.getlength(t) <= largura or not atual:
            atual = t
        else:
            linhas.append(atual); atual = p
    if atual:
        linhas.append(atual)
    return linhas

def bloco_texto(texto, f, largura, cor, entre=1.22, alinhar='esq'):
    linhas = quebrar(texto, f, largura)
    asc, desc = f.getmetrics()
    alt_l = int((asc + desc) * entre)
    img = Image.new('RGBA', (largura, alt_l * len(linhas) + desc), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i, l in enumerate(linhas):
        x = 0 if alinhar == 'esq' else (largura - f.getlength(l)) / 2
        d.text((x, i * alt_l), l, font=f, fill=cor)
    return img

def pilula(texto, f, fundo, cor, px=30, py=14):
    larg = int(f.getlength(texto)) + 2 * px
    asc, desc = f.getmetrics()
    alt = asc + desc + 2 * py
    img = Image.new('RGBA', (larg, alt), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, larg - 1, alt - 1), radius=alt // 2, fill=fundo)
    d.text((px, py), texto, font=f, fill=cor)
    return img

def espacado(texto, f, cor, esp=6):
    larg = int(sum(f.getlength(c) + esp for c in texto))
    asc, desc = f.getmetrics()
    img = Image.new('RGBA', (larg, asc + desc), (0, 0, 0, 0))
    d = ImageDraw.Draw(img); x = 0
    for c in texto:
        d.text((x, 0), c, font=f, fill=cor); x += f.getlength(c) + esp
    return img

def cartao(conteudo, largura, pad=56, cor=SUPER, borda=OURO):
    alt = conteudo.height + 2 * pad
    img = Image.new('RGBA', (largura, alt), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, largura - 1, alt - 1), radius=44, fill=cor + (240,), outline=borda + (110,), width=3)
    img.alpha_composite(conteudo, (pad, pad))
    return img

def fundo_base():
    alt = H + 400
    img = Image.new('RGB', (W, alt), FUNDO)
    d = ImageDraw.Draw(img)
    for y in range(alt):
        k = y / alt
        d.line([(0, y), (W, y)], fill=(int(21 + 12 * k), int(13 + 6 * k), int(31 + 20 * k)))
    brilho = Image.new('RGBA', (W, alt), (0, 0, 0, 0))
    db = ImageDraw.Draw(brilho)
    db.ellipse((W - 520, 80, W + 380, 980), fill=OURO + (60,))
    db.ellipse((-420, alt - 1100, 480, alt - 200), fill=VERDE + (38,))
    db.ellipse((200, 900, 1000, 1700), fill=(120, 80, 180, 34))
    brilho = brilho.filter(ImageFilter.GaussianBlur(160))
    img = img.convert('RGBA'); img.alpha_composite(brilho)
    return img.convert('RGB')

def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3

def colar(quadro, el, x, y, opac=1.0):
    if opac <= 0.01:
        return
    if opac < 0.99:
        el = el.copy()
        el.putalpha(el.getchannel('A').point(lambda v: int(v * opac)))
    quadro.paste(el, (int(x), int(y)), el)

def entrar(quadro, el, x, y, t, atraso=0.0, dur=0.55, desloc=60, opac_cena=1.0):
    k = ease((t - atraso) / dur)
    colar(quadro, el, x, y + (1 - k) * desloc, k * opac_cena)

def blocos_legenda(texto, max_c=34):
    palavras, blocos, atual = texto.split(), [], ''
    for p in palavras:
        t = (atual + ' ' + p).strip()
        if len(t) > max_c and atual:
            blocos.append(atual); atual = p
        else:
            atual = t
    if atual:
        blocos.append(atual)
    pares = [' '.join(blocos[i:i + 2]) for i in range(0, len(blocos), 2)]
    return pares

# ---------------------------------------------------------------- vídeo

def montar_video(a, rot, duracoes, audio, destino, capa_arq=None):
    fundo = fundo_base()
    logo = Image.open(os.path.join(AQUI, 'logo.png')).convert('RGBA')
    logo.thumbnail((76, 76))
    marca = espacado('MAGYSTIC', fonte('serif', 36, 600), TINTA, 7)
    selo_topo = pilula('MINHA MARCA REGISTRADA', fonte('sans', 26, 500), VERDE + (40,), VERDE, 22, 10)

    L = W - 160
    cenas = []
    # abertura
    els = {
        'pill': pilula(f"MÓDULO {a['modulo']} DE 10  ·  AULA {a['num']} DE 99", fonte('sans', 28, 500), OURO + (38,), OURO),
        'aula': espacado('AULA', fonte('sans', 44, 500), OURO, 14),
        'num': bloco_texto(str(a['num']), fonte('serif', 330, 600), L, OURO, 1.0),
        'tit': bloco_texto(a['titulo'], fonte('serif', 78, 600), L, TINTA, 1.15),
        'res': bloco_texto(a['resumo'], fonte('sans', 44, 400), L, DIM, 1.3),
    }
    cenas.append(('abertura', els, rot['abertura']))
    for i, p in enumerate(a['pontos'][:3]):
        txt = bloco_texto(p, fonte('serif', 64, 500), L - 112, TINTA, 1.25)
        els = {'rot': espacado(f'PONTO {i + 1} DE 3', fonte('sans', 34, 500), OURO, 8),
               'card': cartao(txt, L), 'n': i}
        cenas.append(('ponto', els, rot['pontos'][i]))
    prox = a.get('proxima')
    els = {
        'tit': bloco_texto('A aula completa é grátis', fonte('serif', 84, 600), L, TINTA, 1.12, 'centro'),
        'sub': bloco_texto('Texto, resumo e teste rápido em', fonte('sans', 44, 400), L, DIM, 1.3, 'centro'),
        'url': pilula('magystic.com/curso', fonte('sans', 60, 600), VERDE + (255,), VERDE_TINTA, 50, 24),
        'prox': bloco_texto(f"Próxima: Aula {prox['num']} · {prox['titulo']}" if prox else 'Você chegou ao fim do curso!',
                            fonte('sans', 42, 500), L, OURO, 1.3, 'centro'),
        'dia': bloco_texto('Um módulo novo toda segunda-feira', fonte('sans', 36, 400), L, APAGADO, 1.3, 'centro'),
    }
    cenas.append(('fim', els, rot['fechamento']))

    # linha do tempo (o áudio começa com 0,3 s de silêncio)
    inicios, t = [], 0.3
    for d in duracoes:
        inicios.append(t); t += d + PAUSA
    total = t + 0.6
    fins = inicios[1:] + [total]
    fins[0] = inicios[1]

    # legendas: blocos distribuídos pela duração de cada fala
    legendas = []
    for i, (_, _, fala) in enumerate(cenas):
        blocos = blocos_legenda(fala.replace('magystic ponto com, barra curso', 'magystic.com/curso'))
        pesos = [len(b) for b in blocos]; soma = sum(pesos) or 1
        t0 = inicios[i]
        for b, pz in zip(blocos, pesos):
            dur = duracoes[i] * pz / soma
            legendas.append((t0, t0 + dur, b)); t0 += dur
    f_leg = fonte('sans', 46, 500)
    cache_leg = {}

    def legenda_img(txt):
        if txt not in cache_leg:
            linhas = quebrar(txt, f_leg, W - 220)
            asc, desc = f_leg.getmetrics(); al = int((asc + desc) * 1.25)
            alt = al * len(linhas) + 44
            img = Image.new('RGBA', (W - 140, alt), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            d.rounded_rectangle((0, 0, W - 141, alt - 1), radius=30, fill=(10, 6, 16, 200))
            for k, l in enumerate(linhas):
                d.text(((W - 140 - f_leg.getlength(l)) / 2, 18 + k * al), l, font=f_leg, fill=TINTA)
            cache_leg[txt] = img
        return cache_leg[txt]

    n_quadros = int(total * FPS)
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
           '-i', '-', '-i', audio, '-c:v', 'libx264', '-preset', 'medium', '-crf', '24', '-pix_fmt', 'yuv420p',
           '-c:a', 'aac', '-b:a', '128k', '-ar', '44100', '-shortest', '-movflags', '+faststart', destino]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    capa_bytes = Image.open(capa_arq).convert('RGB').resize((W, H)).tobytes() if capa_arq and os.path.exists(capa_arq) else None
    for q in range(n_quadros):
        tg = q / FPS
        if capa_bytes and tg < 0.5:  # primeiro quadro = capa do Reel
            proc.stdin.write(capa_bytes); continue
        off = int(200 + 180 * __import__('math').sin(tg / 9.0))
        quadro = fundo.crop((0, off, W, off + H)).copy()
        # topo fixo
        quadro.paste(logo, (80, 92), logo)
        quadro.paste(marca, (172, 106), marca)
        quadro.paste(selo_topo, (W - 80 - selo_topo.width, 104), selo_topo)
        # cena atual
        i = max(k for k in range(len(cenas)) if tg >= (inicios[k] if k else 0))
        ini, fim = (0 if i == 0 else inicios[i]), fins[i]
        t = tg - ini
        sair = 1.0 if i == len(cenas) - 1 else 1 - ease((tg - (fim - 0.28)) / 0.28)
        tipo, els, _ = cenas[i]
        if tipo == 'abertura':
            entrar(quadro, els['pill'], 80, 330, t, 0.0, opac_cena=sair)
            entrar(quadro, els['aula'], 86, 470, t, 0.12, opac_cena=sair)
            entrar(quadro, els['num'], 72, 520, t, 0.22, desloc=90, opac_cena=sair)
            y = 520 + els['num'].height + 10
            entrar(quadro, els['tit'], 80, y, t, 0.45, opac_cena=sair)
            entrar(quadro, els['res'], 80, y + els['tit'].height + 34, t, 0.7, opac_cena=sair)
        elif tipo == 'ponto':
            entrar(quadro, els['rot'], 80, 400, t, 0.0, opac_cena=sair)
            card = els['card']
            yc = max(500, 900 - card.height // 2)
            entrar(quadro, card, 80, yc, t, 0.15, dur=0.6, desloc=110, opac_cena=sair)
            # marcadores dos 3 pontos
            for k in range(3):
                cor = OURO if k <= els['n'] else (70, 58, 92)
                d = ImageDraw.Draw(quadro)
                d.rounded_rectangle((80 + k * 70, 470, 80 + k * 70 + 52, 478), radius=4, fill=cor)
        else:
            y = 420
            for nome, atraso in (('tit', 0.0), ('sub', 0.2), ('url', 0.35), ('prox', 0.6), ('dia', 0.75)):
                el = els[nome]
                entrar(quadro, el, (W - el.width) // 2, y, t, atraso)
                y += el.height + (60 if nome in ('url', 'tit') else 36)
        # legenda
        for (a0, a1, txt) in (legendas if os.environ.get('LEGENDAS') == '1' else []):
            if a0 <= tg < a1:
                img = legenda_img(txt)
                quadro.paste(img, (70, 1470), img)
                break
        # barra de progresso
        d = ImageDraw.Draw(quadro)
        d.rounded_rectangle((80, 1800, W - 80, 1808), radius=4, fill=(60, 48, 80))
        d.rounded_rectangle((80, 1800, 80 + int((W - 160) * tg / total), 1808), radius=4, fill=OURO)
        proc.stdin.write(quadro.tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError('ffmpeg falhou')
    return total

# ---------------------------------------------------------------- fluxo

def enviar(num, arq, tipo='video', ctype='video/mp4'):
    url = os.environ['ACTIONS_ID_TOKEN_REQUEST_URL'] + '&audience=magystic.com'
    tok = json.loads(http(url, headers={'authorization': 'bearer ' + os.environ['ACTIONS_ID_TOKEN_REQUEST_TOKEN']}))['value']
    with open(arq, 'rb') as f:
        dados = f.read()
    r = http(f'{SITE}/api/curso/{tipo}/{num}', dados, {'authorization': 'Bearer ' + tok, 'content-type': ctype}, method='POST')
    print('  enviado:', r.decode())

def gerar(num, m_txt, m_voz):
    a = json.loads(http(f'{SITE}/api/curso/aula/{num}'))
    print(f"Aula {num}: {a['titulo']}")
    pasta = os.path.join(SAIDA, f'aula-{num}'); os.makedirs(pasta, exist_ok=True)
    rot = roteiro(a, m_txt)
    falas = [rot['abertura']] + rot['pontos'] + [rot['fechamento']]
    arqs, duracoes = [], []
    if SEM_VOZ:
        for i, fala in enumerate(falas):
            arq = os.path.join(pasta, f'fala-{i}.wav')
            arqs.append(arq); duracoes.append(silencio(max(2.5, len(fala.split()) / 2.6), arq))
    else:
        for arq, d in falar_tudo(m_voz, falas, pasta):
            arqs.append(arq); duracoes.append(d)
    print('  falas:', ', '.join(f'{d:.1f}s' for d in duracoes))
    audio = os.path.join(pasta, 'narracao.wav')
    juntar_wavs(arqs, PAUSA, audio)
    destino = os.path.join(SAIDA, f'aula-{num}.mp4')
    capa_arq = fazer_capa(a)
    total = montar_video(a, rot, duracoes, audio, destino, capa_arq)
    with open(os.path.join(pasta, 'roteiro.json'), 'w', encoding='utf-8') as f:
        json.dump(rot, f, ensure_ascii=False, indent=2)
    print(f'  vídeo: {destino} ({total:.1f}s, {os.path.getsize(destino) / 1e6:.1f} MB)')
    if not NAO_ENVIAR:
        enviar(num, destino)

def fazer_capa(a):
    arq = os.path.join(SAIDA, f"capa-aula-{a['num']}.jpg")
    capa(a, arq)
    print('  capa:', arq)
    if not NAO_ENVIAR:
        try:
            enviar(a['num'], arq, 'capa', 'image/jpeg')
        except Exception as e:
            print('  capa não enviada:', e)
    return arq

def main():
    os.makedirs(SAIDA, exist_ok=True)
    if len(sys.argv) > 1:
        nums = [int(x) for x in sys.argv[1:]]
    elif os.environ.get('AULAS', '').strip():
        nums = [int(x) for x in re.split(r'[,\s]+', os.environ['AULAS'].strip()) if x]
    else:
        nums = json.loads(http(f'{SITE}/api/curso/pendentes'))['pendentes'][:MAX_VIDEOS]
    if SO_CAPA:
        if not nums or not os.environ.get('AULAS', '').strip():
            nums = list(range(100))
        falhas = 0
        for n in nums:
            try:
                fazer_capa(json.loads(http(f'{SITE}/api/curso/aula/{n}')))
            except Exception as e:
                falhas += 1; print(f'ERRO na capa {n}: {e}')
        if falhas:
            sys.exit(1)
        return
    if not nums:
        print('Nenhuma aula pendente.'); return
    m_txt = m_voz = None
    if not SEM_VOZ:
        m_txt, m_voz = escolher_modelos()
        print('Modelos:', m_txt, m_voz)
    falhas = 0
    for n in nums:
        try:
            gerar(n, m_txt, m_voz)
        except CotaDiaria:
            falhas += 1
            print(f'Cota diária do Gemini acabou na aula {n}. As próximas saem na execução de amanhã.')
            break
        except Exception as e:
            falhas += 1
            print(f'ERRO na aula {n}: {e}')
    if falhas:
        sys.exit(1)


# ---------------------------------------------------------------- capa do Reel

def capa(a, destino):
    """Capa 1080x1920 do Reel. O essencial fica no miolo 1080x1350 (recorte do feed do Instagram)."""
    img = fundo_base().crop((0, 200, W, 200 + H)).convert('RGBA')
    L = W - 180
    logo = Image.open(os.path.join(AQUI, 'logo.png')).convert('RGBA')
    logo.thumbnail((92, 92))
    marca = espacado('MAGYSTIC', fonte('serif', 40, 600), TINTA, 8)
    # topo do miolo (y ≈ 300)
    y = 330
    larg = logo.width + 22 + marca.width
    x0 = (W - larg) // 2
    colar(img, logo, x0, y)
    colar(img, marca, x0 + logo.width + 22, y + (logo.height - marca.height) // 2)
    y += logo.height + 46
    selo = pilula('CURSO MINHA MARCA REGISTRADA', fonte('sans', 28, 500), VERDE + (46,), VERDE, 26, 12)
    colar(img, selo, (W - selo.width) // 2, y)
    y += selo.height + 50
    rot = espacado('AULA', fonte('sans', 46, 500), OURO, 16)
    colar(img, rot, (W - rot.width) // 2, y)
    y += rot.height + 4
    num = bloco_texto(str(a['num']), fonte('serif', 300, 600), L, OURO, 0.95, 'centro')
    colar(img, num, (W - L) // 2, y)
    y += num.height - 70
    tam = 70
    tit = bloco_texto(a['titulo'], fonte('serif', tam, 600), L, TINTA, 1.12, 'centro')
    while tit.height > 260 and tam > 50:
        tam -= 4; tit = bloco_texto(a['titulo'], fonte('serif', tam, 600), L, TINTA, 1.12, 'centro')
    colar(img, tit, (W - L) // 2, y)
    y += tit.height + 40
    frase = (a.get('pontos') or [a.get('resumo', '')])[0]
    ft = bloco_texto(frase, fonte('sans', 40, 400), L - 100, DIM, 1.32, 'centro')
    card = cartao(ft, L, pad=50)
    if y + card.height < 1640:
        colar(img, card, (W - L) // 2, y)
    # rodapé (fora do recorte do feed, aparece no Reel aberto)
    url = pilula('Grátis em magystic.com/curso', fonte('sans', 44, 600), VERDE + (255,), VERDE_TINTA, 40, 20)
    colar(img, url, (W - url.width) // 2, 1700)
    img.convert('RGB').save(destino, 'JPEG', quality=90, optimize=True, progressive=True)
    return destino

if __name__ == '__main__':
    main()
