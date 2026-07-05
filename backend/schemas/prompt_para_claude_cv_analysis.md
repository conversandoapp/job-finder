# Prompt para generar `cv_analysis.json` con Claude

Este es el flujo manual del MVP para la etapa de "análisis y optimización de CV":

1. Entrás al panel admin (`/admin.html`), descargás el CV original de la
   solicitud (botón "📄 Descargar CV original").
2. Le pegás el texto del CV a Claude junto con el prompt de abajo.
3. Claude te devuelve un JSON con el análisis completo (scores, roles,
   keywords, debilidades) **y además el texto del CV ya reescrito y
   mejorado**, listo para que lo pegues en Word y lo guardes como `.docx`.
4. Subís dos archivos desde el panel admin, en la sección "Subir CV optimizado":
   - el `.docx` que armaste en Word con el texto reescrito
   - el `cv_analysis.json` que te devolvió Claude (sin tocarlo)

La página de resultado del usuario (`/resultado.html`) ya sabe leer ese JSON
y renderiza automáticamente los círculos de score ATS, las keywords, las
debilidades y los roles — no hace falta tocar HTML ni llenar campos sueltos
a mano.

---

## Prompt (copiar y pegar en Claude)

```
Eres un experto en recursos humanos y en optimización de CVs para sistemas ATS,
especializado en el mercado laboral latinoamericano. Conoces bien Perú, Colombia,
México, Chile y Argentina.

Te voy a pasar el texto completo de un CV. Tu tarea es hacer, en un solo paso,
todo este análisis:

1. EXTRAER el perfil: nombre, país, idiomas, años de experiencia, último cargo,
   industrias, herramientas, metodologías, certificaciones.

2. IDENTIFICAR 4 a 6 roles objetivo a los que esta persona podría postular,
   ordenados por probabilidad de éxito, considerando tanto roles locales como
   100% remotos para LATAM.

3. EVALUAR el CV original con un rubric ATS estricto (keywords, verbos de acción,
   estructura, resultados cuantificables, sección de skills, longitud) y calcular
   un score_total sobre 100.

4. REESCRIBIR el CV aplicando las recomendaciones del análisis ATS. Reglas
   absolutas para la reescritura:
   - No inventes información, logros, empresas, fechas ni certificaciones que
     no estén en el CV original.
   - No agregues métricas o porcentajes que no estén en el original.
   - Sí podés reformular bullets con verbos de acción más fuertes.
   - Sí podés reorganizar el orden de los elementos.
   - Sí podés agregar keywords evidentes del propio CV (ej: si dice "lideré 7
     equipos Scrum", podés agregar "Scrum Master" en skills).
   - Sí podés eliminar información irrelevante o personal (DNI, estado civil,
     fecha de nacimiento).
   - El output debe estar en el mismo idioma que el CV original.

5. ESTIMAR qué score ATS tendría el CV ya reescrito con el mismo rubric.

Devuelve SOLO un JSON válido (sin markdown, sin texto adicional) con esta
estructura exacta:

{
  "session_id": "<pegar aquí el session_id real>",
  "ats_score_original": 0,
  "ats_score_optimizado": 0,
  "resumen": "1-2 oraciones resumiendo el perfil y el principal hallazgo del análisis",
  "roles_objetivo": [
    { "titulo": "", "justificacion": "", "match_porcentaje": 0 }
  ],
  "keywords_agregados": ["..."],
  "debilidades": ["..."],
  "cv_reescrito": {
    "nombre": "",
    "tagline": "",
    "contacto": { "email": "", "telefono": "", "linkedin": "", "ciudad": "" },
    "resumen_profesional": "",
    "experiencia": [
      {
        "empresa": "", "cargo": "", "fecha_inicio": "", "fecha_fin": "",
        "modalidad": "", "descripcion": "", "logros": ["..."]
      }
    ],
    "educacion": [ { "institucion": "", "titulo": "", "anio": "" } ],
    "certificaciones": [ { "nombre": "", "institucion": "", "anio": "" } ],
    "habilidades": { "metodologias": [], "herramientas": [], "blandas": [], "idiomas": [] }
  }
}

Reglas:
- "keywords_agregados" son las palabras clave que el CV reescrito tiene y el
  original no tenía.
- "debilidades" son los problemas del CV ORIGINAL (no del reescrito).
- "roles_objetivo" van ordenados de mayor a menor match_porcentaje.
- "cv_reescrito" es solo para que vos lo pegues en Word — la plataforma no lo
  usa directamente, así que puede ser un poco más largo/detallado sin problema.

CV ORIGINAL:
<pegar aquí el texto completo del CV>
```

Ver `cv_analysis_ejemplo.json` en esta misma carpeta para un ejemplo completo
y válido del JSON que tenés que subir en el panel admin (podés subir ese
mismo archivo tal cual para probar cómo se ve la plataforma).
