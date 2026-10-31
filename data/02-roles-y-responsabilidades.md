# Roles y Responsabilidades de Gobierno de Datos

**Código:** GD-ROL-001 · **Versión:** 1.3 · **Vigencia:** desde el 1 de marzo de 2026 · **Propietario:** Líder de Gobierno de Datos de Mercado Austral S.A.

> Documento ficticio con fines didácticos. Mercado Austral S.A. es una empresa inventada para el dataset de la pre-entrega 4 del curso de AI Engineering.

## 1. Propósito

Este documento define quién decide, quién ejecuta y quién controla cada aspecto del gobierno de datos en Mercado Austral S.A. Complementa a la Política de Calidad de Datos (GD-POL-001) y al Procedimiento de Alta y Mantenimiento del Maestro de Artículos (GD-PRO-003). Su objetivo es que cada dato crítico tenga un responsable identificable y que ningún incidente quede sin dueño.

## 2. Comité de Gobierno de Datos

El Comité es la máxima instancia de decisión en materia de datos. Tiene cinco miembros con voto: el Gerente de Sistemas, que lo preside, el Gerente Comercial, el Gerente de Operaciones, el Gerente de Finanzas y el Gerente de Compras. El Líder de Gobierno de Datos actúa como secretario: convoca las reuniones, prepara la agenda y redacta el acta, con voz pero sin voto.

El Comité se reúne de forma ordinaria el segundo martes de cada mes. Para sesionar se necesita quórum de tres de los cinco miembros, y las decisiones se toman por mayoría simple. En caso de empate, desempata el presidente. Una reunión extraordinaria puede ser convocada por el presidente o por dos miembros, con al menos 48 horas de anticipación.

Entre sus responsabilidades están aprobar y revisar las políticas, aprobar las excepciones a los umbrales de calidad, priorizar las iniciativas de datos, designar a los Data Owners y resolver los escalamientos de nivel 3.

## 3. Líder de Gobierno de Datos

El Líder de Gobierno de Datos reporta al Gerente de Sistemas y cuenta con un equipo de analistas. Mantiene actualizadas las políticas y procedimientos, consolida los scorecards mensuales de calidad, coordina a los Data Stewards, administra el catálogo de datos y dirige el programa de capacitación. No es dueño de ningún dominio de datos: su rol es facilitar y controlar, no decidir sobre el contenido de los maestros.

## 4. Data Owner

El Data Owner es el ejecutivo responsable, ante el Comité, por la calidad y el uso adecuado de los datos de un dominio. Cada dominio tiene un único Data Owner, y una misma persona puede serlo de hasta dos dominios.

| Dominio de datos | Data Owner |
|---|---|
| Artículos | Gerente Comercial |
| Proveedores | Gerente de Compras |
| Clientes de fidelización | Gerente de Marketing |
| Sucursales y estructura organizacional | Gerente de Operaciones |
| Plan de cuentas | Gerente de Finanzas |

El Data Owner define las reglas de negocio del dominio, aprueba los accesos de nivel restringido, aprueba las altas de artículos de marca propia, presenta los planes de remediación y designa a los Data Stewards de su dominio.

## 5. Data Steward

El Data Steward es quien opera el dominio día a día. Cada dominio tiene un Data Steward titular y uno suplente, designados por el Data Owner. Sus funciones son revisar cada mañana las alertas de calidad, aprobar o rechazar las solicitudes de alta y modificación dentro de 1 día hábil, publicar el scorecard mensual, mantener la ficha del dominio en el catálogo de datos y actuar como primer nivel de escalamiento.

Todo Data Steward nuevo debe completar un curso de capacitación de 16 horas durante los primeros 30 días desde su designación. Hasta completarlo, no puede aprobar altas de forma individual.

## 6. Data Custodian (Tecnología)

El rol de Data Custodian lo cumple el equipo de Infraestructura y Aplicaciones de TI. Mantiene los sistemas donde viven los datos, ejecuta los controles automáticos de calidad, administra los accesos según lo que apruebe cada Data Owner y realiza los respaldos. Los respaldos son diarios y se conservan durante 35 días. El Data Custodian no define reglas de negocio ni aprueba el contenido de los maestros.

## 7. Productores de datos

Son las personas que cargan o modifican datos en los sistemas: compradores, administración de proveedores, el equipo de marketing y el personal de sucursales, entre otros. Cada productor es responsable de la exactitud de lo que carga. Si detecta un error en un dato maestro, debe reportarlo al Data Steward del dominio y no corregirlo por su cuenta.

## 8. Segregación de funciones

Quien solicita o carga un registro no puede aprobarlo. Un Data Steward no puede aprobar sus propias solicitudes; en ese caso interviene el suplente. El Data Custodian no puede modificar el contenido de un maestro en producción, salvo que el Data Steward autorice la corrección por escrito.

## 9. Matriz de responsabilidades

La matriz usa la convención R (responsable de ejecutar), A (aprobador final), C (consultado) e I (informado).

| Actividad | Comité | Líder de GD | Data Owner | Data Steward | TI |
|---|---|---|---|---|---|
| Aprobar y revisar políticas | A | R | C | C | I |
| Definir reglas de calidad | I | C | A | R | C |
| Ejecutar controles automáticos | I | I | I | C | R |
| Resolver incidentes de calidad | I | I | A | R | C |
| Aprobar excepciones | A | C | R | C | I |
| Gestionar accesos | I | I | A | C | R |

## 10. Escalamiento de incidentes

El escalamiento tiene tres niveles. En el nivel 1, el Data Steward tiene 1 día hábil para resolver el incidente o escalarlo. En el nivel 2, el Data Owner tiene 3 días hábiles para resolverlo. En el nivel 3, el incidente pasa al Comité, que lo trata en la próxima reunión ordinaria o, si se trata de un incidente grave, en una reunión extraordinaria dentro de los 5 días hábiles.

Los incidentes críticos, que según la política de calidad deben resolverse en 4 horas hábiles, se escalan al Data Owner de inmediato, sin esperar a que venza el plazo del nivel 1.

## 11. Historial de versiones

- **1.3 (1 de marzo de 2026):** se incorporó la regla de capacitación obligatoria de 16 horas para los Data Stewards.
- **1.2 (1 de septiembre de 2025):** se agregó la matriz de responsabilidades.
- **1.0 (1 de marzo de 2025):** versión inicial.
