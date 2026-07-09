"""
Diccionario de puestos y palabras clave para el filtro automático de roles
(ver backend/services/role_matcher.py).

Las keywords se buscan sin distinguir mayúsculas ni tildes (se normalizan
antes de comparar). Mezclá español e inglés: los CVs de la región suelen
usar jerga técnica en inglés tal cual (ej. "product owner", "scrum").

Este archivo tiene dos partes:

1. Un núcleo de ~20 puestos curados a mano con listas de keywords ricas
   (los más comunes entre los candidatos de Job Finder).
2. Una "cola larga" de 300+ puestos adicionales, armada automáticamente al
   cargar el módulo a partir de CATEGORY_KEYWORDS (términos compartidos por
   industria/área) + un puñado de keywords específicas por puesto en
   _EXTRA_ROLES. Esto permite cubrir muchísimos más puestos sin tener que
   escribir a mano una lista larga de keywords para cada uno.

Cómo agregar un puesto nuevo:
  - Si es uno de los ~20 puestos "núcleo" (alto volumen, vale la pena
    curarlo bien): agregá una entrada directo en ROLE_KEYWORDS.
  - Si es un puesto más de nicho: agregalo a _EXTRA_ROLES como
    (titulo, categoria, [keywords específicas]). Si la categoría no existe
    todavía, agregala primero a CATEGORY_KEYWORDS.
No hace falta tocar role_matcher.py en ningún caso.
"""

ROLE_KEYWORDS: dict[str, dict] = {
    # --- Tech / Producto (núcleo) -------------------------------------------
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
    # --- Negocios / Administración (núcleo) ---------------------------------
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

# ---------------------------------------------------------------------------
# Cola larga: 300+ puestos adicionales, generados por categoría.
# ---------------------------------------------------------------------------

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "salud": ["salud", "paciente", "atención médica", "clínica", "hospital", "historia clínica"],
    "ingenieria": ["ingeniería", "proyectos técnicos", "normas técnicas", "diseño técnico", "especificaciones técnicas"],
    "construccion": ["construcción", "obra", "edificación", "planos de construcción"],
    "tech": ["tecnología", "sistemas", "software", "ti", "desarrollo de sistemas"],
    "legal": ["legal", "jurídico", "normativa", "derecho", "asesoría legal"],
    "finanzas": ["finanzas", "banca", "seguros", "gestión financiera"],
    "administracion": ["gestión empresarial", "administración", "planificación estratégica"],
    "marketing": ["marketing", "publicidad", "comunicación", "estrategia de marca"],
    "logistica": ["logística", "operaciones", "producción", "cadena de suministro"],
    "mineria": ["minería", "sector extractivo", "operaciones mineras"],
    "agro": ["agricultura", "agroindustria", "sector agropecuario"],
    "turismo": ["turismo", "hotelería", "gastronomía", "servicio al huésped"],
    "seguridad": ["seguridad", "vigilancia", "prevención de riesgos"],
    "transporte": ["transporte", "movilidad", "logística de transporte"],
    "arte": ["arte", "diseño creativo", "producción creativa"],
    "rrhh": ["recursos humanos", "talento humano", "gestión de personas"],
    "gobierno": ["sector público", "gestión pública", "entidad estatal"],
    "ciencia": ["investigación científica", "ciencia", "método científico"],
    "deportes": ["deporte", "actividad física", "entrenamiento deportivo"],
    "retail": ["retail", "comercio", "tienda", "punto de venta"],
    "educacion": ["educación", "enseñanza", "pedagogía", "formación académica"],
}

