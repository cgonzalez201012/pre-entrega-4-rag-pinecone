# Procedimiento de Alta y Mantenimiento del Maestro de Proveedores

**Código:** GD-PRO-001 · **Versión:** 1.2 · **Vigencia:** desde el 1 de marzo de 2026 · **Data Owner:** Gerente de Compras

> Documento ficticio con fines didácticos. Mercado Austral S.A. es una empresa inventada para el dataset de la pre-entrega 4 del curso de AI Engineering.

## 1. Objetivo y alcance

Este procedimiento describe cómo se da de alta, se modifica y se da de baja un proveedor en el maestro de proveedores de Mercado Austral S.A. Alcanza a los proveedores de mercadería para la reventa, de servicios y de insumos. El solicitante es siempre un comprador o el área que contrata el servicio. La revisión la hace la Administración de Proveedores, que cumple el rol de Data Steward del dominio, y la aprobación final, cuando corresponde, la da el Data Owner.

## 2. Datos y documentación obligatoria

Antes de aprobar un proveedor deben estar cargados los siguientes datos:

1. CUIT, con once dígitos y dígito verificador válido.
2. Razón social.
3. Domicilio fiscal.
4. Condición frente al IVA.
5. CBU de la cuenta bancaria donde se le pagará, con el nombre del titular.
6. Condición de pago acordada.
7. Contacto comercial y contacto de cobranzas.
8. Rubro.

Además se adjunta el legajo del proveedor, que contiene la constancia de inscripción ante ARCA, el certificado de no retención si corresponde y el contrato o la carta de acuerdo comercial.

## 3. Flujo de alta

**Paso 1: solicitud.** El comprador completa el formulario de alta y adjunta el legajo.

**Paso 2: validación automática.** El sistema verifica el formato del CUIT y bloquea la solicitud si ya existe un proveedor activo con el mismo CUIT.

**Paso 3: revisión de la Administración de Proveedores.** Dentro de 2 días hábiles, verifica el legajo, compara la razón social con la constancia de ARCA y controla que el CBU esté a nombre del proveedor.

**Paso 4: evaluación de riesgo.** Se aplica solo a los proveedores críticos, que son los que proveen mercadería de marca propia o tienen compras estimadas de más de 120 millones de pesos por año. Incluye una verificación de antecedentes comerciales y financieros y la aprobación del Data Owner dentro de 3 días hábiles.

**Paso 5: habilitación.** El proveedor queda activo en el ERP y ya puede recibir órdenes de compra.

El tiempo de ciclo objetivo es de 4 días hábiles para los proveedores comunes y de 6 días hábiles para los críticos.

## 4. Cambio de datos bancarios

El cambio de CBU es la modificación más riesgosa del maestro, porque es el método más usado para desviar pagos a cuentas fraudulentas. Por eso exige tres controles:

- Un pedido por escrito del proveedor, firmado por un apoderado.
- Una contrafirma telefónica: la Administración de Proveedores llama a un teléfono que ya estaba registrado, y no al que figura en el pedido, y la confirmación la hacen dos personas distintas.
- El pago al proveedor queda bloqueado durante 3 días hábiles posteriores al cambio.

Ningún productor de datos puede modificar un CBU sin pasar por este circuito.

## 5. Otras modificaciones

Los cambios de condición de pago los aprueba el Gerente de Compras. Los cambios de domicilio o de contacto los aprueba la Administración de Proveedores dentro de 1 día hábil. Un cambio de CUIT no se tramita como modificación: se da de alta un proveedor nuevo y se inactiva el anterior.

## 6. Revisión anual del legajo

Una vez por año, la Administración de Proveedores revisa el legajo de cada proveedor crítico y verifica que su constancia de inscripción ante ARCA siga vigente. Si no puede verificarla, el proveedor pasa a estado Bloqueado y no puede recibir nuevas órdenes de compra hasta regularizar su situación.

## 7. Baja de proveedores

Un proveedor nunca se elimina del maestro. Pasa a estado Inactivo cuando no registra operaciones durante 12 meses. Un proveedor Inactivo puede reactivarse con el mismo circuito que un alta, sin repetir los documentos que sigan vigentes.

## 8. Indicadores del procedimiento

La Administración de Proveedores informa todos los meses la tasa de rechazo de solicitudes, cuyo objetivo es que no supere el 10 %, y el tiempo de ciclo promedio. Los motivos de rechazo más frecuentes son el CUIT inválido, el legajo incompleto y el CBU a nombre de un tercero.

## 9. Historial de versiones

- **1.2 (1 de marzo de 2026):** se agregó la contrafirma telefónica y el bloqueo de pagos para los cambios de CBU.
- **1.1 (1 de septiembre de 2025):** se incorporó la evaluación de riesgo de los proveedores críticos.
- **1.0 (1 de marzo de 2025):** versión inicial.
