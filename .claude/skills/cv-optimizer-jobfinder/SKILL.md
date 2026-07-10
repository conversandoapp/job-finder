---
name: cv-optimizer-jobfinder
description: >
  Optimizador de CVs con scoring ATS para el flujo de admin de Job Finder. Úsalo
  cuando el admin quiera: optimizar el CV de un candidato para el panel
  (/admin), generar los dos outputs que exige la sección "Subir CV
  optimizado" del panel (cv_optimizado_{nombre}.docx y analysis_{nombre}.json),
  o puntuar un CV para un rol objetivo. Se activa con frases como "optimiza
  este CV para el panel", "generame el analysis_json de este candidato",
  "puntúa este CV", "procesa esta solicitud de CV". El input ideal es
  `postulacion.zip` (CV + puestos elegidos por el candidato, descargado desde
  `/admin`), pero también acepta un PDF o Word (.docx) suelto -- el skill
  detecta el formato solo.
---

# CV Optimizer — Job Finder (scoring ATS + outputs con nombre del postulante)

Este skill reemplaza el proceso manual de `backend/schemas/prompt_para_claude_cv_analysis.md`
(copiar y pegar un prompt en el chat web de Claude): lee el CV del candidato,
identifica los roles objetivo, lo puntúa como un ATS, aplica mejoras de
keywords y estructura **sin inventar información**, y genera los **dos outputs
obligatorios** listos para subir al panel admin.

## Outputs obligatorios

Este skill genera exactamente **dos archivos**, usando el **primer nombre del
postulante en minúsculas** como parte del nombre (por ejemplo, si el
postulante se llama "Andrés García", `{nombre}` = `andres`):

| Archivo | Formato | Descripción |
|---|---|---|
| `cv_optimizado_{nombre}.docx` | Word (.docx) | CV mejorado, ATS-friendly, listo para subir |
| `analysis_{nombre}.json` | JSON | Análisis ATS con scores, roles, keywords y debilidades |

Ambos se guardan en el mismo directorio que el CV de entrada.
El admin los sube manualmente desde `/admin`, sección "Subir CV optimizado".

## Por qué el JSON tiene este esquema exacto

El endpoint `POST /api/admin/{session_id}/cv` (`backend/app.py`) valida que
el JSON tenga estas 5 claves, ni una más ni una menos:

```
ats_score_original, ats_score_optimizado, roles_objetivo,
keywords_agregados, debilidades
```

`resultado.js` (frontend) solo lee esas 5 claves para pintar los círculos de
score, las keywords, las debilidades y las tarjetas de roles — cualquier otro
campo no se usa en ningún lado, así que el JSON de este skill es minimalista
a propósito.

## Setup

El directorio base del skill contiene:
- `scripts/extract_cv.py` — extractor de texto para PDF y DOCX

Dependencias necesarias en el entorno:
- `pdfplumber` (pip) — extracción de texto de PDF
- `pandoc` — extracción de texto de DOCX
- `unzip` o `python3 -m zipfile` — descomprimir `postulacion.zip`
- paquete npm `docx` (`npm install -g docx`) — generación del .docx de salida
- `python3`, `node`

---

## Paso 1 — Identificar el archivo de entrada

Pedí al admin la ruta del archivo si no la dio. El input esperado desde el
panel admin es `postulacion.zip` (botón "📦 Descargar CV + puestos (.zip)"
en `/admin`), pero también acepta un `.pdf`/`.docx`/`.doc` suelto para usos
ad hoc fuera del flujo del panel (ej. "puntuá este CV para tal rol").

**Caso A — el admin dio un `.zip`:**

1. Descomprimilo a una carpeta temporal:
   ```bash
   python3 -m zipfile -e /ruta/a/postulacion.zip /tmp/postulacion_extraida/
   ```
2. Adentro vas a encontrar dos archivos fijos (los pone
   `backend/services/packaging.py`): `cv_original.<ext>` y
   `puestos_candidato.json`.
3. Extraé el texto del CV como siempre:
   ```bash
   python3 <skill_base>/scripts/extract_cv.py /tmp/postulacion_extraida/cv_original.<ext>
   ```
4. Leé `puestos_candidato.json` — tiene esta forma:
   ```json
   { "modo": "candidato" | "admin", "roles": ["Puesto 1", "Puesto 2", "Puesto 3"] }
   ```
   Guardá `modo` y `roles`: los usás en el Paso 2. `roles` viene **en orden
   de prioridad** puesto por el candidato (el primero es el más importante),
   y está vacío cuando `modo == "admin"`.

**Caso B — el admin dio un `.pdf`/`.docx`/`.doc` suelto (sin zip):**

