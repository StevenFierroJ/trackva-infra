# 12 · Observabilidad

| | |
|---|---|
| **Estado** | Configurado el 24-nov-2026 |
| **Proyecto** | `trackva-dev` |
| **Región** | global |
| **ADR del diseño** | — (sección 6.2 del diseño: monitoreo y observabilidad) |
| **Costo estimado** | US$0 (las comprobaciones de disponibilidad y las alertas por correo son gratuitas a este volumen) |

## 1. Para qué sirve en TrackVa

Avisa cuando develop deja de responder o empieza a fallar, sin tener que estar mirando. Se apoya
en lo que Google Cloud ya recoge solo: los registros de los contenedores (Cloud Logging) y las
métricas de Cloud Run y del balanceador (Cloud Monitoring). Aquí se agrega lo que no viene por
defecto: una comprobación externa de disponibilidad y las alertas por correo.

| Pieza | Ya existe | Se agrega aquí |
|---|---|---|
| Registros de la API, la web e integraciones | Sí, en Cloud Logging, en JSON y con `X-Request-Id` | — |
| Métricas de Cloud Run y del balanceador | Sí, en Cloud Monitoring | — |
| Registros del balanceador y de Cloud Armor | Sí (se activaron en el servicio 08) | — |
| Comprobación de disponibilidad desde fuera | No | Sí |
| Avisos por correo | No | Sí |
| Errores de la app (Sentry) | La API ya envía con su DSN | — |

## 2. Requisitos previos

Servicio 08: el dominio `app-dev.trackva.com.co` responde.

## 3. Paso a paso

### 3.1 Canal de aviso

Monitoring › Alertas › **Editar canales de notificación** › Correo electrónico › **Agregar nuevo**:

| Campo | Valor |
|---|---|
| Dirección de correo | El correo personal de Steven |
| Nombre visible | `Steven - Personal - Trackva` |

**Captura — Canal de correo creado**

![Canal de correo creado](capturas/01-canal-correo.png)

### 3.2 Comprobación de disponibilidad de la API

Monitoring › Comprobaciones de tiempo de actividad › **Crear comprobación**:

| Sección | Campo | Valor |
|---|---|---|
| Destino | Protocolo | HTTPS |
| | Tipo de recurso | URL |
| | Nombre de host | `app-dev.trackva.com.co` |
| | Ruta | `/api/v1/health` |
| | Frecuencia | 15 minutos (decisión de Steven; la guía proponía 5) |
| | Regiones | Global (o al menos 3) |
| Validación de la respuesta | Tiempo de espera | 10 segundos |
| | Coincidencia de contenido | Contiene `"status":"ok"` |
| | Códigos aceptados | 200 |
| Alertas y notificaciones | Crear una alerta | Sí · nombre `TrackVa develop · API caída` · duración 5 minutos · canal `TrackVa develop · avisos` |
| Revisión | Título | `trackva-dev-api-health` |

Antes de crear, pulsar **Probar**: debe responder 200.

Esta comprobación pasa por todo el camino real: DNS, certificado, balanceador, Cloud Armor y
la API. Si cualquiera de esos falla, avisa.

**Frecuencia y arranque en frío.** Con 15 minutos la comprobación no alcanza a mantener
despierta la API (Cloud Run apaga la instancia tras unos 15 minutos sin uso), así que seguirá
habiendo arranques en frío. Con 5 minutos casi desaparecerían, sin costo: las comprobaciones
son gratuitas a este volumen y Cloud Run solo cobra el tiempo en que atiende peticiones.
`/api/v1/health` no consulta la base ni cae en las reglas de límite de Cloud Armor.

**Captura — Destino de la comprobación de la API**

![Destino de la comprobación de la API](capturas/02-crear-comprobacion.png)

**Captura — Validación de la respuesta**

![Validación de la respuesta](capturas/02b-validacion.png)

**Captura — Alerta asociada a la comprobación**

![Alerta asociada a la comprobación](capturas/02c-alerta.png)

### 3.3 Comprobación de disponibilidad de la web

Igual que la anterior, cambiando:

| Campo | Valor |
|---|---|
| Ruta | `/login` |
| Coincidencia de contenido | Contiene `TrackVa` |
| Nombre de la alerta | `TrackVa develop · web caída` |
| Título | `trackva-dev-web-login` |

**Captura — Prueba de la comprobación de la web en verde**

![Prueba de la comprobación de la web en verde](capturas/02d-prueba-web.png)

**Captura — Las dos comprobaciones creadas**

![Las dos comprobaciones creadas](capturas/03-comprobaciones.png)

