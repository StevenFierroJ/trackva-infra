# 15 · Webhook y secretos de WhatsApp (Cloud API de Meta)

| | |
|---|---|
| **Estado** | Configurado el 27-nov-2026: regla de Cloud Armor, tres secretos conectados al servicio y webhook suscrito y probado desde Meta |
| **Proyecto** | `trackva-dev` |
| **Región** | `us-east4` |
| **ADR del diseño** | — (R-36, propuesta v1.1 en `trackva-docs`) |
| **Costo estimado** | US$1/mes (una regla más de Cloud Armor; los tres secretos entran en la capa gratuita de Secret Manager) |

## 1. Para qué sirve en TrackVa

Los couriers conectan su propio número de WhatsApp a TrackVa. Meta entrega lo que llega a esos números a **una sola URL para todas las empresas**:

```
https://app-dev.trackva.com.co/api/v1/public/whatsapp/webhook
```

La API reparte cada evento por el número de Meta (`phone_number_id`). Lo que protege la ruta es la firma `X-Hub-Signature-256`, que se calcula con el app secret. El token de cada courier **no** va en Secret Manager: va cifrado en la base. Por eso son tres secretos fijos, sin importar cuántos couriers conecten su número.

## 2. Requisitos previos

- App de Meta «TrackVa» (id `1691871302339001`) registrada como proveedor de tecnología, con el portfolio verificado. Hecho el 26 y 27-nov.
- Migración `20261205120000_whatsapp_channel` aplicada en la base de dev. Hecho el 27-nov.
- El código del webhook desplegado en develop, es decir, `trackva-api` pasado de `develop` a `main`. Sin él, Meta no puede verificar la URL.

## 3. Paso a paso

### 3.1 Regla de Cloud Armor (27-nov)

```bash
source scripts/env.sh
gcloud compute security-policies rules create 950 --security-policy=trackva-armor \
  --expression="request.path == '/api/v1/public/whatsapp/webhook'" --action=allow \
  --description="R-36: webhook de WhatsApp (Meta). Sin límite por IP ni reglas de ataques web; lo protege la firma X-Hub-Signature-256"
```

```
950	allow	request.path == '/api/v1/public/whatsapp/webhook'
```

Va antes de la 1000 (límite por IP) y de la 2000/2100 (ataques web). El motivo está en el servicio 09.

### 3.2 Secretos (27-nov)

Los dos que genera TrackVa se crearon sin que el valor pase por la pantalla:

```bash
openssl rand -hex 32 | tr -d '\n' | gcloud secrets create api-whatsapp-webhook-verify-token \
  --replication-policy=automatic --data-file=-
openssl rand -base64 32 | tr -d '\n' | gcloud secrets create api-whatsapp-token-encryption-key \
  --replication-policy=automatic --data-file=-
gcloud secrets create api-whatsapp-app-secret --replication-policy=automatic   # sin versión: la agrega Steven
for s in api-whatsapp-app-secret api-whatsapp-webhook-verify-token api-whatsapp-token-encryption-key; do
  gcloud secrets add-iam-policy-binding $s \
    --member="serviceAccount:trackva-api-cloud-run@$PROJECT_ID.iam.gserviceaccount.com" \
    --role=roles/secretmanager.secretAccessor
done
```

**App secret.** Se copia de Meta for Developers › TrackVa › Configuración de la app › Básica › **Clave secreta de la app**: Meta pide la contraseña de Facebook para mostrarlo. Se agrega sin que quede en el historial de la terminal:

```bash
read -s S && printf '%s' "$S" | gcloud secrets versions add api-whatsapp-app-secret --data-file=- ; unset S
```

### 3.3 Conectar los secretos al servicio (27-nov)

Los tres van juntos y **antes** de desplegar el código que trae `WHATSAPP_APP_ID` en `deploy/develop.env`. Con unas variables sí y otras no, la API no arranca.

```bash
gcloud run services update trackva-api --region=$REGION \
  --update-secrets="WHATSAPP_APP_SECRET=api-whatsapp-app-secret:latest,WHATSAPP_WEBHOOK_VERIFY_TOKEN=api-whatsapp-webhook-verify-token:latest,WHATSAPP_TOKEN_ENCRYPTION_KEY=api-whatsapp-token-encryption-key:latest"
```

```
Service [trackva-api] revision [trackva-api-00012-4pj] has been deployed and is serving 100 percent of traffic.
```

La revisión sigue con la imagen anterior, que todavía no lee las variables `WHATSAPP_*`; `/api/v1/health` respondió 200. El código que las usa llega al pasar `develop` a `main`.

### 3.4 Suscribir el webhook en Meta (27-nov, tras desplegar `trackva-api` #131)

En Meta for Developers › TrackVa › Casos de uso › Conectar en WhatsApp › Configuración:

| Campo | Valor |
|---|---|
| URL de devolución de llamada | `https://app-dev.trackva.com.co/api/v1/public/whatsapp/webhook` |
| Token de verificación | el valor de `api-whatsapp-webhook-verify-token` (`gcloud secrets versions access latest --secret=api-whatsapp-webhook-verify-token`) |
| Campo de webhook | `messages` (Meta deja suscritos además varios campos por defecto; la API solo procesa `messages` y a los demás responde 200) |

El token lo pegó Steven. Meta marcó «Configurar webhooks» como completado.

## 4. Verificación

```bash
# Sin la firma, la API responde 401 (no 403 ni 429 de Cloud Armor):
curl -s -o /dev/null -w "%{http_code}\n" -X POST https://$DEV_DOMAIN/api/v1/public/whatsapp/webhook \
  -H 'Content-Type: application/json' -d '{}'
```

Prueba desde Meta (campo `messages` › **Probar** › Enviar al servidor v27.0), 27-nov 19:11: Meta respondió «Se probó correctamente». En la base de dev quedó el evento en `whatsapp_webhook_events` con `tenant_id` vacío, porque la muestra de Meta trae el número de ejemplo `123456123`, que no es de ninguna empresa. Eso confirma la firma real de Meta contra el secreto cargado.

Mientras la app de Meta esté sin publicar, solo llegan estos webhooks de prueba del panel: los mensajes reales (incluso de los administradores) no se entregan hasta publicarla.

## 5. Notas

- La URL del webhook es una por app de Meta. Cuando exista producción, esta app apuntará allá y develop usará una app de prueba.
- Rotar la llave de cifrado obliga a volver a cifrar los tokens (`key_version`). Sin el proceso de rotación escrito, no se rota.
