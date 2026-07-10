---
name: vacantes-linkedin-jobfinder
description: >
  Arma la plataforma de vacantes de LinkedIn para un candidato de Job Finder,
  a partir de su CV optimizado. Úsalo cuando el admin quiera: buscar vacantes
  de LinkedIn para un candidato, armar/generar el vacantes_{nombre}.json que
  exige la sección "Subir vacantes.json" del panel admin, o procesar una
  solicitud de búsqueda de empleo. Se activa con frases como "arma la
  plataforma de vacantes", "busca vacantes de LinkedIn para este candidato",
  "generame el vacantes.json", "procesa esta solicitud de vacantes". El input
  ideal es `cv_optimizado_{nombre}.zip` (CV optimizado + analysis.json,
  generado por el skill cv-optimizer-jobfinder), pero también acepta el
  `.docx` del CV optimizado suelto -- el skill detecta el formato solo.
  Requiere navegación real de LinkedIn en Chrome (herramientas tipo
  claude-in-chrome: navigate, get_page_text, computer, find).
---

# Vacantes LinkedIn — Job Finder (búsqueda real + vacantes_{nombre}.json)

Este skill reemplaza el proceso manual de `backend/schemas/prompt_para_claude_vacantes.md`
(copiar y pegar vacantes encontradas a mano): navega LinkedIn Jobs en Chrome
para el perfil del candidato, arma un ranking honesto de vacantes reales, y
genera directamente el `vacantes_{nombre}.json` con el esquema exacto que
necesita `/vacantes.html`.

## Output obligatorio

Este skill genera exactamente **un archivo JSON**, usando el **primer nombre
del postulante en minúsculas y sin tildes** como parte del nombre:

| Archivo | Formato | Descripción |
|---|---|---|
| `vacantes_{nombre}.json` | JSON | Vacantes rankeadas con stats, Top 5 y notas de estrategia |

Ejemplo: postulante "Andrés García" → `vacantes_andres.json`.
El archivo se guarda en el mismo directorio que el archivo de entrada (ver
"Directorio de salida" en el Paso 1).
El admin lo sube manualmente desde `/admin`, sección "Subir vacantes.json".

**A diferencia de un generador de informe HTML**, acá no se genera ningún
HTML: la plataforma (`vacantes.html` + `vacantes.js` + `vacantes.css`) ya
sabe renderizar todo (sidebar de categorías, stats, tabla Top 5, cards,
filtros, notas de estrategia) a partir del JSON — este skill solo tiene que
producir datos correctos, nunca maquetación.

## Por qué el JSON tiene este esquema exacto

`POST /api/admin/{session_id}/vacantes` (`backend/app.py`) solo valida que
el JSON tenga una clave `"vacantes"`. Pero `vacantes.js` (frontend) además
lee `candidato.nombre`, `stats.*`, `top5_ids` y `notas_estrategia` para
pintar toda la pantalla — por eso el JSON de este skill incluye esos campos,
y **no** incluye `session_id`, `generado_el`, `candidato.cargo_objetivo` ni
`candidato.pais` (existen en el prompt manual viejo, pero no se renderizan
en ningún lado).

`categoria` debe ser **exactamente** uno de estos 5 valores (los soporta
`CATEGORY_META` en `frontend/vacantes.js`):
```
alta_relevancia | ventaja_interna | remoto_latam | media | especializado
```
Una vacante con `categoria` mal escrita o fuera de esta lista **desaparece
silenciosamente** de la plataforma (se cuenta en las stats pero no aparece
en ninguna sección) — verificalo siempre antes de entregar.

---

## Input requerido

Pedí al admin la ruta del archivo si no la dio. El input esperado es
`cv_optimizado_{nombre}.zip` (el que genera `cv-optimizer-jobfinder` en su
Paso 9), pero también acepta el `.docx` del CV optimizado suelto para usos
ad hoc.

El CV original no hace falta en ningún caso — no es un input de este skill.

---

## Paso 1 — Extraer el contenido del CV optimizado

