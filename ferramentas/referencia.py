#!/usr/bin/env python3
"""Gera os dados de referência da página (docs/referencia.js) a partir das fontes primárias do TSE.

Fontes:
  - Histórico oficial de totalização do 2º turno de 2022 (presidente, BR) → curva de composição por % de seções, horas, virada.
  - detalhe_votacao_munzona_2022.zip → abstenção e brancos+nulos do 2º turno de 2022 por UF.
  - votacao_candidato_munzona_2022.zip (580 MB, opcional, --munzona CAMINHO) → Lula × Bolsonaro no 2º turno de 2022 por UF.
    Sem o arquivo, mantém o que já está em dados/urna_2t_2022_uf.json.
  - Divulga/TSE, eleição 6257 (1º turno de 2026) → resultado final por UF (Lula, Flávio, abstenção, brancos+nulos).

Uso: python3 ferramentas/referencia.py [--munzona /caminho/votacao_candidato_munzona_2022.zip] [--sem-rede]
Saída: dados/*.json (fonte) e docs/referencia.js (o que a página carrega).
"""
import argparse, csv, io, json, os, sys, urllib.request, zipfile, concurrent.futures, datetime

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DADOS = os.path.join(RAIZ, "dados"); DOCS = os.path.join(RAIZ, "docs")
UA = {"User-Agent": "Mozilla/5.0"}
HIST_2T = "https://cdn.tse.jus.br/estatistica/sead/eleicoes/eleicoes2022/Historico_Totalizacao_Presidente_BR_2T_2022.zip"
DETALHE = "https://cdn.tse.jus.br/estatistica/sead/odsele/detalhe_votacao_munzona/detalhe_votacao_munzona_2022.zip"
UFS = "ac al ap am ba ce df es go ma mt ms mg pa pb pr pe pi rj rn rs ro rr sc sp se to".split()

def baixar(url, nome):
    cache = os.path.join(DADOS, "cache"); os.makedirs(cache, exist_ok=True)
    p = os.path.join(cache, nome)
    if not os.path.exists(p):
        print(f"baixando {url}"); open(p, "wb").write(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300).read())
    return p

def num(s):
    if s is None: return None
    s = str(s).strip()
    if "," in s: s = s.replace(".", "").replace(",", ".")
    try: return float(s)
    except ValueError: return None

def curva_2t_2022(path):
    z = zipfile.ZipFile(path); name = [n for n in z.namelist() if n.endswith(".csv")][0]
    r = csv.reader(io.TextIOWrapper(z.open(name), encoding="latin1"), delimiter=";"); hdr = [h.strip() for h in next(r)]; ix = {h: i for i, h in enumerate(hdr)}
    rows = []
    for line in r:
        if len(line) < len(hdr): continue
        try:
            pct = 100 * float(line[ix["PE_SECOES_TOT_ACUMULADO"]].replace(",", "."))
            L = int(line[ix["LULA_QT_VOTOS_TOT_ACUMULADO"]]); B = int(line[ix["JAIR_BOLSONARO_QT_VOTOS_TOT_ACUMULADO"]])
            V = int(line[ix["QT_VOTOS_CONCORRENTES_ACUMULADO"]]); sec = int(line[ix["QT_SECOES_TOT_ACUMULADO"]])
            br = int(line[ix["BRANCO_QT_VOTOS_TOT_ACUMULADO"]]); nu = int(line[ix["NULO_QT_VOTOS_TOT_ACUMULADO"]]); tv = int(line[ix["QT_VOTOS_TOTAL_ACUMULADO"]])
            dt = line[ix["DT_TOTALIZACAO"]].strip()
        except (ValueError, KeyError): continue
        if V > 0: rows.append((pct, sec, dt, L, B, V, br, nu, tv))
    rows.sort(key=lambda x: x[1]); fin = rows[-1]; mf = 100 * (fin[3] - fin[4]) / fin[5]
    def ponto(t):
        b = min(rows, key=lambda x: abs(x[0] - t)); m = 100 * (b[3] - b[4]) / b[5]
        return {"pst": round(b[0], 2), "hora": b[2][-8:-3], "margem": round(m, 2), "efeito": round(m - mf, 2)}
    grade = [0.5, 1, 1.5, 2, 3, 4, 5, 6, 7, 8, 9, 10] + list(range(12, 100, 2)) + [99, 99.5, 100]
    pontos = [ponto(t) for t in grade]
    virada = None; prev = None
    for x in rows:
        m = 100 * (x[3] - x[4]) / x[5]
        if prev is not None and prev < 0 <= m: virada = {"pst": round(x[0], 2), "hora": x[2][-8:-3]}; break
        prev = m
    return {"final": {"lula": round(100 * fin[3] / fin[5], 2), "bolsonaro": round(100 * fin[4] / fin[5], 2), "margem": round(mf, 2),
                      "bn": round(100 * (fin[6] + fin[7]) / fin[8], 2), "hora": fin[2]},
            "pontos": pontos, "virada": virada, "fonte": HIST_2T}

