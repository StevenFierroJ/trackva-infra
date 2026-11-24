# 13 · CI/CD: GitHub Actions con Workload Identity Federation

| | |
|---|---|
| **Estado** | Configurado el 24-nov-2026 en los tres repositorios. Sin protección de rama (el plan de GitHub no la permite) |
| **Proyecto** | `trackva-dev` y los repositorios `trackva-api`, `trackva-web`, `trackva-integrations` |
| **Región** | `us-east4` |
| **ADR del diseño** | — (objetivo 3.2: despliegue automatizado de menos de 10 minutos, sin llaves de cuenta de servicio) |
| **Costo estimado** | US$0 en Google Cloud. En GitHub, los minutos de Actions del plan de la cuenta |

## 1. Para qué sirve en TrackVa

Hoy desplegar es manual: compilar la imagen con un comando y crear la revisión en la consola.
El pipeline hace lo mismo solo, en cada cambio que entra a `main`, y agrega dos cosas que a
mano no se hacen: revisar el código antes de fusionar y comprobar que la versión nueva responde
antes de darla por buena.

Automatiza exactamente los pasos que ya se probaron a mano en los servicios 02, 05, 06 y 07.

## 2. Qué resuelve además

| Pendiente | Cómo lo cierra el pipeline |
|---|---|
| `TRUST_PROXY` debe ser `2` detrás del balanceador (servicio 08) | La configuración no secreta de cada servicio pasa a vivir en el repositorio; el despliegue la aplica |
| El chequeo de aislamiento entre empresas no corre en cada cambio (R-42) | `npm run audit:tenant -- --check` como paso obligatorio de la API |
| `SENTRY_RELEASE` se actualiza a mano | Lo pone el pipeline con el SHA del commit |
| La imagen de la web depende de un guion local (`scripts/build-web.sh`) | Las variables públicas de la web quedan como variables del repositorio en GitHub |

## 3. Diseño

### 3.1 Dos flujos por repositorio

```
Pull request ─▶ CI: formato, lint, tipos, pruebas ─▶ (verde) se puede fusionar

Push a main ──▶ CI ─▶ imagen ─▶ Artifact Registry ─▶ revisión nueva en Cloud Run ─▶ prueba de salud
                                                                                       │
                                                                          falla ─▶ vuelve a la revisión anterior
```

| Flujo | Archivo | Se dispara con | Qué hace |
|---|---|---|---|
| CI | `.github/workflows/ci.yml` | Pull request y push a `main` | Revisa el código. No toca Google Cloud |
| Despliegue a develop | `.github/workflows/deploy-develop.yml` | Push a `main`, tras pasar el CI; también a mano | Compila, sube y despliega |

### 3.2 Pasos del CI por repositorio

| Paso | `trackva-api` | `trackva-web` | `trackva-integrations` |
|---|---|---|---|
| Instalar (`npm ci`) | Sí | Sí | Sí |
| Formato (`prettier --check`) | Sí | Sí (`format:check`) | Sí |
| Lint (sin `--fix`) | Sí | Sí | Sí |
| Tipos (`tsc --noEmit`) | Sí | Sí | Sí |
| Pruebas unitarias | `jest` (174 archivos) | `vitest run` (133 archivos) | `jest` |
| Aislamiento entre empresas | `audit:tenant --check` | — | — |
| Diccionarios de idioma | — | `i18n:check-shared` e `i18n:check-keys` | — |
| Pruebas de integración (base real con contenedores) | Ver decisión P3 | — | — |
| Pruebas E2E con Playwright | — | Fuera del pipeline por ahora | — |

Hoy los guiones `lint` de la API y de integraciones llevan `--fix`, que corrige en vez de
avisar. En el CI se corre el mismo linter sin esa opción.

### 3.3 Pasos del despliegue

1. **Autenticarse en Google Cloud sin llaves** (3.4).
2. **Compilar la imagen** en el propio corredor de GitHub, con caché de capas, y etiquetarla con
   el SHA corto del commit. Los corredores son `linux/amd64`, que es lo que exige Cloud Run.