**Caso A — el admin dio un `.zip` (`cv_optimizado_{nombre}.zip`):**

1. Descomprimilo a una carpeta temporal:
   ```bash
   python3 -m zipfile -e /ruta/a/cv_optimizado_andres.zip /tmp/cv_extraido/
   ```
2. Adentro vas a encontrar dos archivos fijos (los pone
   `cv-optimizer-jobfinder` en su Paso 9): `cv_optimizado_{nombre}.docx` y
   `analysis_{nombre}.json`.
3. Extraé el texto del CV:
   ```bash
   pandoc /tmp/cv_extraido/cv_optimizado_{nombre}.docx -t plain
   ```
4. Parseá `analysis_{nombre}.json` y guardá su campo `roles_objetivo`
   (lista de títulos, ya en orden de prioridad cuando el candidato eligió
   puestos) — lo usás en el Paso 2.

**Caso B — el admin dio el `.docx` suelto (sin zip):**

```bash
pandoc /ruta/al/CV_optimizado.docx -t plain
```

No hay `roles_objetivo` disponible: seguí sin él (Paso 2 se apoya solo en
lo que infiera del CV), salvo que el admin te haya pasado igual el
`analysis_{nombre}.json` por separado o te haya mencionado puestos
objetivo en el chat.

**Directorio de salida:** `vacantes_{nombre}.json` (Paso 7) se guarda en
el directorio donde está el archivo que te dio el admin (el zip o el
`.docx` suelto) — no en la carpeta temporal de extracción del Caso A.

**En ambos casos**, obtené del texto extraído:
- Nombre completo y título profesional / headline.
- Ubicación (ciudad/país) — define el radio de búsqueda local en LinkedIn.
- Resumen profesional y años totales de experiencia.
- Experiencia laboral: empresa, cliente(s), cargo, fechas, funciones y
  logros de cada rol. Prestá especial atención a **empresas donde ya
  trabajó** — generan la categoría "ventaja_interna" si tienen vacantes
  abiertas hoy.
- Habilidades técnicas: metodologías, herramientas, ERP/CRM.
- Certificaciones, con año.
- Idiomas y nivel.
- Formación académica.

No uses ningún dato que no esté en el CV o que no hayas verificado en la
propia vacante de LinkedIn.

Si `pandoc` no extrae texto útil, pedí al admin el `.pdf`/`.docx` del CV
optimizado de nuevo, o el original.

---

## Paso 2 — Definir términos de búsqueda

**Si tenés `analysis_{nombre}.json`:** los títulos de `roles_objetivo` son
el punto de partida obligatorio de la lista de términos — en particular
los que el candidato eligió (los que están primero en la lista, ver el
skill `cv-optimizer-jobfinder`). Buscalos literalmente en LinkedIn aunque
no coincidan con el headline actual del CV optimizado: el candidato
declaró explícitamente que quiere postular a esos puestos, así que no es
opcional incluirlos.

A partir de `roles_objetivo` (si existe) y del headline, los cargos
ocupados y las habilidades del CV optimizado, construí 6-10 términos de
búsqueda combinando:

- Los títulos de `roles_objetivo`, tal cual están escritos.
- Títulos exactos del CV (si dice "Delivery Manager", buscá literalmente eso).
- Sinónimos/variantes usadas en el mercado local (ej. "Project Manager",
  "Jefe de Proyecto", "PMO", "Gerente de Proyectos TI") — descubrilos
  iterando: si un término da 0-3 resultados, probá variantes.
- Nombres de empresas donde la persona ya trabajó (para detectar vacantes
  abiertas ahí → categoría `ventaja_interna`).
- Herramientas o certificaciones distintivas si son relevantes para un
  nicho (ej. "Salesforce CRM", "SAP", "Scrum Master").

Definí también los ámbitos geográficos: ciudad del CV (híbrido/presencial)
y "remoto" a nivel de la región del candidato (ej. LATAM).

