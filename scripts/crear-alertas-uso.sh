#!/usr/bin/env bash
# Crea en Cloud Monitoring las alertas de uso de los contenedores de Cloud Run (memoria, CPU e
# instancias de la API en su máximo), a partir de servicios/12-observabilidad/alertas/*.json.
#
# Uso: bash scripts/crear-alertas-uso.sh
#
# Usa la API de Monitoring directamente: los comandos `gcloud alpha monitoring` piden instalar
# componentes adicionales. No vuelve a crear una alerta que ya exista con el mismo nombre.
set -euo pipefail

HERE="$(cd "$(dirname "$0")/.." && pwd)"
source "$HERE/scripts/env.sh"

API="https://monitoring.googleapis.com/v3/projects/$PROJECT_ID"
auth=(-H "Authorization: Bearer $(gcloud auth print-access-token)" -H "X-Goog-User-Project: $PROJECT_ID")

# Canal de aviso: el primero de tipo correo que esté activo.
CHANNEL="$(curl -fsS "${auth[@]}" "$API/notificationChannels" | python3 -c '
import json, sys
chans = [c for c in json.load(sys.stdin).get("notificationChannels", []) if c.get("type") == "email" and c.get("enabled", True)]
print(chans[0]["name"] if chans else "")')"
[ -n "$CHANNEL" ] || { echo "No hay un canal de correo en Monitoring" >&2; exit 1; }

existing="$(curl -fsS "${auth[@]}" "$API/alertPolicies" | python3 -c '
import json, sys
print("\n".join(p["displayName"] for p in json.load(sys.stdin).get("alertPolicies", [])))')"

for file in "$HERE"/servicios/12-observabilidad/alertas/*.json; do
  name="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["displayName"])' "$file")"
  if grep -qxF "$name" <<<"$existing"; then
    echo "ya existe: $name"
    continue
  fi
  body="$(CHANNEL="$CHANNEL" python3 -c '
import os, sys
print(open(sys.argv[1]).read().replace("${CHANNEL}", os.environ["CHANNEL"]))' "$file")"
  curl -fsS -X POST "${auth[@]}" -H "Content-Type: application/json" "$API/alertPolicies" -d "$body" >/dev/null
  echo "creada:    $name"
done