3. **Subirla** a `us-east4-docker.pkg.dev/trackva-dev/trackva-dev/<servicio>:<sha>`.
4. **Desplegar** la revisión nueva en Cloud Run, con la imagen y la configuración no secreta
   del archivo del repositorio (3.5). Cloud Run solo le da tráfico si arranca.
5. **Probar** por el dominio: `/api/v1/health` para la API, `/login` para la web, y
   `/api/v1/health/integrations` para integraciones (con un reintento, por el arranque en frío).
6. **Si la prueba falla,** devolver el 100 % del tráfico a la revisión anterior y marcar el
   despliegue en rojo.

Se compila en GitHub y no en Cloud Build porque el corredor ya tiene Docker, guarda caché entre
ejecuciones y evita darle a la cuenta de despliegue permisos sobre Cloud Build.

### 3.4 Identidad: Workload Identity Federation

GitHub demuestra a Google quién es con un token de corta duración que emite en cada ejecución.
Google lo cambia por credenciales temporales de la cuenta de despliegue. No se crea ni se guarda
ninguna llave: no hay nada que robar ni que rotar.

| Recurso en `trackva-dev` | Nombre | Para qué |
|---|---|---|
| Grupo de identidades de carga de trabajo | `github` | Agrupa las identidades que vienen de GitHub |
| Proveedor OIDC | `github-actions` (emisor `https://token.actions.githubusercontent.com`) | Valida los tokens de GitHub. Con condición: solo repositorios del dueño `StevenFierroJ` |
| Cuenta de servicio | `trackva-github-deploy` | La identidad con la que el pipeline actúa |

Quién puede usar la cuenta de despliegue: solo los tres repositorios, y solo desde la rama
`main`. Un pull request, una rama o un repositorio ajeno no pueden desplegar.

Permisos de `trackva-github-deploy`, los mínimos:

| Rol | Sobre qué | Para qué |
|---|---|---|
| Escritor de Artifact Registry | El repositorio `trackva-dev` | Subir imágenes |
| Desarrollador de Cloud Run | Los tres servicios | Crear revisiones y mover tráfico |
| Usuario de cuenta de servicio | Las tres cuentas de ejecución | Desplegar servicios que corren con esas cuentas |

No puede leer secretos, ni tocar la red, el balanceador, Cloud Armor o IAM.

### 3.5 Dónde vive la configuración

| Tipo | Dónde | Ejemplo |
|---|---|---|
| Secretos | Secret Manager, como hoy. El pipeline no los ve | `DATABASE_URL`, llaves |
| Configuración no secreta de cada servicio | Un archivo en su repositorio, `deploy/develop.env` | `TRUST_PROXY=2`, `CORS_ORIGIN`, `LOG_LEVEL` |
| Variables públicas de la web (se fijan al compilar) | Variables del repositorio en GitHub, entorno `develop` | `NEXT_PUBLIC_API_URL`, llave anónima de Supabase, llave de Maps del navegador |
| Identificadores de Google Cloud | Variables del repositorio en GitHub | Proyecto, región, proveedor de identidad, cuenta de despliegue |

Con el archivo en el repositorio, un cambio de configuración pasa por pull request y queda en
el historial, en vez de hacerse a mano en la consola.

### 3.6 Lo que el pipeline no hace

| Tema | Por qué | Cómo queda |
|---|---|---|
| Migraciones de base de datos | La base de dev solo acepta la IP del NAT y la del equipo de desarrollo (servicio 11); los corredores de GitHub no tienen IP fija | Se siguen aplicando desde el equipo, antes de fusionar. Más adelante, un trabajo de Cloud Run dentro de la VPC |
| App móvil | Se publica por las tiendas, no en Cloud Run | Fuera de alcance |
| Infraestructura (red, balanceador, Cloud Armor) | Se configuró a mano y cambia poco | Sigue manual, documentada en esta carpeta |
| Producción | No existe todavía | Se agrega como un segundo flujo con aprobación manual (P5) |

## 4. Decisiones (aprobadas por Steven el 24-nov, «tú ejecutas todo»)

