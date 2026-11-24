#!/usr/bin/env bash
# Compila la imagen de trackva-web para develop con Cloud Build y la sube a Artifact Registry.
# Uso: bash scripts/build-web.sh
#
# Los dominios salen de scripts/env.sh. La URL de Supabase y la llave anónima se leen de
# trackva-web/.env.local (que apunta al Supabase de dev). La llave de Google Maps del navegador
# se pide a Google Cloud por su identificador (MAPS_BROWSER_KEY_ID): es la llave restringida a
# los sitios de develop, no la de desarrollo local.
# Las tres son públicas por diseño: viajan en el JavaScript que descarga el navegador.
#
# TAG_SUFFIX (opcional): sufijo de la etiqueta cuando se recompila el mismo commit con otros
# valores, p. ej. TAG_SUFFIX=-maps2 bash scripts/build-web.sh
set -euo pipefail

HERE="$(cd "$(dirname "$0")/.." && pwd)"
source "$HERE/scripts/env.sh"

WEB_ENV="${WEB_ENV:-$HERE/../trackva-web/.env.local}"
[ -f "$WEB_ENV" ] || { echo "No existe $WEB_ENV" >&2; exit 1; }
val() { grep -E "^$1=" "$WEB_ENV" | head -1 | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//'; }

SUPABASE_URL="$(val NEXT_PUBLIC_SUPABASE_URL)"
SUPABASE_ANON_KEY="$(val NEXT_PUBLIC_SUPABASE_ANON_KEY)"
GOOGLE_MAPS_KEY="$(gcloud services api-keys get-key-string "$MAPS_BROWSER_KEY_ID" --format="value(keyString)")"
[ -n "$SUPABASE_URL" ] && [ -n "$SUPABASE_ANON_KEY" ] || { echo "Faltan valores de Supabase en $WEB_ENV" >&2; exit 1; }
[ -n "$GOOGLE_MAPS_KEY" ] || { echo "No se pudo leer la llave de Maps $MAPS_BROWSER_KEY_ID" >&2; exit 1; }

SRC=/tmp/trackva-web-build
rm -rf "$SRC"
git clone --depth 1 https://github.com/StevenFierroJ/trackva-web.git "$SRC"
TAG="$(git -C "$SRC" rev-parse --short HEAD)${TAG_SUFFIX:-}"
IMAGE="$AR_PATH/trackva-web:$TAG"
BASE="https://$DEV_DOMAIN"

echo "Imagen:   $IMAGE"
echo "API:      $BASE   (rutas /api/v1/*)"
echo "Supabase: $SUPABASE_URL"

gcloud builds submit "$SRC" --region="$REGION" --config="$HERE/scripts/cloudbuild-web.yaml" \
  --substitutions="_IMAGE=$IMAGE,_API_URL=$BASE,_SUPABASE_URL=$SUPABASE_URL,_SUPABASE_ANON_KEY=$SUPABASE_ANON_KEY,_TRACKING_URL=$BASE/track,_WIDGETS_URL=$BASE/w,_GOOGLE_MAPS_KEY=$GOOGLE_MAPS_KEY"
