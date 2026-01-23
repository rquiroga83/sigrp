# Especificación de Requisitos de Software (SRS)

**Proyecto:** Sistema Integrado de Gestión de Recursos y Proyectos (SIGRP)
**Versión:** 1.0
**Enfoque:** Monolito Modular en Python (Django + HTMX)

---

## 1. Visión Ejecutiva

El SIGRP es una plataforma de gestión operativa diseñada para resolver la dicotomía entre modelos de contratación **Precio Fijo (Fixed Price)** y **Bolsa de Horas (Time & Materials)**.
A diferencia de herramientas tradicionales (Jira/Trello), el SIGRP integra la dimensión financiera en tiempo real, permitiendo:

1. Calcular rentabilidad real (Margen) contrastando el **Costo del Recurso** vs. la **Tarifa del Rol**.


2. Gestionar el talento mediante **Vectores de Habilidades** y búsqueda semántica (IA).


3. Detectar riesgos invisibles analizando el sentimiento en los *Daily Standups*.



---

## 2. Arquitectura Tecnológica (Tech Stack)

Siguiendo la restricción de **"Pure Python"**, se elimina la complejidad de frameworks JS externos, centralizando la lógica en el servidor.

### 2.1 Núcleo y Backend

* **Lenguaje:** Python 3.12+
* **Gestor de Dependencias:** `uv` (Astral) para una gestión de entorno ultra-rápida.
* **Framework Principal:** **Django 5.x**. Se elige por su ORM robusto y panel de administración, esenciales para manejar las relaciones complejas de las entidades definidas.


* **API/Interacciones:** **HTMX**. Permite interacciones dinámicas (SPA-like) enviando HTML parcial desde el servidor, evitando la necesidad de React/Vue.

### 2.2 Persistencia y Datos

* **Base de Datos Relacional:** **PostgreSQL 15+**.
* Almacena usuarios, proyectos, finanzas y registros de tiempo.
* Uso extensivo de `JSONB` para almacenar metadatos flexibles.




* **Base de Datos Vectorial:** **Qdrant**.
* Almacena los embeddings de las habilidades (`skills_vector`) de los recursos.
* Permite búsquedas por similitud semántica ("Busco experto en datos" -> Encuentra "Python + Pandas").



### 2.3 Procesamiento Asíncrono e IA

* **Cola de Tareas:** **Celery** + **Redis**.
* Encargado de cálculos pesados: Recálculo de EVM nocturno, procesamiento de NLP.




* **NLP Local:** **Sentence-Transformers** (`all-MiniLM-L6-v2`).
* Ejecución local dentro del contenedor para generar embeddings sin depender de APIs externas costosas.



### 2.4 Infraestructura

* **Contenedores:** Docker Compose orquestando `db` (Postgres), `cache` (Redis) y `vector_db` (Qdrant).

---

## 3. Módulos y Features Detallados

### 3.1 Módulo: Resources (Gestión de Talento)

Aquí tienes la actualización del documento de Especificación de Requisitos de Software (SRS). He agregado una nueva sección funcional (**RF-11**) y he actualizado el modelo de datos para soportar la **validación de capacidad concurrente**, asegurando que el sistema permita la asignación a múltiples proyectos pero prevenga la sobrecarga (burnout), alineado con la estrategia de "Resource Leveling" del documento original.

---

### Inserción en Sección 3.1 (Módulo: Resources)

Agrega este feature al listado de funcionalidades del módulo de Recursos:

* **RF-11: Motor de Validación de Asignaciones (Resource Leveling)**
* **Multigestion de Proyectos:** Permite asignar explícitamente un mismo `Resource` a múltiples proyectos simultáneamente (ej. 20h en Proyecto A y 20h en Proyecto B).
* **Validación de Capacidad (Overbooking Check):**
* Antes de confirmar una asignación, el sistema calcula la carga total del recurso en el rango de fechas seleccionado.
* **Fórmula:** .


* 
**Alertas de Fragmentación:** Si el recurso intenta ser asignado a más de **2 proyectos activos** simultáneamente, el sistema emite una advertencia de "Penalización por Context Switching" (reducción teórica de eficiencia del 20%).


* **UI Reactiva (HTMX):** Al seleccionar un recurso y fechas en el formulario de asignación, el sistema muestra visualmente una barra de carga ("Disponibilidad: 10/40 horas") sin recargar la página.



---

### Actualización en Sección 4 (Especificación de Datos)

Se añade una nueva entidad crítica para manejar la "reserva de tiempo" a alto nivel, separada de las tareas individuales.


Centraliza la información del capital humano, separando el "cargo" de la "persona".

* **RF-01: Taxonomía Dual (Rol vs. Recurso)**
* **Roles:** Definición de cargos genéricos (ej. "Senior Backend") con una `standard_rate` (Tarifa de venta).
* **Recursos:** Personas reales vinculadas a un Rol, pero con un `internal_cost` (Costo real/Salario).
* *Valor:* Permite calcular el margen de ganancia exacto por hora trabajada.


* 
**RF-02: Matriz de Habilidades Vectorial** 


* Capacidad de definir skills con niveles (1-5).
* Conversión automática de JSON `{"Python": 5}` a vector semántico en Qdrant.


* **RF-03: Buscador Semántico de Talento**
* Barra de búsqueda potenciada por IA que permite consultas en lenguaje natural para encontrar candidatos ideales para un proyecto basándose en su vector de capacidades.



### 3.2 Módulo: Projects (Gestión Financiera)

El corazón del sistema. Controla la ejecución y el presupuesto.

* 
**RF-04: Soporte Multimodelo** 


* **Fixed Price:** Control basado en `budget_limit` y `fixed_price`. Alertas si el costo proyectado supera el presupuesto.
* **Time & Materials:** Control basado en `hourly_rate` y `max_budget`. Alertas de "Burn Rate" (velocidad de consumo de fondos).




* **RF-05: Jerarquía de Ejecución**
* Estructura: `Proyecto` -> `Etapa` (Stages) -> `Tarea` (Tasks).
* Permite diagramas de Gantt agrupados por fases (Discovery, Dev, QA).


* **RF-06: Estimación vs. Realidad (Dual Cost Logic)**
* Las tareas tienen un costo planificado (`planned_value`) calculado con la tarifa del Rol.
* Las tareas tienen un costo real (`actual_cost`) calculado dinámicamente según quién imputó horas (`TimeLog`) y su costo interno específico.




* 
**RF-07: Métricas EVM Automatizadas** 


* Cálculo automático de CPI (Cost Performance Index) y SPI (Schedule Performance Index) en tiempo real.



### 3.3 Módulo: Standups (Inteligencia de Equipo)

Transforma reportes diarios en datos procesables.

* 
**RF-08: Bitácora de Standups** 


* Formulario para registro diario: "¿Qué hice?", "¿Qué haré?", "Bloqueos".


* 
**RF-09: Análisis de Sentimiento (NLP)** 


* Procesamiento automático del texto para detectar frustración o "Burnout".
* Clasificación de mood: Positivo, Neutral, Negativo.


* 
**RF-10: Detección de Bloqueos** 


* Extracción de entidades para identificar tecnologías problemáticas o dependencias externas bloqueantes.
* Cálculo de `TeamMood` agregado por proyecto.



