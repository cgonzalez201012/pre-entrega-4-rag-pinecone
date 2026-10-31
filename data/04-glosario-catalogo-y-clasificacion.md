# Glosario, Catálogo de Datos y Clasificación de la Información

**Código:** GD-GLO-001 · **Versión:** 1.1 · **Vigencia:** desde el 1 de marzo de 2026 · **Propietario:** Líder de Gobierno de Datos de Mercado Austral S.A.

> Documento ficticio con fines didácticos. Mercado Austral S.A. es una empresa inventada para el dataset de la pre-entrega 4 del curso de AI Engineering.

## 1. Glosario

**Dato maestro.** Información de referencia sobre las entidades centrales del negocio, que cambia poco y se usa en muchos procesos. En Mercado Austral S.A. los datos maestros son artículos, proveedores, clientes de fidelización, sucursales y plan de cuentas.

**Dato transaccional.** Registro de un hecho que ocurre en un momento puntual, como una venta, una recepción de mercadería o un pago. Cada dato transaccional referencia datos maestros: si el maestro es incorrecto, la transacción también lo es.

**Data Owner.** Ejecutivo responsable de un dominio de datos ante el Comité de Gobierno de Datos. **Data Steward.** Persona que opera el dominio día a día. **Data Custodian.** Equipo de TI que mantiene los sistemas donde viven los datos.

**EAN-13.** Código de barras de trece dígitos que identifica de forma única a un artículo comercial. El último dígito es un verificador calculado a partir de los doce anteriores.

**Jerarquía mercadológica.** Clasificación de los artículos en cuatro niveles: división, departamento, categoría y subcategoría. Se usa para armar surtidos, reportes de ventas y políticas de precios.

**Scorecard.** Informe mensual que publica cada Data Steward con el cumplimiento de las dimensiones de calidad de su dominio.

**Registro dorado (golden record).** Versión única, completa y validada de una entidad, que resulta de consolidar la información de distintos sistemas.

**Linaje de datos.** Recorrido de un dato desde su sistema de origen hasta los reportes donde se consume, incluyendo las transformaciones intermedias.

## 2. Catálogo de datos

El catálogo de datos es el inventario oficial de los activos de información de la compañía. Hasta que se adopte una herramienta específica de catalogación, el catálogo se mantiene en una planilla controlada, alojada en el repositorio documental corporativo y administrada por el Líder de Gobierno de Datos.

Cada activo del catálogo tiene una ficha con los siguientes campos: nombre, descripción funcional, dominio, Data Owner, Data Steward, sistema fuente, frecuencia de actualización, clasificación de seguridad y reglas de calidad asociadas. El Data Steward de cada dominio es responsable de mantener actualizadas las fichas de su dominio y debe revisarlas al menos una vez por trimestre.

Los sistemas fuente que alimentan al catálogo son cuatro: el ERP corporativo, el sistema de puntos de venta (POS), el sistema de gestión de depósitos (WMS) y el CRM de fidelización.

## 3. Linaje de los indicadores críticos

Para los indicadores críticos de la compañía es obligatorio documentar el linaje completo. Los tres indicadores críticos son las ventas netas, el margen bruto y el stock disponible. La documentación del linaje de cada uno indica de qué sistemas toma los datos, qué transformaciones se aplican y qué Data Owner responde por cada paso. Cualquier cambio en una regla de cálculo de estos indicadores debe ser aprobado por el Comité de Gobierno de Datos.

## 4. Clasificación de la información

Todo activo de información se clasifica en uno de cuatro niveles de seguridad.

- **Público:** información que puede divulgarse sin restricciones, como el folleto de ofertas o la lista de sucursales publicada en el sitio web.
- **Interno:** información de uso general dentro de la compañía, como los procedimientos y los organigramas. No debe compartirse fuera de la empresa sin autorización.
- **Confidencial:** información cuya divulgación podría perjudicar al negocio, como los costos de reposición, los márgenes y los acuerdos comerciales con proveedores. El acceso se otorga por rol.
- **Restringido:** información personal de los clientes, como el DNI, el correo electrónico y el domicilio, y la información financiera sensible. El acceso requiere la aprobación del Data Owner y queda registrado.

Los datos de nivel restringido deben enmascararse en los entornos de desarrollo y de prueba. Está prohibido copiarlos a planillas locales o enviarlos por correo electrónico sin cifrar.

## 5. Retención de la información

Los plazos de conservación definidos por la compañía son los siguientes. Los datos transaccionales de ventas se conservan durante 10 años. Los datos de clientes de fidelización se conservan durante 5 años contados desde la última actividad del cliente, y luego se anonimizan. Los registros de acceso a los sistemas se conservan durante 12 meses. Los respaldos de los sistemas se conservan durante 35 días.

## 6. Indicadores del programa de gobierno de datos

El Comité hace seguimiento de tres indicadores del programa. El primero es el porcentaje de activos catalogados en los dominios críticos, que debe llegar al 90 % al cierre de 2026. El segundo es el cumplimiento global de calidad, es decir, el promedio de las cinco dimensiones sobre los maestros críticos, que debe mantenerse por encima del 95 %. El tercero es el tiempo medio de resolución de incidentes, que debe respetar los plazos definidos en la Política de Calidad de Datos.

## 7. Historial de versiones

- **1.1 (1 de marzo de 2026):** se agregaron los plazos de retención y los indicadores del programa.
- **1.0 (1 de septiembre de 2025):** versión inicial.
