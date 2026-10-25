#!/bin/zsh
# Noite de 25/10/2026: roda o logger da página (régua + brutos do TSE) e o script regional do dossiê, lado a lado, a cada 2 min.
# Uso: zsh ferramentas/noite.sh        (deixar o terminal aberto; Ctrl+C encerra os dois)
set -u
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
DOSSIE="/Users/guilhermecarneiro/Code/stf-caso-master"
mkdir -p "$RAIZ/dados/noite"
echo "== probe do TSE =="; python3 "$RAIZ/ferramentas/apuracao.py" --probe
echo; echo "== logger da página (dados/log_2t_2026.csv + dados/noite/*.json.gz) =="
python3 "$RAIZ/ferramentas/apuracao.py" --loop 120 2>&1 | tee -a "$RAIZ/dados/noite/logger.txt" &
P1=$!
echo "== régua regional do dossiê (dados/noite/regioes.txt), a cada 2 min =="
( while true; do echo "----- $(date '+%H:%M:%S') -----"; python3 "$DOSSIE/ferramentas/pesquisas_2t_regioes.py" --live --ele 6258 2>&1 | sed -n '/§5/,$p'; sleep 120; done ) >> "$RAIZ/dados/noite/regioes.txt" 2>&1 &
P2=$!
trap "kill $P1 $P2 2>/dev/null; echo; echo 'encerrado'; exit 0" INT TERM
echo "rodando: logger (pid $P1) e regional (pid $P2). Para ver o regional ao vivo noutra aba: tail -f $RAIZ/dados/noite/regioes.txt"
wait
