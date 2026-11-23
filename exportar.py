# Exporta aulas, vídeos e bônus para montar o curso na Hotmart
import os, json, subprocess, urllib.request
AQUI = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(AQUI, 'export'); os.makedirs(os.path.join(OUT, 'videos'), exist_ok=True)
UA = {'user-agent': 'Mozilla/5.0 magystic-export'}
def get(u, t=120):
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=t) as r:
        return r.read()
aulas = []
for n in range(100):
    a = json.loads(get(f'https://magystic.com/api/curso/aula/{n}'))
    aulas.append(a)
    v = a.get('video')
    if v:
        arq = os.path.join(OUT, 'videos', f'aula-{n}.mp4')
        open(arq, 'wb').write(get(v.split('?')[0] + '?x=export', 300))
        print(n, 'video', os.path.getsize(arq))
json.dump(aulas, open(os.path.join(OUT, 'aulas.json'), 'w', encoding='utf-8'), ensure_ascii=False)
subprocess.run(['python', os.path.join(AQUI, 'bonus.py')], check=True)
print('ok', len(aulas))
