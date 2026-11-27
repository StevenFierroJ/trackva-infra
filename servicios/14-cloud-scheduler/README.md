# 14 · Cloud Scheduler y cola de trabajos

| | |
|---|---|
| **Estado** | Configurado el 27-nov-2026 por línea de comandos. El trabajo `trackva-hourly-tick` queda **pausado** hasta que la API con R-45 llegue a develop |
| **Proyecto** | `trackva-dev` |
| **Región** | `us-east4` |
| **ADR del diseño** | ADR-04, ADR-13 |
| **Costo estimado** | US$0 (Cloud Scheduler: 3 trabajos gratis por cuenta de facturación; Cloud Tasks: el primer millón de operaciones al mes) |

## 1. Para qué sirve en TrackVa

Hace que los trabajos diarios corran solos. Cada hora, Cloud Scheduler llama a un punto interno
de la API (`/api/v1/internal/schedule/tick`). La API no hace el trabajo ahí: para cada empresa
con bodega mira su hora local y deja en la cola `jobs` lo que toca, una tarea por empresa:

| Trabajo | Hora local de la empresa |
|---|---|
| Cargo diario de almacenamiento | 23:00 |
| Resumen diario de alertas por correo | 07:00 |
| Conciliación del stock (nunca corrige) | 03:00 |

El mismo tic vuelve a encolar los correos que lleven más de 10 minutos sin salir. Los correos
van por la cola `notifications` del servicio 10.

Cloud Tasks llama después a `/api/v1/internal/tasks` con un token OIDC de
`trackva-tasks-invoker`; la API comprueba emisor, audiencia y cuenta antes de ejecutar
(ADR-13). Contrato y código: `trackva-api` R-45 (`TaskQueuePort`, CLAUDE.md §12.0.bis).

## 2. Requisitos previos

Servicios 06 (API desplegada), 09 (Cloud Armor) y 10 (cuenta `trackva-tasks-invoker`, con la
API como «Usuario de cuenta de servicio» sobre ella).

## 3. Paso a paso

Todo por línea de comandos, desde `trackva-infra` con `source scripts/env.sh`.

### 3.1 API de Cloud Scheduler

```bash
gcloud services enable cloudscheduler.googleapis.com
```

```text
Operation "operations/acf.p2-1082495364-8da05796-…" finished successfully.
```

### 3.2 Cola `jobs`

Una cola aparte para que los trabajos diarios no compitan con los correos, con más intentos y
esperas más largas que `notifications`:

```bash
gcloud tasks queues create "$JOBS_QUEUE" --location="$REGION" \
  --max-dispatches-per-second=2 --max-concurrent-dispatches=2 \
  --max-attempts=5 --min-backoff=10s --max-backoff=300s
gcloud tasks queues add-iam-policy-binding "$JOBS_QUEUE" --location="$REGION" \
  --member="serviceAccount:$SA_API@$PROJECT_ID.iam.gserviceaccount.com" \
  --role=roles/cloudtasks.enqueuer
```

```text
Created queue [us-east4/jobs].
```

### 3.3 Trabajo de cada hora

Llama a la URL `run.app` de la API (no al dominio: el balanceador niega las rutas internas,
paso 3.4). Se crea pausado y se reanuda cuando la API desplegada tenga la ruta (sección 7).

```bash
RUN_URL="https://trackva-api-$PROJECT_NUMBER.$REGION.run.app"
gcloud scheduler jobs create http "$SCHEDULER_TICK" --location="$REGION" \
  --schedule="5 * * * *" --time-zone="Etc/UTC" \
  --uri="$RUN_URL/api/v1/internal/schedule/tick" --http-method=POST \
  --oidc-service-account-email="$SA_TASKS@$PROJECT_ID.iam.gserviceaccount.com" \
  --oidc-token-audience="$RUN_URL" --attempt-deadline=60s \
  --description="R-45: tic de cada hora; reparte los trabajos diarios por empresa"
gcloud scheduler jobs pause "$SCHEDULER_TICK" --location="$REGION"
```

