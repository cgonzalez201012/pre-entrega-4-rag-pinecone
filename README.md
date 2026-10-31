# Pre-entrega 4 · Sistema RAG escalable en la nube con Pinecone

En este repositorio construí un módulo de recuperación para un sistema RAG: indexo documentos (Markdown y PDF) en un índice **Pinecone Serverless**, los recupero con un **buscador híbrido** (BM25 + vectorial, fusionados con `EnsembleRetriever`) y mido la calidad con **Recall@5 y Precision@5** sobre un *golden set*.

Como dataset usé 13 documentos sintéticos de Gobierno de Datos de una empresa retail ficticia, *Mercado Austral S.A.* (políticas, roles, procedimientos y glosarios), con códigos como `GD-POL-001` y siglas como `Depo360`, para que la búsqueda léxica tenga algo concreto que encontrar.

```
data/ (.md, .pdf) ─► ingest.py ─► fragmentos de ~600 tokens + metadatos ─► embeddings Gemini (1536) ─► Pinecone Serverless
                                                                                                      (namespace mercado-austral)
consulta ─► RAGSystem ─► EnsembleRetriever ─┬─ BM25   (texto leído de la metadata de Pinecone)
                                            └─ vectorial (PineconeVectorStore)      ─► top-5 con fuente, página y sección
evaluate.py ─► Recall@5 · Precision@5 · MRR sobre golden_set.json (compara bm25, vectorial e híbrido)
```

## Resultados

Ejecuté el sistema contra Pinecone y Gemini reales el 31/10/2026: 16 preguntas, k = 5, híbrido con pesos BM25/vectorial 0.5/0.5 y 10 candidatos por recuperador. La salida completa está en [`docs/evidencia/evaluacion-consola.txt`](docs/evidencia/evaluacion-consola.txt).

| Modo | Recall@5 | Precision@5 | MRR |
|---|---:|---:|---:|
| `bm25` (solo léxico) | 0.81 | 0.26 | 0.78 |
| `vectorial` (solo embeddings) | 1.00 | 0.40 | 0.92 |
| **`hibrido`** (el sistema) | **1.00** | **0.39** | **0.92** |

Por tipo de pregunta (Recall@5 / MRR):

| Tipo (n) | `bm25` | `vectorial` | `hibrido` |
|---|---:|---:|---:|
| exacta (4): código o sigla | 1.00 / 1.00 | 1.00 / 0.80 | 1.00 / 0.88 |
| mixta (7): dato puntual con términos del texto | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 |
| parafraseada (5): sin palabras en común | 0.40 / 0.30 | 1.00 / 0.90 | 1.00 / 0.84 |

**Cómo leo estos resultados, sin exagerar:**

- **BM25 solo falla donde esperaba**: en 3 de las 5 preguntas parafraseadas, que no comparten palabras con el texto (por ejemplo, «falla muy grave» frente a «incidente crítico»). El vectorial no falla ninguna.
- **El híbrido no pierde cobertura**: mantiene Recall@5 = 1.00 y el mismo MRR que el vectorial (0.92), con 0.01 menos de Precision@5.
- **Dónde ayuda**: en los términos exactos. En «¿Qué función cumple Calidata?» el vectorial pone el documento correcto en el puesto 5 y el híbrido lo sube al 2 (MRR de las preguntas exactas: 0.80 → 0.88).
- **Dónde perjudica**: en alguna parafraseada, BM25 mete documentos que comparten una palabra suelta. En «¿Con cuánta antelación hay que cargar un local nuevo antes de abrirlo?» el vectorial acierta en el puesto 1 y el híbrido en el 5 (MRR de las parafraseadas: 0.90 → 0.84).
- **Con 16 preguntas no puedo afirmar que el híbrido sea mejor en general.** Lo que sí muestra la corrida es que no pierde cobertura en ninguno de los dos tipos de pregunta, mientras que BM25 solo la pierde en las parafraseadas.
- **Por qué la Precision@5 es baja**: cada documento se parte en pocos fragmentos (36 fragmentos en 13 documentos, 2.8 por documento en promedio) y la precisión divide siempre por 5. Un documento de 3 fragmentos, aun recuperado entero, da como máximo 3/5 = 0.60, y el de 4 fragmentos, 4/5 = 0.80. Con este dataset la métrica no puede llegar a 1.0.