Extraé el texto igual que siempre:
```bash
python3 <skill_base>/scripts/extract_cv.py /ruta/al/cv.pdf
```
No hay `puestos_candidato.json` — tratalo como `modo == "admin"` con
`roles == []`, salvo que el admin te haya mencionado un rol objetivo
puntual en el chat (en ese caso, usá ese rol como si fuera `roles = [ese
rol]` con `modo == "candidato"`).

**En ambos casos:** guardá el texto extraído — es la **única fuente de
verdad** para todo el proceso. Nunca inventes, agregues ni infieras
información que no esté explícita en este texto.

**Directorio de salida:** los outputs del Paso 7 y 8 se guardan siempre en
el mismo directorio donde está el archivo que te dio el admin (el
`postulacion.zip` o el CV suelto) — **no** en la carpeta temporal de
extracción del Caso A, que es descartable.

Si `extract_cv.py` devuelve una advertencia de texto vacío (PDF escaneado
como imagen), avisá al admin y pedile la versión en texto o el .docx
original — no sigas con texto vacío.

---

## Paso 2 — Identificar roles objetivo

**Si `modo == "candidato"` y `roles` tiene al menos un puesto** (el caso
normal cuando viene de `postulacion.zip`): esos son los roles objetivo,
no los inventes de cero.

1. Los puestos de `roles` van primero en `roles_objetivo`, **en el mismo
   orden de prioridad que puso el candidato**. `roles[0]` es el rol
   **#1 ⭐ — el que se usa en el Paso 3 para el score "antes/después",
   siempre, sin reordenar por mejor match** (aunque el match real sea
   bajo: el punto es mostrar honestamente qué tan lejos está el CV actual
   de ese objetivo).
2. Si el candidato dio menos de 3 puestos, completá la lista hasta 4-6
   roles totales **infiriendo del CV** con el mismo criterio de siempre
   (cargos ocupados, sectores, skills, certificaciones, años de
   experiencia), evitando duplicar los que el candidato ya puso. Estos
   inferidos van **después** de los elegidos por el candidato.
3. Mostrá la lista al admin distinguiendo el origen de cada uno, y
   **continuá inmediatamente** sin esperar respuesta:

```
Roles identificados (continuando con el proceso):
1. Product Owner Senior 🎯 elegido por el candidato ⭐ (score ATS se calcula contra este rol)
2. Product Manager 🎯 elegido por el candidato
3. Scrum Master 🎯 elegido por el candidato
4. IT Project Coordinator 🤖 sugerido por match con el CV
→ El score se calcula contra el puesto #1 que eligió el candidato.
```

**Si `modo == "admin"` (el candidato prefirió que elijan) o no hay
`puestos_candidato.json`:** comportamiento de siempre — con el texto
extraído, identificá entre 4 y 6 puestos a los que el candidato podría
postular realistamente, según:
- Cargos ocupados (título exacto y seniority)
- Sectores/industrias mencionados
- Habilidades técnicas y herramientas listadas
- Certificaciones y nivel educativo
- Años de experiencia

Ordená de mayor a menor match (mejor match primero) y marcá el primero
con ⭐ — ese rol #1 (el de mejor match) es el que se usa en el Paso 3.
Mostrá la lista al admin como notificación y **continuá inmediatamente**
sin esperar respuesta — si el admin quiere cambiar el orden, puede
avisarte y se recalcula, pero el proceso no se detiene.

```
Roles identificados (continuando con el proceso):
1. Product Owner Senior ⭐ (score ATS se calcula contra este rol)
2. Product Manager
3. Scrum Master
4. IT Project Coordinator
→ El candidato prefirió que elijamos nosotros; si querés ajustar el orden, avisame.
```

---

## Paso 3 — Scoring ATS (contra el rol #1 únicamente)

A diferencia de un análisis genérico multi-rol, el panel admin solo tiene
espacio para **un** score "antes" y **un** score "después" — no uno por
rol. Por eso el score se calcula **una sola vez, contra el rol #1**
confirmado en el Paso 2 — ya sea el puesto que el candidato eligió como
prioridad #1, o el de mejor match inferido del CV cuando no hay elección
del candidato. Los demás roles de la lista siguen apareciendo en
`roles_objetivo` (con su propio `match_porcentaje`, que es distinto del
score ATS), pero no se puntúan individualmente.

Rubric (100 pts totales), aplicado pensando en el rol #1:

| Categoría | Pts máx | Qué revisar |
|---|---|---|
| Match de keywords | 30 | Cuántas keywords del rol #1 aparecen (títulos, herramientas, metodologías, términos de dominio) |
| Verbos de acción | 15 | Verbos fuertes al inicio de los bullets (Lideré, Implementé, Desarrollé, Gestioné…) |
| Estructura y legibilidad | 15 | Secciones claras, fechas consistentes, sin tablas/columnas en el cuerpo |
| Resultados cuantificables | 15 | Números, porcentajes, indicadores de escala |
| Sección de skills relevante | 15 | Herramientas técnicas, metodologías y soft skills listadas explícitamente |
| Longitud y densidad | 10 | 1-2 páginas óptimo; ni muy vacío ni sobrecargado |