Si el CV no indica ciudad o país, preguntale al admin antes de definir el
alcance geográfico.

---

## Paso 3 — Navegar LinkedIn Jobs (Chrome)

Usá las herramientas de control de navegador disponibles en la sesión
(`navigate`, `get_page_text`, `computer`, `find`, `browser_batch` o
equivalentes). Si no están disponibles en esta sesión en particular, avisá
al admin y pedile que te pegue el texto crudo de las vacantes encontradas
a mano en el chat, en vez de intentar sortear la falta de la herramienta.

1. Andá a `https://www.linkedin.com/jobs/search/?keywords=<termino>&location=<ciudad>&f_TPR=r604800`
   (última semana) para cada término del Paso 2. Repetí sin `f_TPR` si hay
   pocos resultados.
2. Repetí con `location=<región remota>` (ej. "Latin America") para roles remotos.
3. Para cada búsqueda, leé la lista de resultados con `get_page_text` y
   anotá: título, empresa, ubicación, modalidad.
4. Para las vacantes candidatas (match razonable con el CV), abrí cada una
   y capturá con `get_page_text` el detalle completo (requisitos, funciones,
   beneficios) y el `id` de la URL — la URL pública es
   `https://www.linkedin.com/jobs/view/<id>/`.
5. Capturá también, cuando esté visible: tiempo de publicación, número de
   solicitudes, si es "Solicitud sencilla".

---

## Paso 4 — Regla crítica: NO excluir vacantes por su estado de postulación en la cuenta usada para navegar

La navegación se hace con **la cuenta de LinkedIn conectada en el
navegador**, que casi nunca es la cuenta del candidato del CV. El estado de
postulación que LinkedIn muestra (p. ej. "Ya postulaste") refleja el
historial de **esa cuenta**, no el del candidato. Por lo tanto:

- **Nunca excluyas una vacante por aparecer marcada como "Ya postulaste"**
  u otro indicador de postulación previa — incluila igual si por lo demás
  es relevante.
- El único motivo válido para excluir una vacante es que no sea relevante
  para el perfil (o esté cerrada/expirada) — nunca su estado de postulación
  en la cuenta del navegador.
- **Esto es una regla interna del proceso, no un dato para el JSON.** Nunca
  incluyas en `descripcion_corta`, `notas_estrategia` ni ningún otro campo
  ninguna mención a la cuenta usada para navegar ni al estado de
  postulación observado.

---

## Paso 5 — Clasificar las vacantes

Cada vacante va a **una sola** de estas 5 categorías (los únicos valores
válidos de `categoria`, ver arriba):

- `alta_relevancia` — título casi idéntico al del CV, en la ciudad del candidato.
- `ventaja_interna` — vacante en una empresa donde el candidato ya trabajó.
- `remoto_latam` — vacante remota en la región del candidato.
- `media` — rol relacionado pero con menor coincidencia de seniority o alcance.
- `especializado` — requiere una herramienta o sector específico no
  confirmado en el CV, pero con metodología transferible.

Si una vacante exige un nivel de seniority claramente distinto al del CV, o
un dominio del que no hay evidencia, incluila igual en la categoría que más
se acerque, y explicá la brecha en `descripcion_corta`.

---

## Paso 6 — Redactar cada `descripcion_corta`

Para cada vacante, 2-4 líneas que:
- Citen 1-2 requisitos textuales de la vacante.
- Conecten esos requisitos con evidencia concreta del CV (empresa, cliente,
  años, certificación) — nunca una afirmación genérica sin respaldo.
- Mencionen honestamente las brechas si las hay.
- Si la vacante es `ventaja_interna`, mencioná la conexión previa con la
  empresa acá (es el único lugar donde ese ángulo se comunica — no hay un
  campo aparte para eso).

---

## Paso 7 — Generar `vacantes_{nombre}.json`

Escribí, en el directorio de salida definido en el Paso 1, el archivo
`vacantes_{nombre}.json` (donde `{nombre}` es el primer nombre del postulante
en minúsculas y sin tildes, ej: `vacantes_andres.json`) con **exactamente**
este esquema (sin `session_id`, `generado_el`, `candidato.cargo_objetivo`
ni `candidato.pais`):