### Ajuste del híbrido

`python evaluate.py --modo hibrido --candidatos N --pesos BM25 VECTORIAL` permite probar configuraciones. Probé 6 (salida en [`docs/evidencia/ajuste-hibrido.txt`](docs/evidencia/ajuste-hibrido.txt)):

| Candidatos por recuperador | Pesos BM25/vectorial | Recall@5 | Precision@5 | MRR |
|---:|---|---:|---:|---:|
| 5 | 0.5 / 0.5 | 1.00 | 0.34 | 0.88 |
| 5 | 0.4 / 0.6 | 1.00 | 0.40 | 0.88 |
| 5 | 0.3 / 0.7 | 1.00 | 0.40 | 0.88 |
| **10** | **0.5 / 0.5** | **1.00** | **0.39** | **0.92** |
| 10 | 0.4 / 0.6 | 0.94 | 0.40 | 0.89 |
| 10 | 0.3 / 0.7 | 0.94 | 0.40 | 0.89 |

Elegí **10 candidatos y 0.5/0.5** porque logra el mejor MRR (0.92) sin perder Recall@5 (1.00); con 10 candidatos y más peso al vectorial, el Recall baja a 0.94. Con 5 candidatos y 0.4/0.6 la Precision@5 es 0.01 mayor (0.40 contra 0.39), pero el MRR baja a 0.88. **Advertencia:** elegí la configuración con el mismo golden set con el que evalúo, así que los números del híbrido son algo optimistas.

## Cómo replicar el índice

