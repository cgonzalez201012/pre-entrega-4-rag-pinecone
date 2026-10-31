#!/usr/bin/env bash
# Regenera la evidencia de docs/evidencia/ corriendo el proyecto de punta a punta con servicios REALES
# (Pinecone y Gemini). Necesita el .env completo y el entorno virtual activo.
#
# Uso (desde la raiz del repo):
#     bash scripts/capturar_evidencia.sh
#
# Cada paso guarda su salida en un archivo, asi cada criterio de la rubrica tiene su prueba.
set -uo pipefail
cd "$(dirname "$0")/.."
mkdir -p docs/evidencia

paso() { printf '\n==> %s\n' "$1"; }

paso "1/6 Tests (corren sin claves ni red)"
python -m pytest -q 2>&1 | tee docs/evidencia/tests.txt

paso "2/6 Indice serverless: lo crea si falta y no lo toca si ya existe"
python setup_index.py 2>&1 | tee docs/evidencia/setup-index.txt

paso "3/6 Ingesta (idempotente: lo que no cambio no se vuelve a embeber ni a subir)"
python ingest.py 2>&1 | tee docs/evidencia/ingesta.txt

paso "4/6 Consultas de ejemplo (hibrido, BM25 solo, y filtro por categoria)"
{
    python consultar.py "¿Cuántos miembros hacen falta para que sesione el Comité de Gobierno de Datos?"
    python consultar.py "¿Qué es Depo360?" --modo bm25
    python consultar.py "plazo para resolver un incidente" --categoria politica
} 2>&1 | tee docs/evidencia/consultas.txt

paso "5/6 Evaluacion: Recall@5, Precision@5 y MRR de BM25, vectorial e hibrido"
python evaluate.py -v --json docs/evidencia/evaluacion.json 2>&1 | tee docs/evidencia/evaluacion-consola.txt

paso "6/6 Ajuste del hibrido: 5 o 10 candidatos y tres repartos de peso"
{
    for c in 5 10; do
        for p in 0.5,0.5 0.4,0.6 0.3,0.7; do
            python evaluate.py --modo hibrido --candidatos "$c" --pesos "${p%,*}" "${p#*,}" 2>&1 \
                | grep -E "^Hibrido|^hibrido|ERROR|error" || true
        done
    done
} | tee docs/evidencia/ajuste-hibrido.txt

printf '\nListo. Evidencia guardada en docs/evidencia/\n'
