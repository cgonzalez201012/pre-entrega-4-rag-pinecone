# Procedimiento de Cambios en la Definición de los Indicadores Críticos

**Código:** GD-PRO-005 · **Versión:** 1.0 · **Vigencia:** desde el 1 de junio de 2026 · **Propietario:** Líder de Gobierno de Datos de Mercado Austral S.A.

> Documento ficticio con fines didácticos. Mercado Austral S.A. es una empresa inventada para el dataset de la pre-entrega 4 del curso de AI Engineering.

## 1. Objetivo y alcance

Los tres indicadores críticos de la compañía, que son las ventas netas, el margen bruto y el stock disponible, deben calcularse siempre con la misma definición en todas las áreas. Este procedimiento regula cómo se cambia la definición o la regla de cálculo de cualquiera de ellos. Desarrolla el paso a paso de lo que el Glosario (GD-GLO-001) ya exige: que todo cambio sea aprobado por el Comité de Gobierno de Datos.

## 2. Ficha de definición

Cada indicador crítico tiene una ficha de definición en el catálogo de datos. La ficha contiene la fórmula, los sistemas fuente, los filtros que se aplican (por ejemplo, si se excluyen las devoluciones), la frecuencia de cálculo, el Data Owner responsable y el número de versión. Una ficha nunca se edita: cada cambio aprobado genera una versión nueva y la anterior se conserva.

## 3. Solicitud de Cambio de Indicador

Quien necesita un cambio completa una Solicitud de Cambio de Indicador, que se abrevia SCI. La SCI indica el indicador afectado, el cambio propuesto, el motivo y el impacto esperado, y se presenta al Líder de Gobierno de Datos.

## 4. Análisis de impacto

Dentro de 5 días hábiles, el Líder de Gobierno de Datos analiza junto con el Data Owner qué reportes, tableros y cálculos dependen del indicador, incluidos los que se usan para calcular objetivos comerciales y bonificaciones.

## 5. Prueba de regresión

La nueva regla se calcula en el entorno de prueba sobre los últimos 3 meses de datos históricos y se compara con la regla vigente. Toda diferencia mayor al 0,5 % debe quedar explicada por el cambio propuesto. Si no se puede explicar, la SCI se rechaza hasta aclararla.

## 6. Aprobación

La aprueba el Comité de Gobierno de Datos en su reunión ordinaria. Una SCI urgente puede tratarse en una reunión extraordinaria, convocada según las reglas de GD-ROL-001.

## 7. Comunicación y puesta en producción

El cambio se comunica a todos los usuarios de los reportes con 10 días hábiles de anticipación a su puesta en producción. En una SCI urgente, el aviso puede darse con 2 días hábiles de anticipación.

Durante los dos primeros cierres mensuales posteriores al cambio se publican las dos versiones del indicador, la anterior y la nueva, para que los usuarios puedan comparar los resultados. Esto se conoce como doble publicación.

## 8. Registro

La SCI, el resultado de la prueba de regresión y el acta de aprobación se archivan junto a la ficha de definición del indicador. El Analista de Catálogo del equipo de Gobierno de Datos es responsable de mantener ese archivo ordenado.

## 9. Historial de versiones

- **1.0 (1 de junio de 2026):** versión inicial.