Esto da `ats_score_original`. Anotá también qué categorías pierden más
puntos y qué keywords del rol #1 faltan — esa info alimenta
`debilidades` y `keywords_agregados` más adelante.

---

## Paso 4 — Planificar y aplicar mejoras (sin pausa)

Identificá internamente qué mejoras son posibles con la información
disponible en el CV y **aplicalas directamente** en el Paso 5, sin pedir
confirmación. Clasificá cada mejora posible en una de estas dos categorías:

**✅ Se puede implementar** (la información ya existe en el CV):
- Agregar la keyword X naturalmente al bullet Y de la empresa Z
- Reemplazar verbo débil "Responsable de" → "Lideré"
- Agregar skills faltantes a la sección de habilidades
- Fusionar bullets duplicados para liberar espacio
- Reorganizar secciones para mejor legibilidad ATS
- Agregar Perfil Profesional / tagline si no existe (redactado con info del CV)
- Crear sección Habilidades Técnicas con herramientas ya mencionadas en la experiencia

**❌ No se puede implementar** (requiere información que el candidato no puso en el CV):
- Agregar métricas o logros cuantificables (no hay números en el original)
- Agregar certificaciones que el candidato no tiene
- Agregar experiencia en una tecnología no mencionada
- Subir el título de un cargo por encima de lo que dice el CV
- Agregar estudios no mencionados
- Agregar sección de Idiomas (si no están mencionados en ningún lado)

Los ítems ❌ se reportan en `debilidades` del JSON (ver Paso 8) y se listan
en el resumen final del chat (ver Paso 9). **No interrumpas el proceso para
pedir confirmación del plan** — aplicá todo lo posible y avanzá.

---

## Paso 5 — Aplicar mejoras

Aplicá solo los ítems ✅. Regla cardinal: cada palabra del CV mejorado
tiene que poder rastrearse al texto original extraído o a información que
el admin dio explícitamente en la conversación. Sin excepciones.

Cambios permitidos:
- Reformular bullets para incluir keywords faltantes de forma natural
- Reemplazar verbos débiles por verbos de acción fuertes
- Reordenar bullets dentro de un puesto para que el más fuerte vaya primero
- Agregar a Habilidades keywords relevantes que ya están mencionadas en la
  experiencia
- Ajustar formato (orden de secciones, espaciado)
- Fusionar bullets casi duplicados para ahorrar espacio

Cambios prohibidos:
- Inventar métricas, porcentajes o cifras que no estén en el original
- Agregar empresas, cargos o fechas que no estén en el original
- Afirmar certificaciones o estudios que no estén en el original
- Agregar herramientas o tecnologías no mencionadas en ningún lado del CV

---

## Paso 6 — Re-puntuar el CV mejorado

Aplicá exactamente el mismo rubric del Paso 3, contra el mismo rol #1, al
CV ya mejorado. Esto da `ats_score_optimizado`. Sé honesto: si una mejora
no mueve la aguja en una categoría, no infles el número.

---

## Paso 7 — Generar el .docx optimizado

Generá un script de Node.js (con el paquete npm `docx`) que produzca el CV
mejorado como `.docx` ATS-friendly:

**Reglas de layout:**
- Texto plano — sin tablas laterales, sin cuadros de texto flotantes
- Fuente: Calibri 11pt cuerpo, 14pt nombre, 11pt encabezados de sección
- Página: Carta US (12240 × 15840 DXA), márgenes de 1" en todos los lados
- Encabezados de sección: negrita, con línea fina inferior, sin color de fondo
- Listas con viñetas: `LevelFormat.BULLET` con numbering config (nunca • unicode en TextRun)
- Tabulaciones para alinear fechas a la derecha en la misma línea que el cargo
- Sin imágenes, sin rellenos de color, sin tablas en el cuerpo

**Secciones en orden:**
1. Nombre (grande, negrita)
2. Título profesional / tagline
3. Datos de contacto (teléfono, email, LinkedIn, ciudad) — todo en una línea
4. Perfil Profesional
5. Experiencia Profesional (orden cronológico inverso)
6. Habilidades Técnicas
7. Formación Académica
8. Certificaciones
9. Idiomas
10. Referencias (si están en el original)

**Nombre del archivo de salida:** `cv_optimizado_{nombre}.docx`, donde
`{nombre}` es el **primer nombre del postulante en minúsculas y sin tildes**
(ejemplo: postulante "Andrés García" → `cv_optimizado_andres.docx`).
Se guarda en el mismo directorio que el archivo de entrada.