def detalhe_2t_2022(path):
    z = zipfile.ZipFile(path); agg = {}
    r = csv.reader(io.TextIOWrapper(z.open("detalhe_votacao_munzona_2022_BRASIL.csv"), encoding="latin1"), delimiter=";"); hdr = [h.strip() for h in next(r)]; ix = {h: i for i, h in enumerate(hdr)}
    for line in r:
        if line[ix["NR_TURNO"]] != "2" or line[ix["CD_CARGO"]] != "1": continue
        a = agg.setdefault(line[ix["SG_UF"]].lower(), {"aptos": 0, "abst": 0, "br": 0, "nu": 0, "votos": 0})
        a["aptos"] += int(line[ix["QT_APTOS"]]); a["abst"] += int(line[ix["QT_ABSTENCOES"]]); a["votos"] += int(line[ix["QT_VOTOS"]])
        a["br"] += int(line[ix["QT_VOTOS_BRANCOS"]]); a["nu"] += int(line[ix["QT_TOTAL_VOTOS_NULOS"]])
    pct = lambda a: {"abst": round(100 * a["abst"] / a["aptos"], 2), "bn": round(100 * (a["br"] + a["nu"]) / a["votos"], 2)}
    out = {u: pct(a) for u, a in agg.items()}
    out["br"] = pct({k: sum(v[k] for v in agg.values()) for k in agg["sp"]})
    return out

def munzona_2t_2022(path):
    z = zipfile.ZipFile(path); name = [n for n in z.namelist() if n.endswith("_BRASIL.csv")][0]
    r = csv.reader(io.TextIOWrapper(z.open(name), encoding="latin1"), delimiter=";"); hdr = [h.strip() for h in next(r)]; ix = {h: i for i, h in enumerate(hdr)}
    iT, iC, iU, iN, iV = ix["NR_TURNO"], ix["CD_CARGO"], ix["SG_UF"], ix["NR_CANDIDATO"], ix["QT_VOTOS_NOMINAIS_VALIDOS"]
    agg = {}
    for line in r:
        if line[iT] != "2" or line[iC] != "1": continue
        a = agg.setdefault(line[iU].lower(), {"13": 0, "22": 0}); a[line[iN]] = a.get(line[iN], 0) + int(line[iV])
    out = {}
    for u, a in agg.items():
        tot = a["13"] + a["22"]; out[u] = {"lula": round(100 * a["13"] / tot, 2), "bolsonaro": round(100 * a["22"] / tot, 2), "margem": round(100 * (a["13"] - a["22"]) / tot, 2), "validos": tot}
    t13 = sum(a["13"] for a in agg.values()); t22 = sum(a["22"] for a in agg.values())
    out["br"] = {"lula": round(100 * t13 / (t13 + t22), 2), "bolsonaro": round(100 * t22 / (t13 + t22), 2), "margem": round(100 * (t13 - t22) / (t13 + t22), 2), "validos": t13 + t22}
    return out

def urna_1t_2026():
    def get(uf):
        u = f"https://resultados.tse.jus.br/oficial/ele2026/6257/dados/{uf}/{uf}-c0001-e006257-u.json"
        j = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30).read())
        votos = {}
        for carg in j.get("carg", []):
            for agr in carg.get("agr", []):
                for par in agr.get("par", []):
                    for c in par.get("cand", []): votos[str(c["n"])] = votos.get(str(c["n"]), 0) + int(num(c["vap"]) or 0)
        tot = sum(votos.values()) or 1; L = votos.get("13", 0); F = votos.get("22", 0)
        e, v = j.get("e", {}), j.get("v", {}); tv = num(v.get("tv")) or 0
        return uf, {"lula": round(100 * L / tot, 2), "flavio": round(100 * F / tot, 2), "margem": round(100 * (L - F) / tot, 2), "terceiros": round(100 * (tot - L - F) / tot, 2),
                    "abst": round(num(e.get("pan") or e.get("pa")), 2), "bn": round(100 * ((num(v.get("vb")) or 0) + (num(v.get("vn")) or 0)) / tv, 2) if tv else None, "validos": tot, "arquivo": f"{j.get('dg')} {j.get('hg')}"}
    with concurrent.futures.ThreadPoolExecutor(8) as ex: return dict(ex.map(get, UFS + ["br"]))