### 3.4 Alerta de errores de la API

Monitoring › Alertas › **Crear política**:

| Campo | Valor |
|---|---|
| Métrica | Cloud Run Revision › Request Count (`run.googleapis.com/request_count`) |
| Filtros | `service_name = trackva-api` · `response_code_class = 5xx` |
| Agregación | Función de ventana `sum` de 5 minutos; en «series temporales», también `sum` sin agrupar |
| Condición | Por encima de `5` |
| Canal | `TrackVa develop · avisos` |
| Nombre | `TrackVa develop · errores 5xx en la API` |

Las respuestas 4xx no cuentan: son errores esperados del cliente (sesión vencida, datos
inválidos). Más de cinco respuestas 5xx en cinco minutos sí indica un fallo del servicio.

**Captura — Métrica, filtros y función de ventana**

![Métrica, filtros y función de ventana](capturas/04a-alerta-filtros.png)

**Captura — Umbral de la alerta**

![Umbral de la alerta](capturas/04b-alerta-umbral.png)

**Captura — Política de errores 5xx creada**

![Política de errores 5xx creada](capturas/04-politica-5xx.png)

## 4. Verificación

```bash
source scripts/env.sh
gcloud monitoring uptime list-configs \
  --format="table(displayName,httpCheck.path,period,monitoredResource.labels.host)"
```

Las políticas de alerta y los canales se revisan en la consola (Monitoring › Alertas): los
comandos de `gcloud` para leerlos piden instalar componentes adicionales.

Estado al 24-nov, leído de la API de Monitoring:

```text
COMPROBACIÓN trackva-dev-api-health | /api/v1/health | cada 900s | contenido: ""status":"ok"     ← comilla de más
COMPROBACIÓN trackva-dev-web-login  | /login         | cada 900s | contenido: TrackVa

POLÍTICA TrackVa develop · API caída               | activa | 1 canal
POLÍTICA TrackVa develop · web caída               | activa | 1 canal
POLÍTICA TrackVa develop · errores 5xx en la API   | activa | 1 canal
   filtro: cloud_run_revision · service_name = "trackva-api" · request_count · response_code_class = "5xx"
   agregación: ALIGN_SUM 300 s + REDUCE_SUM · condición: > 5 durante 300 s

CANAL Steven - Personal - Trackva | email | activo
```

**Corrección del mismo día.** La comprobación de la API validaba `""status":"ok"`, con dos
comillas al inicio, y fallaba siempre aunque la API respondiera 200 (los registros decían
`content_mismatch: true`). Steven lo corrigió a `"status":"ok"`. El cambio tardó unos minutos en
llegar a todas las regiones:

```text
20:27–20:29 UTC   São Paulo, Oregón, Singapur   FALLA   (aún con el texto anterior)
20:32 UTC         Iowa, Bélgica                 OK      (ya con el texto corregido)
```

Las regiones que quedan en rojo pasan a verde en su siguiente ronda (cada 15 minutos). Si la
alerta «API caída» llegó a abrirse por esto, se cierra sola.

## 5. Índice de capturas

| # | Qué muestra | Dónde | Archivo |
|---|---|---|---|
| 1 | Canal de correo creado | Monitoring › Alertas › Canales de notificación | `capturas/01-canal-correo.png` |
| 2 | Formulario de la comprobación de la API con la prueba en verde | Comprobaciones de tiempo de actividad › Crear | `capturas/02-crear-comprobacion.png` (y `02b`, `02c`, `02d`) |
| 3 | Las dos comprobaciones en verde desde todas las regiones | Comprobaciones de tiempo de actividad | `capturas/03-comprobaciones.png` |
| 4 | Política de errores 5xx creada (y sus pasos en `04a`, `04b`) | Monitoring › Alertas | `capturas/04-politica-5xx.png` |
| 5 | Panel de métricas de `trackva-api` (peticiones, latencia, instancias) | Cloud Run › `trackva-api` › Observabilidad | `capturas/05-metricas-api.png` (pendiente) |

## 6. Cómo deshacerlo

Borrar las políticas, las comprobaciones y el canal desde las mismas pantallas, en ese orden.

## 7. Diferencias con el diseño y pendientes

- El diseño menciona alertas sobre peticiones bloqueadas por Cloud Armor; se deja para cuando
  las reglas de ataques web salgan de vista previa.
- La web no envía errores a Sentry ni eventos a PostHog: el código no los tiene todavía.
- No hay tablero propio: se usan los de Cloud Run y del balanceador que trae la consola.