```json
{
  "candidato": { "nombre": "" },
  "stats": {
    "total_vacantes": 0,
    "publicadas_hoy": 0,
    "remotas": 0,
    "solicitud_sencilla": 0
  },
  "top5_ids": ["job_001", "..."],
  "notas_estrategia": "",
  "vacantes": [
    {
      "id": "job_001",
      "titulo": "",
      "empresa": "",
      "ubicacion": "",
      "modalidad": "Remoto | Híbrido | Presencial",
      "fecha_publicacion": "YYYY-MM-DD",
      "es_nuevo_24h": true,
      "num_solicitudes": 0,
      "solicitud_sencilla": true,
      "url": "https://www.linkedin.com/jobs/view/...",
      "descripcion_corta": "",
      "categoria": "alta_relevancia",
      "match_porcentaje": 0
    }
  ]
}
```

Reglas:
- `stats.*` se recalculan siempre a partir de las vacantes reales
  encontradas en esta ejecución — nunca copiadas de una corrida anterior.
- `top5_ids`: elegí las 5 mejores vacantes (cualquier categoría) por
  relevancia real para el perfil.
- `notas_estrategia`: 2-4 oraciones de estrategia de postulación
  personalizada (prioridades del día, ángulo para las `ventaja_interna`,
  keywords ATS sugeridas, hallazgos del mercado). Sin mencionar la cuenta
  de navegación ni estados de postulación (ver Paso 4).
- No inventes datos que no estén verificados en LinkedIn — si no tenés
  `num_solicitudes` o `fecha_publicacion` exacta, usá `null`.
- `url` debe ser el link real de la vacante — si no se pudo abrir el
  detalle individual, enlazá a la búsqueda filtrada por esa empresa y
  aclaralo en `descripcion_corta`.
- `id` único por vacante (`job_001`, `job_002`, ...).

**Nombre del archivo:** `vacantes_{nombre}.json` (primer nombre en minúsculas
y sin tildes), guardado en el directorio de salida del Paso 1.
Ejemplo: "Andrés García" → `vacantes_andres.json`.

---

## Paso 8 — Verificación final antes de entregar

- Confirmá que cada `categoria` es exactamente uno de los 5 valores
  permitidos — cualquier otro valor hace que la vacante desaparezca de la
  plataforma sin error visible.
- Confirmá que cada `url` tiene el formato
  `https://www.linkedin.com/jobs/view/<id>/` y corresponde a un `id` real
  capturado durante la navegación.
- Confirmá que ninguna cifra de `stats` es inventada (contá las vacantes
  reales del JSON).
- Confirmá que no excluiste ninguna vacante relevante solo por aparecer
  marcada como "ya postulada" en la cuenta usada para navegar.
- Confirmá que el JSON final no menciona la cuenta de navegación ni el
  estado de postulación observado en ningún campo.
- Validá que el JSON es válido (parsea sin errores).

---

## Paso 9 — Reportar en el chat y subir al panel

Reportá en el chat: cuántas vacantes se encontraron por categoría, cuáles
son las Top 5, y cualquier término de búsqueda que no dio resultados (útil
para `notas_estrategia`).

Este skill **no sube nada a la API directamente**. Recordale al admin que
tiene que ir a `/admin`, a la tarjeta de esa solicitud, sección "Subir
vacantes.json", y subir ahí el archivo `vacantes_{nombre}.json` generado.

---

## Notas importantes

- Esta instrucción es agnóstica del candidato: sirve para cualquier CV
  optimizado, no para uno en particular.
- Si LinkedIn requiere iniciar sesión o la cuenta conectada no tiene
  acceso, informá al admin en vez de intentar sortear el bloqueo.
- Si el CV optimizado ya trae poca info (CV muy corto), decilo — no
  inventes experiencia ni empresas para llenar categorías.