| # | Decisión | Resultado |
|---|---|---|
| P1 | Cada push a `main` despliega solo a develop | Hecho en los tres repositorios |
| P2 | CI obligatorio para fusionar | **No se pudo:** la protección de rama en repositorios privados exige GitHub Pro. El CI corre e informa, pero GitHub no impide fusionar en rojo. El despliegue sí depende del CI: un push con el CI en rojo no llega a develop |
| P3 | Pruebas de integración fuera del camino del despliegue | Hecho. A pedido de Steven también salieron de los pull request: corren cada noche si `main` cambió, y a mano |
| P4 | Configuración no secreta en el repositorio | Hecho: `deploy/develop.env` en la API y en integraciones. La web no tiene configuración de ejecución |
| P5 | Producción después | Sin cambios |
| P6 | Vuelta atrás automática | Implementada. **No se ha probado con un fallo real** |
| P7 | Identidad en Google Cloud | La creó Claude por `gcloud`, por indicación de Steven |

## 5. Qué contradice o extiende CLAUDE.md

| Sección | Qué dice hoy | Qué cambia |
|---|---|---|
| §2.bis, CI/CD | Decisión abierta: GitHub Actions con Workload Identity Federation | Se cierra para develop |
| §22 Definition of Done | Las comprobaciones se corren a mano antes del PR | Las corre el CI; el DoD puede remitir a él |
| §23.8 Git | Push a `main` con autorización por cada push | No cambia la regla, pero **cada push a `main` pasa a desplegar en develop**: conviene que conste |
| §5 Docker | Imágenes desde GitHub Container Registry y `docker-compose` por ambiente | Las imágenes van a Artifact Registry y el despliegue es Cloud Run |
| §17 Variables | Lista de variables por servicio | Se agrega dónde vive cada una (3.5) |

## 6. Lo que se hizo

### 6.1 Identidad en Google Cloud

```bash
gcloud iam workload-identity-pools create github --location=global --display-name="GitHub Actions"
gcloud iam workload-identity-pools providers create-oidc github-actions --location=global \
  --workload-identity-pool=github --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.repository_owner_id=assertion.repository_owner_id,attribute.ref=assertion.ref" \
  --attribute-condition="assertion.repository_owner_id=='168310457' && assertion.ref=='refs/heads/main'"
gcloud iam service-accounts create trackva-github-deploy
```

| Qué | Valor |
|---|---|
| Proveedor | `projects/1082495364/locations/global/workloadIdentityPools/github/providers/github-actions`, activo |
| Condición del proveedor | Solo el dueño de los repositorios (por su identificador numérico, no por nombre) y solo la rama `main` |
| Quién puede usar `trackva-github-deploy` | `StevenFierroJ/trackva-api`, `…/trackva-web`, `…/trackva-integrations` |
| Sus permisos | Escritor de Artifact Registry en `trackva-dev`; Desarrollador de Cloud Run en el proyecto; Usuario de cuenta de servicio sobre las tres cuentas de ejecución |

El rol de Cloud Run quedó en el proyecto y no por servicio, como decía el diseño: el proyecto
solo tiene esos tres servicios y así el despliegue no falla al consultar sus operaciones.

### 6.2 Variables en GitHub (no secretas)

En los tres repositorios: `GCP_PROJECT_ID`, `GCP_REGION`, `GCP_WIF_PROVIDER`, `GCP_DEPLOY_SA`,
`GCP_AR_PATH`, `DEV_DOMAIN`. En la web, además: `NEXT_PUBLIC_SUPABASE_URL`,
`NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_GOOGLE_MAPS_KEY`. Son variables del repositorio,
no de un entorno: los entornos de GitHub tampoco están en el plan gratuito para repositorios
privados. No hay ningún secreto en GitHub.

### 6.3 Flujos por repositorio

| Repositorio | PR | Archivos | Primer despliegue automático |
|---|---|---|---|
| `trackva-integrations` | #2 (`d9c8bef`) | `ci.yml`, `deploy-develop.yml`, `deploy/develop.env` | Revisión `trackva-integrations-00002-x7n` |
| `trackva-web` | #112 (`989feb2`) | `ci.yml`, `deploy-develop.yml` | Imagen `trackva-web:989feb2` |
| `trackva-api` | #115 (`1310785`) | `ci.yml`, `deploy-develop.yml`, `integration.yml`, `deploy/develop.env` | Revisión `trackva-api-00007-d5c` |

