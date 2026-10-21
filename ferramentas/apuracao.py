#!/usr/bin/env python3
"""Leitura ao vivo da apuração do 2º turno de 2026 (eleição 6258) pela mesma régua da página, com log em CSV.

Lê os JSON oficiais do Divulga/TSE: <uf>-c0001-e006258-u.json (placar) e br-e006258-ab.json (andamento por UF).
Régua: margem final implícita = parcial − k × efeito de composição do 2º turno de 2022 na mesma fatia de seções (k = 1 central).
Referências em dados/*.json, geradas por ferramentas/referencia.py.

Uso:  python3 ferramentas/apuracao.py                 # uma leitura
      python3 ferramentas/apuracao.py --loop 120      # a cada 2 min, com log em dados/log_2t_2026.csv (começar às 17h de 25/10)
      python3 ferramentas/apuracao.py --probe         # testa se os arquivos existem no TSE
      python3 ferramentas/apuracao.py --demo          # régua com dados fictícios
"""
import argparse, csv, datetime, json, math, os, sys, time, urllib.error, urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from referencia import prior_pesquisas
BASE = "https://resultados.tse.jus.br/oficial"
UA = {"User-Agent": "Mozilla/5.0"}
LULA, FLAVIO = "13", "22"
K = 1.0
UFS_PADRAO = "sp,mg,rj,ba,pe"
NE = {"al", "ba", "ce", "ma", "pb", "pe", "pi", "rn", "se"}

def ler_json(nome):
    with open(os.path.join(RAIZ, "dados", nome)) as f: return json.load(f)
CURVA = ler_json("curva_2t_2022.json"); U22 = ler_json("urna_2t_2022_uf.json"); U26 = ler_json("urna_1t_2026_uf.json"); D22 = ler_json("detalhe_2t_2022_uf.json")
PONTOS = [(p["pst"], p["efeito"]) for p in CURVA["pontos"]]
HORAS = {int(round(p["pst"])): p["hora"] for p in CURVA["pontos"]}
FINAL22 = CURVA["final"]["margem"]; VIRADA = CURVA["virada"]
PRIOR = prior_pesquisas(ler_json("pesquisas_2t.json"))

def phi(z): return 0.5 * (1 + math.erf(z / math.sqrt(2)))
def posterior(imp, ef, fim):
    """Combina o prior das pesquisas N(mu, sigma0) com a implícita da régua N(imp, sr), sr = 30% da ordem de chegada que falta + piso 0,15."""
    sr = 0.01 if fim else 0.3 * abs(ef) + 0.15
    w0, wr = 1 / PRIOR["sigma0"] ** 2, 1 / sr ** 2
    mu = (PRIOR["mu"] * w0 + imp * wr) / (w0 + wr); sd = math.sqrt(1 / (w0 + wr)); pL = 100 * phi(mu / sd)
    return {"pL": pL, "pF": 100 - pL, "sr": sr, "peso": 100 * wr / (w0 + wr)}

def num(s):
    if s is None: return None
    if isinstance(s, (int, float)): return float(s)
    s = str(s).strip()
    if "," in s: s = s.replace(".", "").replace(",", ".")
    try: return float(s)
    except ValueError: return None

def get(url, quiet=False):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r: return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if not quiet: print(f"  [{e.code}] {url}")
    except Exception as e:
        if not quiet: print(f"  [erro {e}] {url}")
    return None

def efeito(pst):
    if pst <= PONTOS[0][0]: return PONTOS[0][1]
    for (p0, e0), (p1, e1) in zip(PONTOS, PONTOS[1:]):
        if p0 <= pst <= p1: return e0 + (e1 - e0) * (pst - p0) / (p1 - p0) if p1 > p0 else e1
    return 0.0

def hora_ref(pst):
    best = min(HORAS, key=lambda p: abs(p - pst)); return f"em 2022, {best:g}% foi às {HORAS[best].replace(':', 'h')}"

def urls(ele, uf="br"):
    d = f"{BASE}/ele2026/{ele}/dados"; e6 = f"{ele:06d}"
    return {"ab": f"{d}/br/br-e{e6}-ab.json", "u": f"{d}/{uf}/{uf}-c0001-e{e6}-u.json"}

def parse_ab(j):
    out = {}
    for a in j.get("abr", []):
        s, e = a.get("s", {}), a.get("e", {})
        out[str(a["cdabr"]).lower()] = {"pst": num(s.get("pstn") or s.get("pst")) or 0.0, "pa": num(e.get("pan") or e.get("pa"))}
    return out

def parse_u(j):
    votos = {}
    for carg in j.get("carg", []):
        for agr in carg.get("agr", []):
            for par in agr.get("par", []):
                for c in par.get("cand", []): votos[str(c.get("n"))] = votos.get(str(c.get("n")), 0) + int(num(c.get("vap")) or 0)
    s, e, v = j.get("s", {}), j.get("e", {}), j.get("v", {})
    tot = {"pst": num(s.get("pstn") or s.get("pst")), "pa": num(e.get("pan") or e.get("pa")), "tv": num(v.get("tv")), "vb": num(v.get("vb")), "vn": num(v.get("vn")),
           "st": int(num(s.get("st")) or 0), "ts": int(num(s.get("ts")) or 0), "te": int(num(e.get("te")) or 0)}
    return votos, tot