def prior_pesquisas(pq):
    """Última onda de cada instituto com campo encerrado em `corte` ou depois → margem Lula−Flávio bruta e corrigida por
    fator_correcao × erro do 1º turno; centro = média das corrigidas; P(Flávio) = Φ(−centro/sigma0)."""
    import math
    ult = {}
    for r in sorted(pq["pesquisas"], key=lambda r: r["fim"]):
        if r["fim"] >= pq["corte"]: ult[r["inst"]] = r
    linhas = []
    for r in ult.values():
        bruta = r["lula"] - r["flavio"]; corr = bruta + pq["fator_correcao"] * r["erro_1t"]
        linhas.append({**r, "bruta": round(bruta, 2), "corrigida": round(corr, 2)})
    linhas.sort(key=lambda r: r["fim"], reverse=True)
    mu = sum(r["corrigida"] for r in linhas) / len(linhas); mub = sum(r["bruta"] for r in linhas) / len(linhas)
    sd = pq["sigma0"]; phi = lambda z: 0.5 * (1 + math.erf(z / math.sqrt(2)))
    return {"corte": pq["corte"], "fator": pq["fator_correcao"], "sigma0": sd, "n": len(linhas), "mu_bruta": round(mub, 2), "mu": round(mu, 2),
            "p_flavio": round(100 * phi(-mu / sd), 1), "p_flavio_sem_correcao": round(100 * phi(-mub / sd), 1), "ultimas": linhas,
            "todas": sorted(pq["pesquisas"], key=lambda r: r["fim"], reverse=True)}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--munzona"); ap.add_argument("--sem-rede", action="store_true"); a = ap.parse_args()
    os.makedirs(DADOS, exist_ok=True); os.makedirs(DOCS, exist_ok=True)
    def ler(nome):
        p = os.path.join(DADOS, nome); return json.load(open(p)) if os.path.exists(p) else None
    def gravar(nome, obj):
        json.dump(obj, open(os.path.join(DADOS, nome), "w"), indent=1, ensure_ascii=False, sort_keys=True)
    if not a.sem_rede:
        gravar("curva_2t_2022.json", curva_2t_2022(baixar(HIST_2T, "Historico_Totalizacao_Presidente_BR_2T_2022.zip")))
        gravar("detalhe_2t_2022_uf.json", detalhe_2t_2022(baixar(DETALHE, "detalhe_votacao_munzona_2022.zip")))
        gravar("urna_1t_2026_uf.json", urna_1t_2026())
    if a.munzona: gravar("urna_2t_2022_uf.json", munzona_2t_2022(a.munzona))
    curva, det, u26, u22 = ler("curva_2t_2022.json"), ler("detalhe_2t_2022_uf.json"), ler("urna_1t_2026_uf.json"), ler("urna_2t_2022_uf.json")
    pq = ler("pesquisas_2t.json"); prior = prior_pesquisas(pq) if pq else None
    faltam = [n for n, v in (("curva", curva), ("detalhe", det), ("urna 1T 2026", u26), ("urna 2T 2022", u22)) if v is None]
    if faltam: sys.exit(f"faltam dados: {faltam}")
    ref = {"gerado": datetime.datetime.now().isoformat(timespec="minutes"),
           "curva": [[p["pst"], p["efeito"]] for p in curva["pontos"]],
           "horas": {str(int(round(p["pst"]))): p["hora"] for p in curva["pontos"] if int(round(p["pst"])) in (2, 5, 10, 20, 30, 40, 50, 60, 68, 70, 80, 90, 95, 99, 100)},
           "virada2022": curva["virada"], "final2022": curva["final"],
           "uf2022": {u: {"margem": u22[u]["margem"], "lula": u22[u]["lula"], "abst": det[u]["abst"], "bn": det[u]["bn"]} for u in UFS + ["br"]},
           "uf2026": {u: {"margem": u26[u]["margem"], "lula": u26[u]["lula"], "flavio": u26[u]["flavio"], "abst": u26[u]["abst"], "bn": u26[u]["bn"]} for u in UFS + ["br"]},
           "prior": prior}
    open(os.path.join(DOCS, "referencia.js"), "w").write("// gerado por ferramentas/referencia.py a partir dos arquivos oficiais do TSE; não editar à mão\nwindow.REF=" + json.dumps(ref, ensure_ascii=False, separators=(",", ":")) + ";\n")
    print(f"ok: docs/referencia.js ({os.path.getsize(os.path.join(DOCS,'referencia.js'))} bytes)")
    print("final 2T 2022:", curva["final"], "virada:", curva["virada"])
    print("BR 2T 2022 abst/bn:", det["br"], "| BR 2022 L×B:", u22["br"], "| BR 1T 2026:", u26["br"])
    if prior:
        print(f"prior pelas pesquisas (corte {prior['corte']}, {prior['n']} institutos): bruta {prior['mu_bruta']:+.2f}, corrigida ×{prior['fator']} {prior['mu']:+.2f}, sigma0 {prior['sigma0']} → P(Flávio) {prior['p_flavio']}% (sem correção {prior['p_flavio_sem_correcao']}%)")
        for r in prior["ultimas"]: print(f"   {r['inst']:18s} {r['onda']} fim {r['fim']} {r['modo']:6s} L {r['lula']:4.1f} × F {r['flavio']:4.1f}  bruta {r['bruta']:+5.1f}  erro1T {r['erro_1t']:+4.1f}  corrigida {r['corrigida']:+5.1f}")

if __name__ == "__main__": main()
