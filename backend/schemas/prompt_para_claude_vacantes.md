# Prompt para generar `vacantes.json` con Claude

> **Más rápido:** si tenés Claude Code con control de navegador (Chrome)
> disponible, usá el skill `.claude/skills/vacantes-linkedin-jobfinder/` en
> vez de este proceso manual — navega LinkedIn en vivo, arma el ranking y
> genera el `vacantes.json` en un solo paso, sin copiar/pegar nada. Esta
> guía queda como referencia/fallback para cuando solo tengas el chat web
> de Claude a mano.

Este es el flujo manual del MVP para la etapa de "búsqueda de vacantes":

1. Entrás a LinkedIn (o donde busques vacantes) con las queries sugeridas en
   `cv_scores.json` / los roles objetivo del candidato.
2. Copiás los datos crudos de cada vacante que encuentres (título, empresa,
   ubicación, modalidad, fecha, link, número de solicitantes, descripción corta).
   No hace falta que sea perfecto — texto pegado de la propia página de LinkedIn sirve.
3. Le pegás todo eso a Claude junto con el prompt de abajo.
4. Claude te devuelve el JSON ya armado, listo para subir en el panel admin
   (`/admin.html` → sección "Subir vacantes.json" de esa sesión).

La plataforma (`/vacantes.html`) renderiza automáticamente ese JSON como una
página tipo LinkedIn con filtros, cards, top 5 y estadísticas — vos no tenés
que tocar HTML nunca.

---

## Prompt (copiar y pegar en Claude)

```
Eres un career coach experto en el mercado laboral latinoamericano.

Te voy a pasar:
1. El perfil de un candidato (roles objetivo, skills, país).
2. Una lista de vacantes que encontré manualmente en LinkedIn (texto crudo, puede venir desordenado).

Tu tarea:
1. Limpiar y estructurar cada vacante.
2. Rankearlas por relevancia para el perfil (match de título, skills requeridos vs disponibles, competencia, urgencia).
3. Clasificar cada una en una categoría: "alta_relevancia", "ventaja_interna" (empresas donde el candidato ya trabajó), "remoto_latam", "media" o "especializado".
4. Elegir las 5 mejores como top5_ids.
5. Escribir una nota de estrategia de postulación personalizada (2-4 oraciones).
6. Devolver SOLO un JSON válido con esta estructura exacta (sin markdown, sin texto adicional):

{
  "session_id": "<pegar aquí el session_id real>",
  "candidato": { "nombre": "", "cargo_objetivo": "", "pais": "" },
  "generado_el": "YYYY-MM-DD",
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
      "categoria": "alta_relevancia | ventaja_interna | remoto_latam | media | especializado",
      "match_porcentaje": 0
    }
  ]
}

Reglas:
- No inventes datos que no estén en el texto que te paso (si no tenés num_solicitudes o fecha exacta, usa null).
- El campo "url" debe ser el link real de la vacante — nunca lo inventes, si no lo tenés déjalo como null.
- "id" debe ser único por vacante (job_001, job_002, ...).

PERFIL DEL CANDIDATO:
<pegar aquí el contenido de cv_scores.json de la sesión, o al menos roles_objetivo y skills>

VACANTES ENCONTRADAS (texto crudo pegado de LinkedIn):
<pegar aquí lo que copiaste de LinkedIn>
```

Ver `vacantes_ejemplo.json` en esta misma carpeta para un ejemplo completo y válido del formato esperado.