Escribí el script en una ruta temporal, corré con `node`, y copiá el
resultado al directorio de salida.

Si el paquete `docx` no está instalado globalmente:
```bash
npm install -g docx
```

**Seguridad de bytes nulos:** siempre pasá los scripts por `tr -d '\0'`
antes de ejecutarlos:
```bash
tr -d '\0' < generate_cv.js > generate_cv_clean.js && node generate_cv_clean.js
```

---

## Paso 8 — Generar `analysis_{nombre}.json`

Generá, en el mismo directorio que el CV de entrada, el archivo
`analysis_{nombre}.json` (mismo `{nombre}` usado en el Paso 7, ej:
`analysis_andres.json`) con **exactamente** estas 5 claves (sin `session_id`,
`resumen` ni `cv_reescrito` — no los usa el frontend, ver la nota de arriba):

```json
{
  "ats_score_original": 0,
  "ats_score_optimizado": 0,
  "roles_objetivo": [
    { "titulo": "", "justificacion": "", "match_porcentaje": 0 }
  ],
  "keywords_agregados": ["..."],
  "debilidades": ["..."]
}
```

Reglas:
- `ats_score_original`/`ats_score_optimizado`: del Paso 3 y Paso 6, ambos
  contra el rol #1.
- `roles_objetivo`: la lista completa confirmada en el Paso 2. Si vienen
  puestos elegidos por el candidato, esos van primero (en su orden de
  prioridad), seguidos de los inferidos del CV; si no, ordená de mayor a
  menor `match_porcentaje` (el `match_porcentaje` es el fit al rol, no el
  score ATS). En `justificacion`, para los puestos que eligió el
  candidato, decilo explícitamente (ej. "Puesto elegido por el candidato
  como prioridad #1" en vez de solo justificar el match) — así queda
  trazable de dónde salió cada entrada, sin agregar campos nuevos al JSON.
- `keywords_agregados`: las keywords que el CV mejorado tiene y el
  original no tenía.
- `debilidades`: limitaciones **reales del perfil del candidato** que no
  pueden resolverse solo con mejor redacción — son cosas que el candidato
  tendría que hacer en su carrera o vida real para mejorar su CV en el
  futuro. Incluí tanto lo que detectó el rubric ATS (Paso 3) como los
  ítems ❌ del Paso 4. Ejemplos típicos:
  - "No tiene métricas ni logros cuantificables en ningún rol"
  - "Falta formación académica formal en el área de su rol objetivo"
  - "No menciona certificaciones relevantes (ej. PMP, Scrum, etc.)"
  - "Sin experiencia documentada en [tecnología clave del rol #1]"
  - "No incluye idiomas — si habla inglés u otro, debería agregarlo"
  Escribilos como recomendaciones accionables para el candidato, no como
  críticas al CV redactado.

---

## Paso 9 — Reportar en el chat

Después de generar ambos archivos, reportá:

### 🎯 Puesto contra el que se calculó el score
Una línea aclarando el origen: "El score se calculó contra '<rol #1>', el
puesto que el candidato eligió como prioridad" o, si no eligió puesto,
"...el puesto que mejor matchea según su CV".

### ✅ Mejoras aplicadas
Cada cambio concreto, agrupado por sección.

### ❌ Recomendaciones que no se pudieron implementar
Los ítems de la columna ❌, con una breve explicación de por qué y qué
necesitaría el candidato para poder aplicarlos.

### 📎 Archivos generados y próximo paso

Los dos outputs generados son:
- `cv_optimizado_{nombre}.docx` — CV optimizado en Word, ATS-friendly
- `analysis_{nombre}.json` — Análisis ATS con scores, roles, keywords y debilidades

Recordale al admin que todavía tiene que subir **ambos archivos** a mano desde
`/admin`, en la tarjeta de la solicitud correspondiente, sección
"Subir CV optimizado" — este skill no llama a la API directamente.

---

## Notas importantes

- Este skill opera enteramente sobre el texto extraído. No puede leer
  imágenes ni PDFs escaneados — si `extract_cv.py` devuelve texto vacío,
  avisá al admin y pedí una versión en texto o el `.docx` original.
- Si el CV ya es fuerte en algunas áreas, decilo — no cambies lo que no
  necesita cambiar.
- El objetivo es una mejora realista, no un CV teórico perfecto. Sé
  honesto sobre cuánto sube el score con los cambios aplicados.
- Nunca reveles ni uses el campo `session_id` en el JSON: no lo pide el
  endpoint, y el admin ya sube el archivo dentro de la tarjeta correcta en
  el panel.