En UTC y al minuto 5: la API calcula la hora local de cada empresa, así que una sola
programación sirve para Colombia, México, España y Estados Unidos.

### 3.4 Regla de Cloud Armor

Las rutas internas solo las llaman Cloud Tasks y Cloud Scheduler, por la URL `run.app`. Por el
balanceador no tienen por qué entrar: se niegan antes de la regla 900 («Deja pasar las llamadas
de los propios servicios»).

```bash
gcloud compute security-policies rules create 800 --security-policy="$ARMOR_POLICY" \
  --expression="request.path.startsWith('/api/v1/internal/')" --action=deny-404 \
  --description="R-45: las rutas internas de la API no se exponen por el balanceador"
```

Tardó unos dos minutos en aplicarse.

### 3.5 Alertas

Dos alertas por registro, en `servicios/12-observabilidad/alertas/` y creadas con
`bash scripts/crear-alertas-uso.sh` (que no repite las que ya existen):

- **tareas internas con error:** una respuesta 5xx en `/api/v1/internal/`;
- **conciliación del WMS con diferencias:** la entrada `wms-reconcile: diferencias entre libro y saldos`.

```text
creada:    TrackVa develop · conciliación del WMS con diferencias
creada:    TrackVa develop · tareas internas con error
```

## 4. Verificación

```bash
gcloud tasks queues describe "$JOBS_QUEUE" --location="$REGION" \
  --format="yaml(name.basename(),state,rateLimits,retryConfig)"
gcloud scheduler jobs describe "$SCHEDULER_TICK" --location="$REGION" \
  --format="yaml(name.basename(),schedule,timeZone,state,httpTarget.uri,httpTarget.oidcToken)"
curl -s -X POST "https://$DEV_DOMAIN/api/v1/internal/tasks" | head -c 40
```

Estado al 27-nov:

```text
cola jobs (us-east4)   state: RUNNING
   rateLimits:  maxDispatchesPerSecond 2 · maxConcurrentDispatches 2
   retryConfig: maxAttempts 5 · minBackoff 10s · maxBackoff 300s
   roles/cloudtasks.enqueuer → trackva-api-cloud-run

trackva-hourly-tick   schedule: 5 * * * *  (Etc/UTC)   state: PAUSED
   uri: https://trackva-api-1082495364.us-east4.run.app/api/v1/internal/schedule/tick
   oidcToken: trackva-tasks-invoker@trackva-dev.iam.gserviceaccount.com · audiencia la URL run.app

POST https://app-dev.trackva.com.co/api/v1/internal/tasks → 404 de Cloud Armor (página HTML,
no la respuesta JSON de la API)
```

## 5. Índice de capturas

Este servicio se configuró por línea de comandos: la evidencia son los comandos y sus salidas
de las secciones 3 y 4.

## 6. Cómo deshacerlo

```bash
gcloud scheduler jobs delete "$SCHEDULER_TICK" --location="$REGION"
gcloud tasks queues delete "$JOBS_QUEUE" --location="$REGION"
gcloud compute security-policies rules delete 800 --security-policy="$ARMOR_POLICY"
```

Antes, poner `TASK_QUEUE_DRIVER=in_process` en `trackva-api/deploy/develop.env`, o la API
seguirá intentando encolar en `jobs`.

## 7. Diferencias con el diseño y pendientes

- **Pausado hasta el despliegue.** La API desplegada todavía no tiene `/api/v1/internal/*`.
  Cuando `trackva-api` con R-45 pase a `main` y se despliegue: reanudar con
  `gcloud scheduler jobs resume "$SCHEDULER_TICK" --location="$REGION"` y forzar un tic con
  `gcloud scheduler jobs run "$SCHEDULER_TICK" --location="$REGION"`.
- **Por comprobar al reanudar:** que Cloud Scheduler entra a la API con el ingress cerrado
  (Cloud Tasks sí, servicio 10). Si no entra, el registro de Cloud Run lo muestra como 403 o
  404 en `/schedule/tick`; la alternativa es que el tic lo encole Cloud Tasks.
- El diseño original no tenía planificador: los trabajos diarios llegaron con el WMS.