### 6.4 Tiempos medidos (primer despliegue, sin caché de capas)

| Repositorio | CI | Despliegue | Total | Meta de 10 min |
|---|---|---|---|---|
| `trackva-integrations` | 1 min 26 s | 3 min 27 s | ~5 min | Cumple |
| `trackva-web` | 4 min 05 s | 5 min 42 s | 9 min 54 s | Cumple, justo |
| `trackva-api` | 5 min 55 s | 6 min 33 s | 12 min 35 s | **No cumple** |

En la API, el CI se va en lint (1 min 30 s) y tipos sobre un corredor de 2 núcleos, y el
despliegue en compilar la imagen. Con la caché de capas ya guardada, los siguientes deberían
bajar; falta medirlo. Si no baja de 10 minutos, lo siguiente es no repetir el CI en el push a
`main` cuando ya pasó en el pull request.

### 6.5 `TRUST_PROXY=2`, aplicado y comprobado

Lo aplicó el despliegue de la API desde `deploy/develop.env`. Prueba con el contador del límite
de peticiones del rastreo público (30 por minuto):

```text
directa #1                               → quedan 29
directa #2                               → quedan 28
directa con X-Forwarded-For: 9.9.9.9     → quedan 27    (una IP inventada no cambia de contador)
4 páginas /track/… (la web consulta la API desde el servidor)
directa #3                               → quedan 26    (esas 4 consultas fueron a otro contador)
```

Antes, con `1`, todas las peticiones que llegaban por el balanceador caían en el mismo contador.
Ahora el visitante directo tiene el suyo y no se puede falsificar. Las consultas que hace la web
desde el servidor comparten el contador de la IP del NAT: es el caso pendiente de código que ya
estaba anotado en el servicio 08.

### 6.6 Hallazgos al encender el CI

| Hallazgo | Qué se hizo |
|---|---|
| **5 consultas sin filtro de empresa** según `audit:tenant --check`: `clients.repository.ts:197`, `contacts.repository.ts:268` y `:397`, `pickups.repository.ts:1155`, `wms/adjustments/adjustments.repository.ts:148` | Sin tocar: es multiempresa y pide revisión propia. El paso del CI quedó informativo (`continue-on-error`) hasta resolverlas |
| 3 errores de lint en pruebas de integración de la API | Corregidos en el PR #115 |
| La suite de integración agotaba la memoria de Node en el corredor (tras 44 de 101 archivos) | Ahora usa un solo proceso que se recicla; **no se ha visto pasar completa en GitHub** |
| Una prueba del portal dependía del orden de dos filas con identificadores aleatorios | Corregida en el PR #115 |
| `i18n:check-keys` falla en `main` (formas de plural) | Paso informativo en el CI de la web |
| `i18n:check-shared` falla en `main` (el `shared.json` de la web y el del móvil difieren) | No corre en el CI: necesita el repositorio del móvil al lado |
| 2 archivos de configuración de la web sin formato | Corregidos en el PR #112 |

## 7. Riesgos y cosas por comprobar

- **Vuelta atrás sin probar.** El paso existe, pero ningún despliegue ha fallado todavía. Se
  prueba fusionando a propósito una versión que no pase la prueba de salud.
- **Tiempo de la API.** Ver 6.4: el primer despliegue pasó de 10 minutos.
- **Minutos de GitHub Actions.** Los repositorios son privados y consumen la cuota del plan de
  la cuenta. No se ha comprobado cuánta cuota hay ni cuánto gasta cada ejecución.
- **Acciones con Node 20.** GitHub avisa que `actions/checkout@v4` y `actions/setup-node@v4`
  usan un Node retirado y las ejecuta con uno más nuevo. Funciona; conviene subirlas de versión.
- **Despliegues simultáneos.** Dos fusiones seguidas en el mismo repositorio deben encolarse y
  no pisarse: se resuelve con el grupo de concurrencia de Actions.
- **Cambios que necesitan migración.** Si se fusiona código que depende de una migración aún no
  aplicada, develop se rompe. El orden correcto sigue siendo: migración primero, fusión después.
