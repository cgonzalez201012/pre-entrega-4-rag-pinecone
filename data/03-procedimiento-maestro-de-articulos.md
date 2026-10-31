# Procedimiento de Alta y Mantenimiento del Maestro de Artículos

**Código:** GD-PRO-003 · **Versión:** 1.4 · **Vigencia:** desde el 1 de marzo de 2026 · **Data Owner:** Gerente Comercial

> Documento ficticio con fines didácticos. Mercado Austral S.A. es una empresa inventada para el dataset de la pre-entrega 4 del curso de AI Engineering.

## 1. Objetivo y alcance

Este procedimiento describe cómo se da de alta, se modifica y se da de baja un artículo en el maestro de artículos de Mercado Austral S.A. El maestro de artículos es la fuente única de verdad para el ERP, los puntos de venta (POS) y el sistema de gestión de depósitos (WMS). Aplica a los artículos de marcas de terceros y a los de marca propia, que se comercializan bajo la marca Austral Selección.

El solicitante de un alta es siempre un comprador. La revisión la hace el Data Steward del dominio de artículos, y la aprobación final, cuando corresponde, la hace el Data Owner.

## 2. Campos obligatorios

Todo artículo debe tener cargados los siguientes doce campos antes de poder aprobarse:

1. Código EAN-13, con dígito verificador correcto.
2. Descripción corta, de hasta 40 caracteres.
3. Descripción larga.
4. Marca.
5. Jerarquía mercadológica completa, en cuatro niveles: división, departamento, categoría y subcategoría.
6. Unidad de medida base.
7. Unidad de venta y factor de conversión a la unidad base.
8. Proveedor principal, identificado por su CUIT.
9. Costo de reposición.
10. Alícuota de IVA: 21 %, 10,5 % o exento.
11. Peso o volumen.
12. País de origen.

La política de calidad exige que al menos el 98 % de los artículos activos tenga todos estos campos completos.

## 3. Reglas para las descripciones

La descripción corta se escribe en mayúsculas, sin tildes ni caracteres especiales, con el formato MARCA, PRODUCTO y PRESENTACIÓN, en ese orden. Un ejemplo válido es AUSTRAL SELECCION ARROZ LARGO FINO 1KG, que tiene 38 caracteres. No se admiten abreviaturas que no estén en el glosario corporativo ni textos promocionales como "oferta" o "nuevo".

Una descripción de más de 40 caracteres es una de las causas más frecuentes de rechazo, porque el POS la trunca en el ticket y en la etiqueta de góndola.

## 4. Flujo de alta

El alta de un artículo sigue cinco pasos.

**Paso 1: solicitud.** El comprador completa el formulario de alta con los doce campos obligatorios y adjunta la ficha técnica del proveedor.

**Paso 2: validación automática.** El sistema verifica de inmediato el formato del EAN-13, la completitud de los campos y la existencia de posibles duplicados. Si alguna validación falla, la solicitud vuelve al comprador sin llegar al Data Steward.

**Paso 3: revisión del Data Steward.** El Data Steward revisa la solicitud dentro de 1 día hábil. Verifica que la jerarquía mercadológica sea coherente, que la descripción cumpla las reglas y que el costo sea razonable frente a artículos similares.

**Paso 4: aprobación del Data Owner.** Solo los artículos de marca propia requieren la aprobación adicional del Data Owner, que debe darla dentro de 2 días hábiles. Los artículos de marcas de terceros se aprueban con la revisión del Data Steward.

**Paso 5: publicación.** Una vez aprobado, el artículo se publica en el ERP y en todos los POS dentro de las 48 horas hábiles posteriores a la aprobación.

El objetivo de tiempo de ciclo, de punta a punta, es de 3 días hábiles para los artículos de marcas de terceros y de 5 días hábiles para los de marca propia.

## 5. Control de duplicados

El alta se bloquea automáticamente si ya existe un artículo con el mismo código EAN. También se bloquea y se envía al Data Steward si la combinación de marca, descripción y presentación tiene una similitud igual o mayor al 90 % con la de un artículo existente. En ese caso, el Data Steward decide si se trata de un duplicado real, que se rechaza, o de una variante legítima, que se aprueba dejando constancia del motivo.

## 6. Altas masivas

Cuando una solicitud incluye más de 50 artículos, el comprador debe usar la plantilla de carga masiva aprobada por el Data Steward. En estos casos la revisión se hace por muestreo: el Data Steward revisa el 10 % de los artículos de la solicitud, elegidos al azar. Si en la muestra encuentra más de dos errores, rechaza toda la solicitud.

## 7. Modificaciones

Los cambios de costo de reposición no se tramitan por este procedimiento: se gestionan exclusivamente mediante el proceso de actualización de listas de costos. Los cambios de descripción requieren la aprobación del Data Steward en 1 día hábil. Los cambios de jerarquía mercadológica también los aprueba el Data Steward, pero se aplican únicamente el primer día hábil de cada mes, para no alterar los reportes de gestión a mitad de período.

## 8. Baja de artículos

Un artículo no se elimina nunca físicamente del maestro. Pasa a estado Discontinuado cuando no tiene stock y no registra movimientos durante 180 días corridos. Si permanece 90 días más en estado Discontinuado sin movimientos, pasa a estado Inactivo. El historial de cada artículo se conserva durante 10 años.

## 9. Indicadores del procedimiento

El Data Steward informa mensualmente la tasa de rechazo de solicitudes, cuyo objetivo es que no supere el 8 %, y el tiempo de ciclo promedio, cuyo objetivo es que no supere los 3 días hábiles. Los motivos de rechazo más frecuentes son el EAN inválido, la jerarquía mercadológica incompleta y la descripción de más de 40 caracteres.

## 10. Historial de versiones

- **1.4 (1 de marzo de 2026):** se agregó el muestreo para altas masivas.
- **1.3 (1 de septiembre de 2025):** se incorporó el control de similitud para detectar duplicados.
- **1.0 (1 de marzo de 2025):** versión inicial.
