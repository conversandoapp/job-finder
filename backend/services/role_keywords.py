"""
Diccionario de puestos y palabras clave para el filtro automático de roles
(ver backend/services/role_matcher.py).

Cómo agregar/ajustar un puesto: agregá o editá una entrada de ROLE_KEYWORDS.
No hace falta tocar role_matcher.py.

  "Nombre del puesto": {
      "keywords": ["frase o palabra clave", "otra keyword", ...],
      "weight": 1.0,  # opcional, por defecto 1.0
  },

Las keywords se buscan sin distinguir mayúsculas ni tildes (se normalizan
antes de comparar), así que basta con escribir cada keyword una sola vez,
con tildes normales — no hace falta agregar también la variante sin tilde.
Mezclá español e inglés: los CVs de la región suelen usar jerga técnica
en inglés tal cual (ej. "product owner", "scrum").
"""

ROLE_KEYWORDS: dict[str, dict] = {
    # --- Tech / Producto ---------------------------------------------------
    "Product Manager": {
        "keywords": [
            "product manager", "gestión de producto", "roadmap", "backlog",
            "product owner", "okrs", "discovery", "product market fit",
            "product-market fit", "métricas de producto", "user research",
            "mvp",
        ],
    },
    "Product Owner": {
        "keywords": [
            "product owner", "backlog", "sprint", "scrum", "user stories",
            "historias de usuario", "priorización de backlog",
            "criterios de aceptación",
        ],
    },
    "Scrum Master / Agile Coach": {
        "keywords": [
            "scrum master", "agile coach", "scrum", "kanban", "sprint",
            "daily standup", "retrospectiva", "metodologías ágiles", "safe",
            "facilitador ágil",
        ],
    },
    "Project Manager / Coordinador de Proyectos": {
        "keywords": [
            "project manager", "gestión de proyectos",
            "coordinador de proyectos", "pmp", "cronograma", "gantt",
            "gestión de stakeholders", "gestión de riesgos", "ms project",
        ],
    },
    "Business Analyst": {
        "keywords": [
            "business analyst", "analista de negocios", "analista de negocio",
            "levantamiento de requerimientos", "requerimientos funcionales",
            "modelado de procesos", "bpmn", "casos de uso",
            "documentación funcional",
        ],
    },
    "Data Analyst": {
        "keywords": [
            "data analyst", "analista de datos", "sql", "power bi", "tableau",
            "excel avanzado", "python", "dashboards", "etl",
            "análisis de datos", "reportería",
        ],
    },
    "QA Tester / Analista de Calidad": {
        "keywords": [
            "qa tester", "analista de calidad", "quality assurance",
            "testing", "casos de prueba", "pruebas funcionales",
            "automatización de pruebas", "selenium", "bugs",
            "control de calidad",
        ],
    },
    "Desarrollador de Software": {
        "keywords": [
            "desarrollador", "developer", "programador", "software engineer",
            "python", "javascript", "java", "backend", "frontend",
            "full stack", "api rest", "bases de datos", "git", "github",
        ],
    },
    "Soporte TI / Help Desk": {
        "keywords": [
            "soporte técnico", "help desk", "mesa de ayuda", "soporte ti",
            "resolución de incidentes", "service desk", "itil",
            "atención de tickets",
        ],
    },
    "UX/UI Designer": {
        "keywords": [
            "ux", "ui", "diseño de experiencia", "figma", "wireframes",
            "prototipado", "usabilidad", "diseño de interfaces",
            "user research",
        ],
    },
    # --- Negocios / Administración ------------------------------------------
    "Analista Contable / Contador": {
        "keywords": [
            "contador", "contabilidad", "analista contable",
            "estados financieros", "conciliación bancaria",
            "libros contables", "declaraciones tributarias", "niif",
            "cierre contable",
        ],
    },
    "Analista Financiero": {
        "keywords": [
            "analista financiero", "finanzas", "flujo de caja", "presupuesto",
            "análisis financiero", "estados financieros", "valorización",
            "indicadores financieros",
        ],
    },
    "Asistente Administrativo": {
        "keywords": [
            "asistente administrativo", "asistente de gerencia",
            "gestión documentaria", "archivo", "coordinación de agenda",
            "atención al cliente", "office",
        ],
    },
    "Analista de RRHH": {
        "keywords": [
            "recursos humanos", "analista de rrhh", "reclutamiento",
            "selección de personal", "onboarding", "gestión del talento",
            "clima laboral", "planilla", "nómina",
        ],
    },
    "Analista de Marketing": {
        "keywords": [
            "marketing", "analista de marketing", "campañas",
            "posicionamiento de marca", "estrategia de marketing",
            "investigación de mercado", "google analytics", "seo", "sem",
        ],
    },
    "Community Manager / Marketing Digital": {
        "keywords": [
            "community manager", "marketing digital", "redes sociales",
            "contenido digital", "instagram", "facebook ads", "google ads",
            "engagement", "gestión de redes",
        ],
    },
    "Ejecutivo Comercial / Ventas": {
        "keywords": [
            "ventas", "ejecutivo comercial", "ejecutivo de ventas",
            "cierre de ventas", "cartera de clientes", "prospección",
            "negociación", "metas comerciales", "crm",
        ],
    },
    "Atención al Cliente": {
        "keywords": [
            "atención al cliente", "servicio al cliente", "customer service",
            "call center", "resolución de reclamos",
            "satisfacción del cliente",
        ],
    },
    "Logística / Compras": {
        "keywords": [
            "logística", "compras", "abastecimiento", "cadena de suministro",
            "supply chain", "gestión de inventarios", "almacén",
            "proveedores",
        ],
    },
    "Analista de Operaciones": {
        "keywords": [
            "analista de operaciones", "operaciones", "mejora de procesos",
            "eficiencia operativa", "indicadores de gestión", "kpi",
            "optimización de procesos",
        ],
    },
}
