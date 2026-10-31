# Política de Seguridad y Acceso a los Datos

**Código:** GD-POL-002 · **Versión:** 1.2 · **Vigencia:** desde el 1 de marzo de 2026 · **Propietario:** Gerente de Sistemas de Mercado Austral S.A.

> Documento ficticio con fines didácticos. Mercado Austral S.A. es una empresa inventada para el dataset de la pre-entrega 4 del curso de AI Engineering.

## 1. Objetivo y alcance

Esta política define quién puede acceder a los datos de Mercado Austral S.A., con qué nivel de permiso y bajo qué controles. Aplica a todo el personal propio, a los contratistas y a los proveedores que tengan acceso a los sistemas de la compañía: el ERP corporativo, el sistema de puntos de venta (POS), el sistema de gestión de depósitos (WMS) y el CRM de fidelización. Complementa la clasificación de la información que figura en el Glosario (GD-GLO-001) y la segregación de funciones definida en el documento de Roles y Responsabilidades (GD-ROL-001).

## 2. Niveles de permiso

Cada acceso se otorga con uno de cuatro niveles de permiso. **Lectura** permite consultar datos. **Carga** permite crear y modificar registros. **Aprobación** permite aprobar solicitudes de alta o de cambio. **Administración** permite configurar el sistema, los roles y los usuarios.

Siempre se otorga el nivel mínimo necesario para la tarea, que es el principio de mínimo privilegio. Una misma persona no puede tener a la vez los niveles Carga y Aprobación sobre el mismo maestro.

## 3. Solicitud y aprobación de accesos

Todo acceso se pide con el formulario FA-07, llamado Solicitud de acceso a datos, que se presenta a través de la Mesa de Ayuda de TI. Lo completa el jefe directo del usuario e indica el sistema, el nivel de permiso, el motivo y, si el acceso es temporal, la fecha de vencimiento.

Quién aprueba depende de la clasificación de los datos a los que se accede:

- **Datos internos:** aprueba el jefe directo. Plazo de atención: 1 día hábil.
- **Datos confidenciales:** aprueba el Data Owner del dominio. Plazo de atención: 2 días hábiles.
- **Datos restringidos:** aprueba el Data Owner del dominio y el acceso queda registrado. Plazo de atención: 2 días hábiles.

El equipo de Infraestructura y Aplicaciones de TI, que cumple el rol de Data Custodian, configura el acceso recién cuando recibe la aprobación correspondiente.

## 4. Autenticación

Cada usuario se identifica con un usuario y una contraseña personales. Las contraseñas tienen un mínimo de 12 caracteres y se cambian cada 90 días. La autenticación multifactor, conocida como MFA, es obligatoria en los sistemas que contienen datos restringidos y para cualquier acceso remoto a través de la VPN corporativa.

Las cuentas compartidas o genéricas están prohibidas. La única excepción son las cuentas de servicio que usan las integraciones entre sistemas, y cada una debe tener un responsable designado por nombre.

## 5. Cuentas inactivas y bloqueo de sesión

Una cuenta que no se usa durante 60 días corridos se bloquea automáticamente. Para reactivarla, el usuario debe pedirlo a la Mesa de Ayuda de TI con la aprobación de su jefe directo. Además, la sesión de cada usuario se bloquea sola después de 10 minutos sin actividad.

## 6. Bajas y cambios de puesto

Cuando una persona se desvincula de la compañía, Recursos Humanos informa la baja a TI y todos sus accesos se revocan dentro de las 24 horas posteriores. Cuando una persona cambia de puesto, se revocan los accesos del puesto anterior que no se justifiquen en el nuevo. Los accesos de los contratistas se dan de baja el último día de su contrato.

## 7. Revisión trimestral de accesos

Cada trimestre, el Data Custodian entrega a cada Data Owner la lista de las personas que tienen acceso a su dominio. El Data Owner debe confirmar o rechazar cada acceso dentro de 5 días hábiles. Los accesos que no se confirman en ese plazo se revocan. El Líder de Gobierno de Datos presenta los resultados de la revisión al Comité de Gobierno de Datos.

## 8. Accesos privilegiados

Las credenciales de administración de los sistemas se guardan en la bóveda de credenciales. Para usarlas, el administrador debe pedirlas prestadas con la aprobación del Gerente de Sistemas, y la sesión queda grabada. Cada vez que se devuelven, la bóveda cambia la credencial de forma automática.

## 9. Registros de acceso

Los sistemas registran quién accedió, a qué dato y en qué momento. Los administradores no pueden modificar esos registros, que se conservan durante el plazo definido en el Glosario (GD-GLO-001). La Auditoría Interna puede pedirlos en cualquier momento.

## 10. Incumplimientos

Compartir una contraseña, acceder a datos sin autorización o copiar datos restringidos a un medio no autorizado es una falta grave. Cada caso se informa a Recursos Humanos y a la Gerencia de Sistemas.

## 11. Historial de versiones

- **1.2 (1 de marzo de 2026):** se agregó el bloqueo automático de las cuentas inactivas.
- **1.1 (1 de septiembre de 2025):** la autenticación multifactor pasó a ser obligatoria para los datos restringidos.
- **1.0 (1 de marzo de 2025):** versión inicial.