**Requisitos:** Python **3.12 o 3.13** (desarrollé el proyecto y generé toda la evidencia con 3.13; con Python 3.14 falla `pip install` porque `langchain-pinecone` todavía no lo soporta), una cuenta gratuita de [Pinecone](https://app.pinecone.io) y una clave gratuita de [Google AI Studio](https://aistudio.google.com/apikey).

```bash
# 1. Clonar y crear el entorno
git clone https://github.com/cgonzalez201012/pre-entrega-4-rag-pinecone.git
cd pre-entrega-4-rag-pinecone
python3.13 -m venv .venv
source .venv/bin/activate            # en Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Configurar las claves (el .env NO se sube al repo)
cp .env.example .env                 # y completar PINECONE_API_KEY y GOOGLE_API_KEY

# 3. Verificar que todo anda (no usa claves ni red)
pytest                               # 206 passed

# 4. Crear el índice serverless (si ya existe, no lo toca)
python setup_index.py

# 5. Indexar los documentos de data/
python ingest.py                     # --dry-run para ver los fragmentos sin subir nada; --reset para rehacer el namespace

# 6. Consultar y evaluar
python consultar.py "¿Cuántos miembros hacen falta para que sesione el Comité de Gobierno de Datos?"
python evaluate.py -v --json docs/evidencia/evaluacion.json
```

`bash scripts/capturar_evidencia.sh` corre los pasos 3 a 6 (más el ajuste del híbrido) contra los servicios reales y vuelve a guardar toda la salida en `docs/evidencia/`.

**Qué obtengo:** `setup_index.py` informa el índice (`Serverless (aws, us-east-1)`, dimensión `1536`, métrica `cosine`); `ingest.py` termina con 13 archivos y 36 fragmentos; si lo repito, informa «el namespace ya estaba al dia (no se escribio nada)» (así, sin tildes, en la salida del programa). Mi índice se llama `rag-gobierno-de-datos` y mi namespace `mercado-austral`.

### Variables de entorno (`.env.example`)

| Variable | Obligatoria | Para qué |
|---|---|---|
| `PINECONE_API_KEY` | sí | Acceso a Pinecone |
| `INDEX_NAME` | sí | Nombre del índice (minúsculas, números y guiones, hasta 45 caracteres) |
| `GOOGLE_API_KEY` | sí | Embeddings `gemini-embedding-001` |
| `PINECONE_NAMESPACE` | no | Namespace dentro del índice (por defecto `mercado-austral`) |

**Diferencia con la consigna:** la consigna pide en el `.env` una clave de OpenAI (o de Anthropic). Usé `GOOGLE_API_KEY` para generar los embeddings con `gemini-embedding-001`, porque Anthropic no ofrece un modelo de embeddings propio, OpenAI pide crédito prepago y Gemini tiene capa gratuita. Para mantener los 1536 que la consigna da de ejemplo para el índice, fijé `output_dimensionality=1536` (por defecto el modelo devuelve 3072). Con métrica coseno no hace falta normalizar los vectores de dimensión reducida. No usé un LLM de generación: la consigna evalúa la recuperación, y `RAGSystem` devuelve los 5 fragmentos mejor rankeados.

## Estructura

| Archivo | Rol |
|---|---|
| `config.py` | Única fuente de configuración: modelo, dimensión, chunking, k, pesos. Lee las claves del entorno |
| `setup_index.py` | Crea el índice Serverless si no existe y verifica que uno existente sea compatible |
| `ingest.py` | Lee, fragmenta, agrega metadatos, genera embeddings y sube por lotes (idempotente) |
| `rag_system.py` | Clase `RAGSystem` con el `EnsembleRetriever` (BM25 + Pinecone) |
| `evaluate.py` | Recall@5, Precision@5 y MRR; compara los tres modos |
| `consultar.py` | Consulta desde la terminal con fuente, página y sección |
| `almacen.py`, `embeddings.py`, `errores.py` | Acceso a Pinecone, embeddings con reintentos, errores con mensaje accionable |
| `golden_set.json` | 16 preguntas con el documento esperado |
| `data/` | 13 documentos: 11 Markdown y 2 PDF de 3 páginas (ya están en el repo; `scripts/generar_pdfs.py` los regenera desde `scripts/fuentes_pdf/` y para eso necesita `pip install reportlab`, que no está en `requirements.txt`) |
| `tests/` | 206 tests con Pinecone y Gemini simulados (`tests/fakes.py`) |
| `docs/evidencia/` | Salidas reales de cada paso, guardadas con `scripts/capturar_evidencia.sh` |

## Evidencia por criterio de la rúbrica

### 1. Configuración e infraestructura cloud (15 %)

- **Índice serverless.** En `setup_index.py` consulto `has_index`; si el índice falta, lo creo con `ServerlessSpec(cloud="aws", region="us-east-1")` (la única región del plan gratuito), dimensión 1536 y métrica coseno, y espero a que quede listo. Si ya existe, verifico dimensión y métrica y no lo modifico. Puedo correrlo dos veces sin riesgo.
- **Variables de entorno seguras.** Leo las claves del entorno solo en `config.py`; `.env` está en `.gitignore`; `.env.example` no tiene valores; la configuración oculta las claves en su `repr`. `tests/test_datos.py` revisa que ningún archivo del repo contenga claves con formato de Google, Pinecone, OpenAI/Anthropic o GitHub y que ningún otro módulo de la raíz lea `os.environ`.
- **Errores accionables.** Traduzco los códigos HTTP de Pinecone (401, 403, 404, 429) a un mensaje que dice qué revisar.
- **Evidencia:** [`setup-index.txt`](docs/evidencia/setup-index.txt) · tests: `tests/test_setup_index.py`, `tests/test_config.py`. Esa salida dice «ya existía» porque la guardé después de la primera ejecución, que fue la que creó el índice; la creación la cubre `test_crea_el_indice_serverless_con_la_dimension_y_la_metrica_del_proyecto`.

### 2. Pipeline de ingesta y gestión de metadatos (25 %)

- **Formatos:** `.md`, `.txt` y `.pdf` (con la página real de cada fragmento, vía `pypdf`).
- **Chunking:** uso `RecursiveCharacterTextSplitter` midiendo en **tokens** (`tiktoken`, `cl100k_base`): 600 tokens con solapamiento de 60, dentro del rango de 500 a 800 de la consigna. En Markdown corta primero por títulos y párrafos. Resultado real: 36 fragmentos de entre 87 y 595 tokens (promedio 435.7).
- **Metadatos** (mismo esquema en todos los fragmentos, sin valores nulos, validado en cada ingesta):

  | Campo | Contenido |
  |---|---|
  | `chunk_id` | `<documento>#<hash del contenido>` |
  | `documento_id` | nombre del archivo sin extensión (es el `documento_id_esperado` del golden set) |
  | `fuente` | nombre del archivo |
  | `pagina` | página real en PDF; `1` en Markdown, que no tiene páginas |
  | `categoria` | `politica`, `roles`, `procedimiento` o `glosario` (sale del código del documento) |
  | `codigo` | código del documento, por ejemplo `GD-POL-001` |
  | `seccion` | títulos Markdown que cubre el fragmento (vacío en PDF) |
  | `chunk_index`, `tokens` | posición del fragmento y su tamaño |
  | **`text`** | **el texto original del fragmento, dentro de la metadata**, como pide la consigna |

- **Texto en la metadata:** por eso armo BM25 leyendo el namespace de Pinecone (`index.list` + `fetch`), sin una segunda base de datos.
- **Namespace:** guardo todo en `mercado-austral` y toda lectura lo especifica.
- **Ingesta por lotes e idempotente:** genero embeddings de a 20 textos, con reintento (10, 20 y 40 s) ante el límite de cuota de Gemini, y subo de a 100 vectores. El ID depende del contenido, así que reindexar lo mismo no vuelve a pedir embeddings ni a escribir, y un documento modificado solo reemplaza sus fragmentos. Borro los fragmentos obsoletos después de subir los nuevos, y si algo falla a mitad, lo ya subido se conserva.
- **Evidencia:** [`ingesta-dry-run.txt`](docs/evidencia/ingesta-dry-run.txt) (fragmentos y categoría de cada uno de los 13 documentos, más la metadata completa de un fragmento; se genera sin claves ni red con `python ingest.py --dry-run`), [`ingesta.txt`](docs/evidencia/ingesta.txt) (36 fragmentos sin cambios, 0 embebidos: la idempotencia funcionando; mi primera corrida subió 14 fragmentos y la siguiente 22 al ampliar el dataset a 13 documentos) y [`consultas.txt`](docs/evidencia/consultas.txt) (resultados con archivo, página y sección, incluidos los PDF en sus páginas 2 y 3) · tests: `tests/test_ingest.py`, `tests/test_datos.py`.

### 3. Recuperador híbrido (35 %)

- **`RAGSystem`** (`rag_system.py`) encapsula un `EnsembleRetriever` con dos recuperadores: un `BM25Retriever` (léxico) y el retriever de `PineconeVectorStore` (semántico). `RAGSystem.buscar(consulta)` devuelve los **top-5** fragmentos con posición, documento, fuente, página, sección, categoría, código y texto.
- **Fusión.** El `EnsembleRetriever` combina los dos rankings con *Reciprocal Rank Fusion*: suma `peso / (posición + 60)` por cada lista en la que aparece el fragmento. Usa posiciones y no puntajes porque los puntajes de BM25 y de coseno tienen escalas incomparables. Cada recuperador aporta 10 candidatos y yo recorto el resultado a 5.
- **Dos ajustes sobre BM25** (cada uno con su test):
  - Tokenizador propio: minúsculas, sin tildes, sin palabras vacías del español y conservando los códigos con guiones como un solo término (`gd-pro-003`). El de LangChain solo parte por espacios.
  - `BM25SoloCoincidencias` descarta los fragmentos con puntaje 0 (ninguna palabra de la consulta aparece en ellos).
- **Por qué quité las palabras vacías:** sin ellas, «qué» y «es» puntuaban fragmentos que no tenían nada que ver y metían ruido en el híbrido. Con ellas fuera, «¿Qué es Depo360?» en modo BM25 devuelve un único fragmento: el que menciona `Depo360` (ver `consultas.txt`).
- **Filtro por metadatos:** `buscar(consulta, categoria="politica")` manda el filtro a Pinecone y arma BM25 solo con esa categoría.
- **Modos:** `bm25`, `vectorial` e `hibrido`, para poder comparar.
- **Evidencia:** [`consultas.txt`](docs/evidencia/consultas.txt) (consulta híbrida, consulta BM25 y consulta filtrada por categoría) · tests: `tests/test_rag_system.py`, que incluye una integración con el `PineconeVectorStore` real contra un Pinecone en memoria.

### 4. Evaluación cuantitativa de métricas (25 %)

- **`evaluate.py`** lee `golden_set.json`, una lista de objetos `{"pregunta": ..., "documento_id_esperado": ...}` (más un campo opcional `tipo`). La consigna pide 5 preguntas; armé **16**: 4 con código o sigla, 7 con un dato puntual y 5 parafraseadas.
- **Recall@5:** 1 si el documento correcto está entre los 5 recuperados, y lo promedio entre preguntas. Como cada pregunta tiene un único documento correcto, equivale a la tasa de acierto.
- **Precision@5:** fragmentos recuperados que pertenecen al documento correcto, divididos por 5 (siempre por 5, aunque recupere menos).
- **MRR (extra):** promedio de 1 / posición del primer acierto; me sirve para distinguir dos modos con el mismo Recall@5 según qué tan arriba ponen el documento.
- **Reporte:** tabla en consola, detalle pregunta por pregunta con `-v`, y JSON con `--json`. Antes de medir verifico que los documentos del golden set estén indexados: si no lo están, falla con un mensaje en lugar de dar números falsos.
- **Evidencia:** [`evaluacion-consola.txt`](docs/evidencia/evaluacion-consola.txt), [`evaluacion.json`](docs/evidencia/evaluacion.json), [`ajuste-hibrido.txt`](docs/evidencia/ajuste-hibrido.txt) · tests: `tests/test_evaluate.py` (fórmulas, formato del golden set, reporte y línea de comandos).

## Errores comunes de la consigna y cómo los evité

| Error | Cómo lo evité |
|---|---|
| **Mismatch de dimensiones** | Una sola constante (`EMBEDDING_DIMENSION = 1536`) define el índice y los embeddings. Verifico al abrir el índice, antes de pedir embeddings (así no gasto cuota de Gemini), y otra vez antes de cada upsert. |
| **Ignorar el namespace** | Toda escritura, lectura, listado y borrado usa el namespace configurado; los otros namespaces no se tocan (lo cubre un test). |
| **Subestimar el chunking** | Fragmentos de 600 tokens con solapamiento, medidos en tokens y no en caracteres; el máximo real es 595. |

## Limitaciones

- **Golden set chico y propio.** 16 preguntas sobre un dataset sintético, con un único documento correcto por pregunta. Sirve para detectar problemas y comparar modos, no para afirmar qué tan bien funcionaría con documentos reales.
- **Ajuste sobre los mismos datos.** Elegí los parámetros del híbrido con el golden set de evaluación (ver arriba).
- **BM25 en memoria.** `RAGSystem` carga el texto del namespace al iniciar. Alcanza para cientos o pocos miles de fragmentos; con corpus mucho mayores tendría que pasar a vectores *sparse* de Pinecone (índice híbrido) en lugar de cargar el corpus completo.
- **Los tests no llaman a servicios reales.** Simulé Pinecone y Gemini; la prueba contra los servicios reales es la evidencia de `docs/evidencia/`.
- **Pinecone es eventualmente consistente.** Tras escribir, `ingest.py` espera hasta 60 s a que el conteo coincida.
- **Solo español.** La lista de palabras vacías de BM25 es del español.
- **Sin generación de respuestas.** La consigna no la pide; el paso siguiente natural sería pasar los 5 fragmentos a un LLM.
