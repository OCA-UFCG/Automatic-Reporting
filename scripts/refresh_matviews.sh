#!/usr/bin/env bash
#
# Atualiza as materialized views de perfil pesadas (relatorios_auto.mv_perfil_*).
#
# Uso:
#   - Cron (diário): ver docs/matviews-perfil.md. A VM roda em UTC, então 01:00 BRT = 04:00 UTC.
#       0 4 * * *  /caminho/refresh_matviews.sh   # = 01:00 America/Sao_Paulo
#   - On-demand (após uma carga de dados):  ./refresh_matviews.sh
#
# Por que existe: vw_perfil_economia (>30s) e vw_perfil_saude_municipal (~12s) são
# agregações pesadas recalculadas a cada relatório. Materializadas, a leitura vira ~ms;
# este script reconstrói o snapshot. Rationale completo em docs/matviews-perfil.md.
#
# REFRESH ... CONCURRENTLY não bloqueia as leituras durante o refresh — exige um índice
# único em cada matview (criado junto do build). O statement_timeout é rede de segurança.
#
# Autenticação: assume conexão local sem senha (peer/trust) OU um ~/.pgpass. Se precisar,
# exporte PGPASSWORD antes de chamar.

set -uo pipefail

# --- conexão (sobrescrevível por env) ---
DB_HOST="${DB_HOST:-127.0.0.1}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-oca_user}"
DB_NAME="${DB_NAME:-oca_db}"
SCHEMA="relatorios_auto"

# Cap por refresh (ms). Um refresh normal leva ~1-2min; 10min é folga.
STMT_TIMEOUT_MS="${STMT_TIMEOUT_MS:-600000}"

# Matviews a atualizar — ADICIONE aqui ao materializar uma nova view.
MATVIEWS=(
  mv_perfil_economia
  mv_perfil_saude_municipal
  mv_perfil_educacional_municipal
  mv_indicadores
)

# --- log (timestamps em UTC, coerente com a VM) ---
LOG_FILE="${LOG_FILE:-${HOME:-/tmp}/logs/refresh_matviews.log}"
if ! mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null; then
  LOG_FILE="/tmp/refresh_matviews.log"
fi
log() { echo "$(date -u '+%Y-%m-%dT%H:%M:%SZ') $*" | tee -a "$LOG_FILE"; }

# --- lock: evita cron e execução manual (ou dois crons) se sobreporem ---
LOCK_FILE="${LOCK_FILE:-/tmp/refresh_matviews.lock}"
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  log "ABORT: outro refresh já está em execução (lock: $LOCK_FILE)"
  exit 1
fi

refresh_um() {
  local mv="$1"
  PGOPTIONS="-c statement_timeout=${STMT_TIMEOUT_MS}" \
    psql -X -v ON_ERROR_STOP=1 -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
      -c "REFRESH MATERIALIZED VIEW CONCURRENTLY ${SCHEMA}.${mv};"
}

log "=== refresh_matviews início (${#MATVIEWS[@]} matviews) ==="
rc_total=0
for mv in "${MATVIEWS[@]}"; do
  inicio=$(date +%s)
  if saida=$(refresh_um "$mv" 2>&1); then
    log "OK    ${mv} ($(( $(date +%s) - inicio ))s)"
  else
    rc_total=1
    # uma falha (timeout, lock, matview inexistente) não aborta as demais
    log "FALHA ${mv} ($(( $(date +%s) - inicio ))s): ${saida}"
  fi
done
log "=== refresh_matviews fim (rc=$rc_total) ==="

# Invalida o cache de relatórios prontos: marca que os dados mudaram, forçando
# regeneração preguiçosa no próximo acesso (services/cache.py compara mtime).
CONTAINER="${REPORT_CONTAINER:-automatic-reporting-beta}"
if docker exec "$CONTAINER" touch /app/output/.data_version 2>/dev/null; then
  log "cache de relatórios invalidado (.data_version tocado em $CONTAINER)"
else
  log "AVISO: não consegui tocar .data_version no container $CONTAINER"
fi

exit "$rc_total"
