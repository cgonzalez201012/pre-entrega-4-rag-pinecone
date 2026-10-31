# Política de Calidad de Datos

**Código:** GD-POL-001 · **Versión:** 2.1 · **Vigencia:** desde el 1 de marzo de 2026 · **Propietario:** Comité de Gobierno de Datos de Mercado Austral S.A.

> Documento ficticio con fines didácticos. Mercado Austral S.A. es una empresa inventada para el dataset de la pre-entrega 4 del curso de AI Engineering.

## 1. Objetivo y alcance

Esta política define cómo Mercado Austral S.A. mide, controla y mejora la calidad de sus datos maestros y de los datos transaccionales que dependen de ellos. Su objetivo es que las decisiones comerciales, logísticas y financieras se tomen con información confiable, completa y disponible a tiempo.

Alcanza a los cinco dominios de datos maestros de la compañía: artículos, proveedores, clientes de fidelización, sucursales y estructura organizacional, y plan de cuentas. Aplica a todos los sistemas que los almacenan o consumen: el ERP corporativo, el sistema de puntos de venta (POS), el sistema de gestión de depósitos (WMS) y el CRM de fidelización. Rige para todo el personal propio y para los terceros que carguen o modifiquen datos en esos sistemas.

## 2. Dimensiones de calidad y umbrales mínimos

La compañía evalúa la calidad de sus datos en cinco dimensiones. Cada una tiene un umbral mínimo de cumplimiento, que se mide sobre los registros activos de cada maestro.

**Completitud.** Mide el porcentaje de registros que tienen cargados todos los campos obligatorios. El umbral es 98 % para el maestro de artículos y 95 % para el maestro de proveedores.

**Unicidad.** Mide que una misma entidad del mundo real no esté registrada dos veces. El umbral es cero duplicados activos: no puede haber dos artículos activos con el mismo código EAN ni dos proveedores activos con el mismo CUIT.

**Validez.** Mide que el valor cumpla el formato y las reglas del negocio. Un EAN-13 debe tener trece dígitos y un dígito verificador correcto; un CUIT debe tener once dígitos con verificador válido; las fechas se almacenan en formato AAAA-MM-DD. El umbral de validez es 99 %.

**Consistencia.** Mide que el mismo dato no se contradiga entre sistemas o entre campos. Por ejemplo, el precio de lista nunca puede ser menor que el costo de reposición, y la unidad de medida de un artículo debe ser la misma en el ERP y en el POS. El umbral de consistencia es 97 %.

**Oportunidad.** Mide que el dato esté disponible cuando se lo necesita. Un artículo aprobado debe estar operativo en todos los POS dentro de las 48 horas hábiles posteriores a su aprobación. El umbral es 95 % de cumplimiento de ese plazo.

## 3. Medición y reporte

Las reglas de calidad se ejecutan de forma automática todos los días a las 06:00 sobre los maestros críticos (artículos y proveedores) y todos los domingos a las 22:00 sobre los maestros restantes. Los resultados se guardan en el repositorio de calidad, que conserva el historial de cada regla.

El Data Steward de cada dominio publica un scorecard mensual el quinto día hábil de cada mes. El scorecard informa el cumplimiento de cada dimensión, la evolución contra los tres meses previos y la lista de los diez registros con más reglas incumplidas. El Líder de Gobierno de Datos consolida los scorecards de todos los dominios y los presenta en la reunión mensual del Comité de Gobierno de Datos.

## 4. Clasificación y resolución de incidentes

Todo incumplimiento detectado se registra como incidente de calidad y se clasifica por severidad. La severidad determina el plazo máximo de resolución, contado desde el momento de la detección.

- **Crítico:** impide vender, cobrar, facturar o recibir mercadería en una o más sucursales. Plazo de resolución: 4 horas hábiles.
- **Alto:** afecta reportes de gestión o decisiones de abastecimiento, pero no frena la operación diaria. Plazo de resolución: 2 días hábiles.
- **Medio:** afecta a un grupo reducido de registros, sin impacto en los reportes clave. Plazo de resolución: 5 días hábiles.
- **Bajo:** inconsistencias formales o estéticas. Plazo de resolución: 15 días hábiles.

Si un incidente no se resuelve dentro del plazo, el Data Steward lo escala al Data Owner del dominio, siguiendo el esquema de escalamiento definido en el documento de Roles y Responsabilidades (GD-ROL-001).

## 5. Plan de remediación

Cuando una dimensión de calidad de un maestro queda por debajo de su umbral durante dos meses consecutivos, el Data Owner del dominio debe presentar al Comité un plan de remediación dentro de los 10 días hábiles siguientes a la publicación del segundo scorecard. El plan debe incluir la causa raíz, las acciones correctivas, los responsables y las fechas comprometidas.

El Comité hace seguimiento del plan en cada reunión mensual hasta que la dimensión vuelva a superar su umbral durante dos meses seguidos. Recién entonces el plan se da por cerrado.

## 6. Excepciones

Un Data Owner puede solicitar una excepción temporal a un umbral cuando exista una causa justificada, como una migración de sistemas. La excepción debe pedirse por escrito, ser aprobada por el Comité y tener una fecha de vencimiento que no supere los 90 días corridos. Una excepción se puede renovar una sola vez, con una nueva aprobación del Comité.

## 7. Revisión de la política y auditoría

La política se revisa cada seis meses. Además, la Auditoría Interna realiza una vez por año una auditoría de calidad de datos sobre una muestra de registros de cada dominio y presenta sus hallazgos al Comité de Gobierno de Datos.

## 8. Historial de versiones

- **2.1 (1 de marzo de 2026):** se incorporó la dimensión de oportunidad y se redujo a 4 horas hábiles el plazo de los incidentes críticos, que antes era de 8 horas hábiles.
- **2.0 (1 de septiembre de 2025):** se agregó el plan de remediación obligatorio.
- **1.0 (1 de marzo de 2025):** versión inicial de la política.
