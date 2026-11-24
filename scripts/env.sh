#!/usr/bin/env bash
# Variables compartidas por todos los comandos del despliegue de develop.
# Uso: source scripts/env.sh
# Aquí NO van secretos. Los secretos viven en Secret Manager (servicio 03).

# --- Proyecto, facturación y dominio ---
export PROJECT_ID="trackva-dev"            # creado por Steven en la consola el 23-nov-2026
export PROJECT_NUMBER="1082495364"
export BILLING_ACCOUNT="01B40F-71E1AA-6A96C9"  # «Trackva», factura en COP; enlazada por Steven el 23-nov
export DEV_DOMAIN="app-dev.trackva.com.co" # web en /, API en /api/*

# Configuración propia de gcloud: los comandos de esta carpeta van al proyecto de TrackVa
# sin cambiar la configuración activa del equipo (que apunta a otros proyectos).
export CLOUDSDK_ACTIVE_CONFIG_NAME="trackva-dev"

# --- Fijadas por el diseño (proyecto-final-cloud-grupo-08.docx) ---
export REGION="us-east4"                   # ADR-09
export VPC_NAME="trackva-vpc"              # ADR-12

# --- Nombres propuestos (se confirman al configurar cada servicio) ---
export AR_REPO="trackva-dev"               # Artifact Registry; creado por Steven en la consola, 23-nov
export AR_HOST="us-east4-docker.pkg.dev"
export AR_PATH="$AR_HOST/trackva-dev/trackva-dev"   # + /<servicio>:<etiqueta>
export SUBNET_NAME="trackva-run-us-east4"
export ROUTER_NAME="trackva-router"
export NAT_NAME="trackva-nat"
export NAT_IP_NAME="trackva-nat-ip"
export RUN_API="trackva-api"
export RUN_WEB="trackva-web"
export RUN_INTEGRATIONS="trackva-integrations"
export SA_API="trackva-api-cloud-run"                    # creadas por Steven en la consola, 23-nov
export SA_WEB="trackva-web-cloud"
export SA_INTEGRATIONS="trackva-integraciones-cloud-ru"   # la consola recortó el ID a 30 caracteres
export SA_TASKS="trackva-tasks-invoker"
export SA_DEPLOY="trackva-github-deploy"
export TASKS_QUEUE="notifications"
export ARMOR_POLICY="trackva-armor"
export LB_NAME="trackva-lb"

# --- Llaves de Google Maps (identificadores, no las llaves) ---
export MAPS_BROWSER_KEY_ID="0bc78b6c-dc18-4056-99d1-4cfc438c512d"   # «TrackVa dev · navegador»: por sitio, solo Maps JavaScript
export MAPS_SERVER_KEY_ID="c898cbb3-7a04-46f7-9016-b311cd8c64db"    # «TrackVa dev · servidor»: solo Geocoding y Routes
export MAPS_LOCAL_BROWSER_KEY_ID="fcf14532-b569-45ec-b9da-b914bfa1cb5c"  # «TrackVa local · navegador»: localhost, solo Maps JavaScript
export MAPS_LOCAL_SERVER_KEY_ID="55c57ecb-f541-451f-a8f7-bb028c8c53ca"   # «TrackVa local · servidor»: solo Geocoding y Routes