def shares(votos):
    L, F = votos.get(LULA, 0), votos.get(FLAVIO, 0); t = (L + F) or 1
    return 100 * L / t, 100 * F / t, L + F

def dois(uf):
    r = U26.get(uf); return 100 * (r["lula"] - r["flavio"]) / (r["lula"] + r["flavio"]) if r else None

def regua(pst, L, F, bn, abst, por_uf, ab, log=None, ts=None, fim=False):
    m = L - F; ef = efeito(pst); imp = m - K * ef; post = posterior(imp, ef, fim)
    print(f"\n=== {ts or datetime.datetime.now().strftime('%H:%M:%S')} — {pst:.2f}% das seções ({hora_ref(pst)}) ===")
    print(f"Válidos: Lula {L:.2f}  Flávio {F:.2f}  margem (L−F) {m:+.2f}" + (f"  brancos+nulos {bn:.2f}% (2022: {D22['br']['bn']}; 1ºT: {U26['br']['bn']})" if bn is not None else "")
          + (f"  abstenção {abst:.2f}% (2022: {D22['br']['abst']}; 1ºT: {U26['br']['abst']})" if abst is not None else ""))
    print(f"Ordem de chegada de 2022 nesta fatia: {ef:+.2f}. Implícita k=1: {imp:+.2f}  |  k=0,5: {m - 0.5*ef:+.2f}  |  parcial de 2022 nesta altura: {FINAL22 + ef:+.2f}")
    print(f"Se o final for Lula +2 / empate / Flávio +2, a parcial agora seria {2 + K*ef:+.1f} / {K*ef:+.1f} / {-2 + K*ef:+.1f}")
    print(f"Chance: Flávio {post['pF']:.0f}% × Lula {post['pL']:.0f}%  (pelas pesquisas, antes da urna: Flávio {PRIOR['p_flavio']:.0f}%; a apuração já pesa {post['peso']:.0f}%, incerteza da régua ±{post['sr']:.2f})")
    inst = sorted(PRIOR["ultimas"], key=lambda r: abs(imp - r["bruta"]))
    print("Institutos (distância implícita − pesquisa, do mais perto ao mais longe): " + "  ".join(f"{r['inst']} {r['bruta']:+.1f} ({imp - r['bruta']:+.1f})" for r in inst))
    if pst < 15: print("Leitura: cedo demais (até 15% a ordem de chegada domina).")
    else:
        q = "Lula tende a vencer" if imp > 1 else ("Flávio tende a vencer" if imp < -1 else "empate técnico pela régua (entre −1 e +1 o método não separa)")
        if m < 0 < imp - 1: q += f"; Flávio na frente agora, mas em 2022 a virada veio aos {VIRADA['pst']}% ({VIRADA['hora'].replace(':', 'h')})"
        print(f"Leitura (k=1): {q}.")
    print("Estados (margem L−F | % seções da UF | 2022 | 1º turno entre os dois):")
    linhas = {}
    for uf, d in por_uf.items():
        l, f, _ = shares(d); mu = l - f; p = (ab.get(uf) or {}).get("pst")
        print(f"   {uf.upper()}: {mu:+.2f} ({l:.1f} × {f:.1f}) | {f'{p:.0f}' if p is not None else '?'}% | 2022 {U22[uf]['margem']:+.1f} | 1ºT {dois(uf):+.1f}")
        linhas[uf] = (mu, p)
    ufs = [(u, v["pa"], v["pst"]) for u, v in ab.items() if u not in ("br", "zz") and v.get("pa") is not None and v["pst"] >= 5]
    if ufs:
        ufs.sort(key=lambda x: x[1] - (U26.get(x[0], {}).get("abst") or 0))
        print("Abstenção × 1º turno (variação; mais caiu → mais subiu): " + "  ".join(f"{u.upper()} {pa:.1f} ({pa - U26[u]['abst']:+.1f}, {p:.0f}%)" for u, pa, p in ufs))
        ne = [x for x in ufs if x[0] in NE]
        if ne: print(f"   Nordeste: {sum(x[1] for x in ne)/len(ne):.1f}% em {len(ne)} UFs (1ºT {sum(U26[x[0]]['abst'] for x in ne)/len(ne):.1f}; 2022 {sum(D22[x[0]]['abst'] for x in ne)/len(ne):.1f})")
    if log is not None:
        log.writerow([ts or datetime.datetime.now().isoformat(timespec="seconds"), f"{pst:.2f}", f"{L:.2f}", f"{F:.2f}", f"{m:+.2f}", f"{imp:+.2f}", f"{post['pF']:.1f}",
                      "" if bn is None else f"{bn:.2f}", "" if abst is None else f"{abst:.2f}"]
                     + [f"{linhas[u][0]:+.2f}" if u in linhas else "" for u in UFS_PADRAO.split(",")]
                     + [f"{linhas[u][1]}" if u in linhas and linhas[u][1] is not None else "" for u in UFS_PADRAO.split(",")])