_EXTRA_ROLES: list[tuple[str, str, list[str]]] = [
    # --- Salud ---------------------------------------------------------
    ("Médico General", "salud", ["consulta médica", "diagnóstico", "medicina general"]),
    ("Médico Cardiólogo", "salud", ["cardiología", "electrocardiograma", "enfermedades cardiovasculares"]),
    ("Médico Pediatra", "salud", ["pediatría", "salud infantil", "control de niño sano"]),
    ("Médico Ginecólogo", "salud", ["ginecología", "obstetricia", "salud reproductiva"]),
    ("Médico Dermatólogo", "salud", ["dermatología", "enfermedades de la piel"]),
    ("Médico Psiquiatra", "salud", ["psiquiatría", "salud mental", "trastornos mentales"]),
    ("Médico Cirujano", "salud", ["cirugía", "sala de operaciones", "procedimientos quirúrgicos"]),
    ("Médico Anestesiólogo", "salud", ["anestesiología", "anestesia", "quirófano"]),
    ("Médico Oftalmólogo", "salud", ["oftalmología", "salud visual", "cirugía ocular"]),
    ("Médico Traumatólogo", "salud", ["traumatología", "fracturas", "ortopedia"]),
    ("Médico Neurólogo", "salud", ["neurología", "sistema nervioso", "electroencefalograma"]),
    ("Médico Oncólogo", "salud", ["oncología", "quimioterapia", "cáncer"]),
    ("Médico Endocrinólogo", "salud", ["endocrinología", "diabetes", "hormonas"]),
    ("Médico Urólogo", "salud", ["urología", "sistema urinario"]),
    ("Médico Otorrinolaringólogo", "salud", ["otorrinolaringología", "oído nariz garganta"]),
    ("Médico Internista", "salud", ["medicina interna", "enfermedades crónicas"]),
    ("Médico Geriatra", "salud", ["geriatría", "adulto mayor"]),
    ("Médico de Emergencias", "salud", ["emergencias médicas", "urgencias", "triaje"]),
    ("Médico Infectólogo", "salud", ["infectología", "enfermedades infecciosas"]),
    ("Médico Nefrólogo", "salud", ["nefrología", "enfermedades renales"]),
    ("Médico Neumólogo", "salud", ["neumología", "enfermedades respiratorias"]),
    ("Médico Reumatólogo", "salud", ["reumatología"]),
    ("Médico Patólogo", "salud", ["anatomía patológica", "biopsias"]),
    ("Médico Ocupacional", "salud", ["salud ocupacional", "medicina del trabajo"]),
    ("Enfermero/a", "salud", ["enfermería", "cuidado de pacientes", "signos vitales"]),
    ("Técnico en Enfermería", "salud", ["técnico en enfermería", "asistencia al paciente"]),
    ("Camillero", "salud", ["traslado de pacientes"]),
    ("Obstetra", "salud", ["obstetricia", "parto", "control prenatal"]),
    ("Odontólogo", "salud", ["odontología", "salud dental", "consultorio dental"]),
    ("Técnico Dental", "salud", ["laboratorio dental", "prótesis dental"]),
    ("Técnico en Farmacia", "salud", ["dispensación de medicamentos", "farmacia"]),
    ("Químico Farmacéutico", "salud", ["farmacia", "regencia de farmacia", "dispensación farmacéutica"]),
    ("Nutricionista", "salud", ["nutrición", "plan alimenticio", "dietética"]),
    ("Fisioterapeuta", "salud", ["fisioterapia", "rehabilitación física"]),
    ("Terapeuta Ocupacional", "salud", ["terapia ocupacional", "rehabilitación"]),
    ("Psicólogo Clínico", "salud", ["psicología clínica", "terapia psicológica", "salud mental"]),
    ("Tecnólogo Médico", "salud", ["laboratorio clínico", "análisis clínicos"]),
    ("Técnico en Radiología", "salud", ["radiología", "imágenes médicas", "rayos x"]),
    ("Paramédico", "salud", ["atención prehospitalaria", "ambulancia", "primeros auxilios"]),
    ("Veterinario", "salud", ["medicina veterinaria", "salud animal", "clínica veterinaria"]),
    ("Auxiliar Veterinario", "salud", ["asistencia veterinaria"]),
    ("Instrumentista Quirúrgico", "salud", ["instrumentación quirúrgica"]),
    ("Auditor Médico", "salud", ["auditoría médica", "seguros de salud"]),
    # --- Ingeniería ------------------------------------------------------
    ("Ingeniero Civil", "ingenieria", ["construcción", "estructuras", "obras civiles"]),
    ("Ingeniero Industrial", "ingenieria", ["procesos productivos", "optimización de procesos", "lean manufacturing"]),
    ("Ingeniero Mecánico", "ingenieria", ["diseño mecánico", "mantenimiento mecánico", "maquinaria"]),
    ("Ingeniero Eléctrico", "ingenieria", ["instalaciones eléctricas", "sistemas de potencia"]),
    ("Ingeniero Electrónico", "ingenieria", ["circuitos electrónicos", "automatización"]),
    ("Ingeniero Químico", "ingenieria", ["procesos químicos", "plantas industriales"]),
    ("Ingeniero Ambiental", "ingenieria", ["gestión ambiental", "impacto ambiental", "sostenibilidad"]),
    ("Ingeniero de Minas", "ingenieria", ["minería", "explotación minera", "yacimientos"]),
    ("Ingeniero de Petróleo y Gas", "ingenieria", ["petróleo", "gas natural", "yacimientos petrolíferos"]),
    ("Geólogo", "ingenieria", ["geología", "exploración geológica", "mapeo geológico"]),
    ("Ingeniero Metalurgista", "ingenieria", ["metalurgia", "procesamiento de minerales"]),
    ("Ingeniero Agrónomo", "ingenieria", ["agronomía", "cultivos", "producción agrícola"]),
    ("Ingeniero de Alimentos", "ingenieria", ["industria alimentaria", "procesamiento de alimentos"]),
    ("Ingeniero Textil", "ingenieria", ["industria textil", "confección"]),
    ("Ingeniero Naval", "ingenieria", ["construcción naval", "buques"]),
    ("Ingeniero Aeronáutico", "ingenieria", ["aeronáutica", "aviación"]),
    ("Ingeniero de Sistemas", "ingenieria", ["sistemas de información", "desarrollo de software"]),
    ("Ingeniero de Telecomunicaciones", "ingenieria", ["telecomunicaciones", "redes de telecomunicación"]),
    ("Ingeniero Estructural", "ingenieria", ["cálculo estructural", "diseño estructural"]),
    ("Ingeniero de Seguridad Industrial", "ingenieria", ["seguridad industrial", "prevención de riesgos laborales"]),
    ("Ingeniero de Procesos", "ingenieria", ["mejora de procesos", "ingeniería de procesos"]),
    ("Ingeniero de Mantenimiento", "ingenieria", ["mantenimiento preventivo", "mantenimiento correctivo"]),
    ("Ingeniero Sanitario", "ingenieria", ["saneamiento", "agua potable", "alcantarillado"]),
    ("Ingeniero Forestal", "ingenieria", ["manejo forestal", "recursos forestales"]),
    ("Ingeniero Pesquero", "ingenieria", ["industria pesquera", "acuicultura"]),
    ("Dibujante Técnico", "ingenieria", ["planos técnicos", "autocad"]),
    ("Topógrafo", "ingenieria", ["topografía", "levantamiento topográfico"]),
    ("Ingeniero Biomédico", "ingenieria", ["equipos biomédicos", "ingeniería biomédica", "equipos médicos"]),
    ("Ingeniero de Confiabilidad", "ingenieria", ["confiabilidad de activos", "mantenimiento predictivo"]),
    ("Ingeniero de Costos", "ingenieria", ["metrados", "presupuesto de proyectos"]),
    ("Ingeniero de Puesta en Marcha", "ingenieria", ["puesta en marcha", "commissioning"]),
    # --- Construcción ----------------------------------------------------
    ("Arquitecto", "construccion", ["diseño arquitectónico", "planos arquitectónicos"]),
    ("Maestro de Obra", "construccion", ["dirección de obra", "cuadrilla de obreros"]),
    ("Residente de Obra", "construccion", ["supervisión de obra", "residencia de obra"]),
    ("Supervisor de Construcción", "construccion", ["control de obra"]),
    ("Prevencionista de Riesgos (SSOMA)", "construccion", ["seguridad y salud ocupacional", "ssoma"]),
    ("Diseñador de Interiores", "construccion", ["diseño de interiores", "decoración"]),
    ("Presupuestista de Obra", "construccion", ["metrados", "presupuesto de obra"]),
    ("Operario de Construcción", "construccion", ["albañilería", "mano de obra"]),
    ("Electricista", "construccion", ["instalaciones eléctricas", "tablero eléctrico"]),
    ("Gasfitero / Plomero", "construccion", ["instalaciones sanitarias", "tuberías"]),
    ("Soldador", "construccion", ["soldadura", "trabajos de soldadura"]),
    ("Carpintero", "construccion", ["carpintería", "trabajos en madera"]),
    ("Modelador BIM", "construccion", ["modelado bim", "revit"]),
    ("Instalador de Gas", "construccion", ["instalaciones de gas"]),
    # --- Tecnología --------------------------------------------------------
    ("DevOps Engineer", "tech", ["ci/cd", "docker", "kubernetes", "infraestructura como código"]),
    ("Data Engineer", "tech", ["pipelines de datos", "big data", "spark"]),
    ("Data Scientist", "tech", ["machine learning", "modelos predictivos", "estadística"]),
    ("Machine Learning Engineer", "tech", ["modelos de machine learning", "inteligencia artificial"]),
    ("Cloud Architect", "tech", ["aws", "azure", "google cloud", "arquitectura cloud"]),
    ("Analista de Ciberseguridad", "tech", ["ciberseguridad", "seguridad informática", "pentesting"]),
    ("Ingeniero de Redes", "tech", ["redes", "cisco", "administración de redes"]),
    ("Administrador de Bases de Datos", "tech", ["administración de bases de datos", "oracle", "postgresql"]),
    ("Desarrollador Móvil (iOS/Android)", "tech", ["desarrollo móvil", "android", "ios", "kotlin", "swift"]),
    ("Desarrollador de Videojuegos", "tech", ["desarrollo de videojuegos", "unity", "unreal engine"]),
    ("Gerente de TI", "tech", ["gerencia de ti", "gestión de sistemas"]),
    ("CTO", "tech", ["dirección tecnológica", "estrategia tecnológica"]),
    ("Analista de Sistemas", "tech", ["análisis de sistemas"]),
    ("Consultor SAP", "tech", ["sap", "erp", "implementación de sap"]),
    ("Administrador Salesforce", "tech", ["salesforce", "crm"]),
    ("Desarrollador RPA", "tech", ["automatización robótica de procesos", "rpa", "uipath"]),
    ("Arquitecto de Software", "tech", ["arquitectura de software", "microservicios"]),
    ("Site Reliability Engineer", "tech", ["confiabilidad de sistemas", "monitoreo de sistemas"]),
    ("Administrador de Sistemas", "tech", ["administración de servidores", "sysadmin"]),
    ("Especialista en Inteligencia Artificial", "tech", ["inteligencia artificial", "deep learning"]),
    ("Desarrollador Web", "tech", ["desarrollo web", "html", "css"]),
    ("Blockchain Developer", "tech", ["blockchain", "smart contracts", "criptomonedas"]),
    ("Technical Writer", "tech", ["documentación técnica"]),
    ("Especialista en ERP Oracle", "tech", ["oracle erp"]),
    ("Auditor de Sistemas", "tech", ["auditoría de sistemas", "auditoría ti"]),
    ("Especialista en Protección de Datos (DPO)", "tech", ["protección de datos personales", "dpo"]),
    ("Oficial de Seguridad de la Información (CISO)", "tech", ["seguridad de la información", "ciso"]),
    ("Analista SOC", "tech", ["centro de operaciones de seguridad", "soc"]),
    ("Analista de Inteligencia de Negocios (BI)", "tech", ["business intelligence", "power bi", "tableau"]),
    # --- Legal ---------------------------------------------------------
    ("Abogado Corporativo", "legal", ["derecho corporativo", "asesoría legal empresarial"]),
    ("Abogado Litigante", "legal", ["litigios", "procesos judiciales"]),
    ("Abogado Laboral", "legal", ["derecho laboral", "relaciones laborales"]),
    ("Abogado Penal", "legal", ["derecho penal", "defensa penal"]),
    ("Abogado Tributario", "legal", ["derecho tributario", "impuestos"]),
    ("Notario", "legal", ["notaría", "escrituras públicas"]),
    ("Asistente Legal / Paralegal", "legal", ["asistencia legal", "expedientes legales"]),
    ("Compliance Officer", "legal", ["cumplimiento normativo", "compliance"]),
    ("Analista de Propiedad Intelectual", "legal", ["propiedad intelectual", "marcas y patentes"]),
    # --- Finanzas / Banca / Seguros -----------------------------------------
    ("Analista de Riesgos", "finanzas", ["gestión de riesgos financieros", "riesgo crediticio"]),
    ("Auditor Interno", "finanzas", ["auditoría interna", "control interno"]),
    ("Auditor Externo", "finanzas", ["auditoría externa"]),
    ("Analista de Crédito", "finanzas", ["evaluación crediticia", "score crediticio"]),
    ("Ejecutivo de Banca", "finanzas", ["banca personal", "productos bancarios"]),
    ("Asesor de Inversiones", "finanzas", ["portafolio de inversiones", "mercado de valores"]),
    ("Actuario", "finanzas", ["cálculo actuarial", "seguros"]),
    ("Analista de Seguros", "finanzas", ["pólizas de seguro", "siniestros"]),
    ("Tesorero", "finanzas", ["gestión de tesorería", "flujo de caja"]),
    ("Controller Financiero", "finanzas", ["control de gestión", "reportes financieros"]),
    ("Oficial de Cumplimiento (AML)", "finanzas", ["prevención de lavado de activos", "aml"]),
    ("Cajero Bancario", "finanzas", ["operaciones bancarias", "atención en ventanilla"]),
    ("Analista de Cobranzas", "finanzas", ["gestión de cobranzas", "recuperación de cartera"]),
    ("Ejecutivo de Microfinanzas", "finanzas", ["microfinanzas", "créditos"]),
    ("Analista de Presupuesto", "finanzas", ["elaboración de presupuesto"]),
    # --- Administración / Negocios ------------------------------------------
    ("Gerente General", "administracion", ["dirección general", "gestión estratégica"]),
    ("Gerente de Operaciones", "administracion", ["gestión de operaciones"]),
    ("Gerente Comercial", "administracion", ["dirección comercial", "estrategia de ventas"]),
    ("Gerente de Finanzas (CFO)", "administracion", ["dirección financiera"]),
    ("Gerente de Recursos Humanos", "administracion", ["dirección de recursos humanos"]),
    ("Asistente Ejecutivo", "administracion", ["apoyo a gerencia", "agenda ejecutiva"]),
    ("Secretaria Ejecutiva", "administracion", ["secretariado ejecutivo"]),
    ("Recepcionista", "administracion", ["atención de recepción", "central telefónica"]),
    ("Encargado de Compras", "administracion", ["negociación con proveedores", "órdenes de compra"]),
    ("Analista de Procesos", "administracion", ["mapeo de procesos", "mejora continua"]),
    ("Consultor de Negocios", "administracion", ["consultoría empresarial", "estrategia de negocio"]),
    ("Emprendedor / Fundador de Startup", "administracion", ["emprendimiento", "startup"]),
    ("Gerente de Innovación", "administracion", ["innovación corporativa"]),
    ("Coordinador de Eventos", "administracion", ["organización de eventos", "eventos corporativos"]),
    ("Wedding Planner", "administracion", ["organización de bodas"]),
    ("Practicante / Trainee", "administracion", ["prácticas profesionales", "trainee"]),
    ("Auxiliar de Oficina", "administracion", ["labores de oficina"]),
    ("Consultor Estratégico", "administracion", ["consultoría estratégica"]),
    ("Gestor de Alianzas Estratégicas", "administracion", ["alianzas estratégicas", "partnerships"]),
    ("Analista de Sostenibilidad (ESG)", "administracion", ["sostenibilidad", "esg", "responsabilidad social"]),
    # --- Marketing / Ventas / Comunicación ----------------------------------
    ("Brand Manager", "marketing", ["gestión de marca", "posicionamiento de marca"]),
    ("Especialista en Trade Marketing", "marketing", ["trade marketing", "punto de venta"]),
    ("Diseñador Gráfico", "marketing", ["diseño gráfico", "adobe illustrator", "photoshop"]),
    ("Redactor Publicitario / Copywriter", "marketing", ["redacción publicitaria", "copywriting"]),
    ("Relacionista Público", "marketing", ["relaciones públicas", "gestión de prensa"]),
    ("Periodista", "marketing", ["redacción periodística", "noticias"]),
    ("Locutor", "marketing", ["locución", "radio"]),
    ("Fotógrafo", "marketing", ["fotografía profesional", "sesión fotográfica"]),
    ("Editor de Video / Videomaker", "marketing", ["edición de video", "premiere", "after effects"]),
    ("Growth Hacker", "marketing", ["growth marketing", "experimentos de crecimiento"]),
    ("Ejecutivo de Cuentas", "marketing", ["gestión de cuentas de clientes"]),
    ("Key Account Manager", "marketing", ["cuentas clave", "kam"]),
    ("Merchandiser", "marketing", ["exhibición de productos", "trade marketing"]),
    ("Traffic Manager", "marketing", ["pauta publicitaria", "media buying"]),
    ("Especialista en Email Marketing", "marketing", ["email marketing", "mailchimp"]),
    ("Especialista en Marketplace", "marketing", ["marketplace", "mercado libre", "amazon"]),
    ("Gerente de Ecommerce", "marketing", ["comercio electrónico", "tienda online"]),
    ("Product Marketing Manager", "marketing", ["marketing de producto"]),
    ("Especialista en Experiencia del Cliente (CX)", "marketing", ["experiencia del cliente", "customer experience"]),
    ("Especialista en Comunicaciones Internas", "marketing", ["comunicación interna corporativa"]),
    ("Gestor de Contenidos", "marketing", ["gestión de contenidos", "content manager"]),
    ("Diseñador de Servicios", "marketing", ["diseño de servicios", "service design"]),
    # --- Logística / Operaciones / Manufactura ------------------------------
    ("Supervisor de Planta", "logistica", ["supervisión de producción"]),
    ("Jefe de Almacén", "logistica", ["gestión de almacén", "control de stock"]),
    ("Operario de Producción", "logistica", ["línea de producción", "manufactura"]),
    ("Controlador de Calidad", "logistica", ["control de calidad", "inspección de calidad"]),
    ("Analista de Mantenimiento", "logistica", ["mantenimiento industrial"]),
    ("Conductor / Chofer", "logistica", ["licencia de conducir", "manejo de vehículos"]),
    ("Despachador", "logistica", ["despacho de mercadería"]),
    ("Analista de Comercio Exterior", "logistica", ["importaciones", "exportaciones"]),
    ("Agente de Aduanas", "logistica", ["trámites aduaneros", "aduanas"]),
    ("Supervisor de Flota", "logistica", ["gestión de flota vehicular"]),
    ("Jefe de Producción", "logistica", ["planificación de producción"]),
    ("Planificador de Demanda", "logistica", ["forecast de demanda", "planeamiento"]),
    ("Montacarguista", "logistica", ["manejo de montacargas"]),
    ("Coordinador de Distribución", "logistica", ["distribución de mercadería"]),
    ("Supervisor de Picking y Packing", "logistica", ["picking", "packing"]),
    ("Gerente de Cadena de Suministro", "logistica", ["supply chain management"]),
    ("Estibador", "logistica", ["carga y descarga"]),
    ("Auditor de Calidad ISO", "logistica", ["normas iso", "auditoría de calidad"]),
    ("Especialista en Mejora Continua", "logistica", ["kaizen", "six sigma"]),
    ("Operario Textil", "logistica", ["confección textil"]),
    ("Supervisor de Confección", "logistica", ["supervisión de confección"]),
    # --- Minería / Energía ---------------------------------------------------
    ("Supervisor de Seguridad Minera", "mineria", ["seguridad minera"]),
    ("Operador de Maquinaria Pesada", "mineria", ["maquinaria pesada", "equipos mineros"]),
    ("Técnico Electricista Industrial", "mineria", ["mantenimiento eléctrico industrial"]),
    ("Técnico en Energías Renovables", "mineria", ["energía solar", "energía eólica"]),
    ("Perforista", "mineria", ["perforación minera"]),
    ("Ingeniero de Planeamiento Minero", "mineria", ["planeamiento de mina"]),
    ("Ingeniero de Ventilación de Minas", "mineria", ["ventilación minera"]),
    ("Jefe de Guardia Mina", "mineria", ["turno minero"]),
    ("Especialista en Voladura", "mineria", ["voladura de rocas", "explosivos"]),
    # --- Agro ------------------------------------------------------------
    ("Técnico Agrícola", "agro", ["manejo de cultivos"]),
    ("Supervisor de Campo", "agro", ["supervisión agrícola"]),
    ("Especialista en Exportación Agrícola", "agro", ["exportación de productos agrícolas"]),
    ("Encargado de Packing", "agro", ["empaque de productos agrícolas"]),
    ("Capataz Agrícola", "agro", ["jornaleros", "cosecha"]),
    ("Ingeniero Zootecnista", "agro", ["zootecnia", "producción pecuaria"]),
    ("Técnico Pecuario", "agro", ["manejo de ganado"]),
    # --- Turismo / Hotelería / Gastronomía ---------------------------------
    ("Chef", "turismo", ["cocina profesional", "gastronomía"]),
    ("Cocinero", "turismo", ["preparación de alimentos"]),
    ("Mesero / Mozo", "turismo", ["servicio de mesa", "atención en restaurante"]),
    ("Bartender", "turismo", ["coctelería", "barra"]),
    ("Recepcionista de Hotel", "turismo", ["check-in", "reservas hoteleras"]),
    ("Guía Turístico", "turismo", ["turismo receptivo", "tours guiados"]),
    ("Gerente de Hotel", "turismo", ["administración hotelera"]),
    ("Ama de Llaves", "turismo", ["housekeeping", "limpieza de habitaciones"]),
    ("Sommelier", "turismo", ["maridaje", "cata de vinos"]),
    ("Chef Pastelero", "turismo", ["pastelería", "repostería"]),
    ("Barista", "turismo", ["preparación de café", "cafetería"]),
    # --- Seguridad -------------------------------------------------------
    ("Agente de Seguridad", "seguridad", ["vigilancia", "seguridad patrimonial"]),
    ("Supervisor de Seguridad", "seguridad", ["supervisión de seguridad"]),
    ("Guardaespaldas", "seguridad", ["escolta", "protección personal"]),
    ("Analista de Prevención de Pérdidas", "seguridad", ["prevención de pérdidas"]),
    ("Vigilante Municipal (Sereno)", "seguridad", ["serenazgo"]),
    # --- Transporte --------------------------------------------------------
    ("Chofer de Transporte de Carga", "transporte", ["transporte de carga"]),
    ("Piloto Comercial", "transporte", ["aviación comercial", "vuelos"]),
    ("Controlador Aéreo", "transporte", ["control de tráfico aéreo"]),
    ("Capitán de Barco", "transporte", ["navegación", "marina mercante"]),
    ("Motorizado / Delivery", "transporte", ["reparto", "delivery"]),
    ("Buzo Comercial", "transporte", ["buceo comercial"]),
    # --- Arte / Diseño / Entretenimiento ------------------------------------
    ("Diseñador Industrial", "arte", ["diseño de producto"]),
    ("Diseñador de Modas", "arte", ["diseño textil", "moda"]),
    ("Ilustrador", "arte", ["ilustración digital"]),
    ("Animador 3D", "arte", ["animación 3d", "blender"]),
    ("Músico", "arte", ["interpretación musical"]),
    ("Actor", "arte", ["actuación", "artes escénicas"]),
    ("Productor Audiovisual", "arte", ["producción de video", "cine"]),
    ("Guionista", "arte", ["escritura de guiones"]),
    ("Maquillador Profesional", "arte", ["maquillaje profesional"]),
    ("Estilista / Peluquero", "arte", ["estilismo", "peluquería"]),
    ("Patronista", "arte", ["patronaje", "diseño de patrones"]),
    # --- Recursos Humanos ----------------------------------------------------
    ("Especialista en Compensaciones y Beneficios", "rrhh", ["compensaciones", "beneficios laborales"]),
    ("Especialista en Capacitación", "rrhh", ["capacitación y desarrollo"]),
    ("Generalista de RRHH", "rrhh", ["administración de personal"]),
    ("Headhunter / Reclutador", "rrhh", ["búsqueda de talento", "headhunting"]),
    ("Especialista en Bienestar Laboral", "rrhh", ["bienestar laboral", "clima organizacional"]),
    ("Especialista en Diversidad e Inclusión", "rrhh", ["diversidad e inclusión"]),
    # --- Gobierno / Sector Público / ONG ------------------------------------
    ("Gestor Público", "gobierno", ["gestión pública"]),
    ("Analista de Políticas Públicas", "gobierno", ["políticas públicas"]),
    ("Trabajador Social", "gobierno", ["trabajo social", "intervención social"]),
    ("Coordinador de Proyectos Sociales", "gobierno", ["proyectos sociales"]),
    ("Especialista en Cooperación Internacional", "gobierno", ["cooperación internacional"]),
    ("Especialista en Contrataciones del Estado", "gobierno", ["contrataciones públicas", "osce"]),
    ("Gestor de Trámites Municipales", "gobierno", ["trámites municipales"]),
    # --- Ciencia / Investigación ---------------------------------------------
    ("Investigador Científico", "ciencia", ["investigación científica"]),
    ("Biólogo", "ciencia", ["biología"]),
    ("Químico", "ciencia", ["análisis químico"]),
    ("Físico", "ciencia", ["física aplicada"]),
    ("Estadístico", "ciencia", ["análisis estadístico"]),
    ("Matemático", "ciencia", ["modelamiento matemático"]),
    ("Especialista en Sistemas de Información Geográfica (GIS)", "ciencia", ["sig", "arcgis", "cartografía digital"]),
    # --- Deportes ----------------------------------------------------------
    ("Entrenador Deportivo", "deportes", ["entrenamiento deportivo"]),
    ("Preparador Físico", "deportes", ["preparación física"]),
    ("Fisioterapeuta Deportivo", "deportes", ["rehabilitación deportiva"]),
    ("Árbitro", "deportes", ["arbitraje deportivo"]),
    ("Instructor de Gimnasio", "deportes", ["entrenamiento personal", "fitness"]),
    # --- Retail / Comercio ---------------------------------------------------
    ("Vendedor de Tienda", "retail", ["atención al cliente en tienda"]),
    ("Cajero", "retail", ["manejo de caja"]),
    ("Visual Merchandiser", "retail", ["visual merchandising", "vitrinismo"]),
    ("Encargado de Tienda", "retail", ["gestión de tienda retail"]),
    ("Category Manager", "retail", ["gestión de categorías retail"]),
    ("Especialista en Franquicias", "retail", ["gestión de franquicias"]),
    # --- Educación -----------------------------------------------------------
    ("Profesor de Primaria", "educacion", ["educación primaria"]),
    ("Profesor de Secundaria", "educacion", ["educación secundaria"]),
    ("Docente Universitario", "educacion", ["educación superior"]),
    ("Profesor de Inglés", "educacion", ["enseñanza de inglés"]),
    ("Coordinador Académico", "educacion", ["coordinación académica"]),
    ("Director de Colegio", "educacion", ["dirección educativa"]),
    ("Psicopedagogo", "educacion", ["psicopedagogía"]),
    ("Bibliotecario", "educacion", ["gestión bibliotecaria"]),
    ("Capacitador Corporativo", "educacion", ["capacitación empresarial"]),
    ("Tutor Virtual", "educacion", ["educación virtual", "e-learning"]),
    ("Diseñador Instruccional", "educacion", ["diseño instruccional", "elearning"]),
    ("Profesor de Educación Física", "educacion", ["educación física escolar"]),
    ("Instructor Técnico (SENATI/SENA)", "educacion", ["formación técnica"]),
]

for _titulo, _categoria, _extra in _EXTRA_ROLES:
    _keywords = [_titulo.lower(), *_extra, *CATEGORY_KEYWORDS.get(_categoria, [])]
    ROLE_KEYWORDS[_titulo] = {"keywords": list(dict.fromkeys(_keywords))}

assert len(ROLE_KEYWORDS) >= 300, f"Se esperaban 300+ puestos en el diccionario, hay {len(ROLE_KEYWORDS)}"