def leitura(args, log=None):
    U = urls(args.ele)
    ab_j = get(U["ab"], quiet=True); ab = parse_ab(ab_j) if ab_j else {}
    u_j = get(U["u"], quiet=True)
    if not u_j: print(f"{datetime.datetime.now():%H:%M:%S}: arquivo nacional -u inexistente; -ab: {ab.get('br', {}).get('pst', 0):.2f}% das seções."); return False
    votos, tot = parse_u(u_j); L, F, soma = shares(votos)
    pst = tot["pst"] if tot["pst"] is not None else ab.get("br", {}).get("pst", 0.0)
    if not tot["tv"] or soma == 0:
        print(f"{datetime.datetime.now():%H:%M:%S}: ainda sem votos totalizados (arquivo de {u_j.get('dg')} {u_j.get('hg')}; seções {tot['st']}/{tot['ts']}; eleitorado {tot['te']:,}). "
              f"Chance pelas pesquisas: Flávio {PRIOR['p_flavio']:.0f}% ({PRIOR['n']} institutos, corrigida {PRIOR['mu']:+.1f} ± {PRIOR['sigma0']})."); return False
    bn = 100 * ((tot["vb"] or 0) + (tot["vn"] or 0)) / tot["tv"] if tot["tv"] else None
    por_uf = {}
    for uf in args.ufs.split(","):
        uf = uf.strip().lower(); j = get(urls(args.ele, uf)["u"], quiet=True)
        if not j: continue
        v_uf, t_uf = parse_u(j)
        if sum(v_uf.values()) > 0: por_uf[uf] = v_uf
        ab.setdefault(uf, {}); ab[uf].update({k: t_uf[k] for k in ("pst", "pa") if t_uf[k] is not None})
    regua(pst, L, F, bn, tot["pa"], por_uf, ab, log=log, ts=f"{u_j.get('dg')} {u_j.get('hg')} (hora do arquivo)", fim=(u_j.get("and") == "f" or pst >= 99.99))
    return True

def demo():
    print("MODO DEMO — dados fictícios: final hipotético Lula +0,5 com a ordem de chegada de 2022 (k = 1)")
    for pst in (5, 20, 50, 67, 90):
        m = 0.5 + efeito(pst); L, F = 50 + m / 2, 50 - m / 2
        por_uf = {"sp": {LULA: 44000, FLAVIO: 56000}, "mg": {LULA: 49500, FLAVIO: 50500}, "ba": {LULA: 70000, FLAVIO: 30000}}
        ab = {"br": {"pst": pst, "pa": 20.9}, "sp": {"pst": min(99, pst * 1.25), "pa": 21.0}, "mg": {"pst": min(99, pst * 1.1), "pa": 21.9}, "ba": {"pst": pst * 0.65, "pa": 19.1}, "pe": {"pst": pst * 0.7, "pa": 17.0}, "rj": {"pst": min(99, pst * 1.15), "pa": 22.6}}
        regua(pst, L, F, 4.5, 20.9, por_uf, ab, ts=f"DEMO {pst}%")

def probe(args):
    lst = dict(urls(args.ele)); lst["u_sp"] = urls(args.ele, "sp")["u"]
    for k, u in lst.items():
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=20) as r: j = json.loads(r.read()); print(f"  200 {k}: gerado {j.get('dg')} {j.get('hg')} · {u}")
        except urllib.error.HTTPError as e: print(f"  {e.code} {k}: {u}")
        except Exception as e: print(f"  erro {k}: {u} ({e})")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ele", type=int, default=6258); ap.add_argument("--loop", type=int, default=0, help="segundos entre leituras (0 = uma só)")
    ap.add_argument("--log", default=os.path.join(RAIZ, "dados", "log_2t_2026.csv")); ap.add_argument("--ufs", default=UFS_PADRAO)
    ap.add_argument("--probe", action="store_true"); ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if a.probe: probe(a); sys.exit()
    if a.demo: demo(); sys.exit()
    logf = log = None
    if a.loop:
        novo = not os.path.exists(a.log); logf = open(a.log, "a", newline=""); log = csv.writer(logf)
        if novo: log.writerow(["hora_tse", "pst", "lula", "flavio", "margem", "implicita_k1", "p_flavio", "brancos_nulos", "abstencao"] + [f"{u}_m" for u in UFS_PADRAO.split(",")] + [f"{u}_pst" for u in UFS_PADRAO.split(",")])
    while True:
        leitura(a, log)
        if logf: logf.flush()
        if not a.loop: break
        time.sleep(a.loop)
