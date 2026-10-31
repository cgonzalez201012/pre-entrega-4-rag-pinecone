# Procedimiento de Alta, Modificación y Baja de Clientes de Fidelización

**Código:** GD-PRO-004 · **Versión:** 1.1 · **Vigencia:** desde el 1 de marzo de 2026 · **Data Owner:** Gerente de Marketing

> Documento ficticio con fines didácticos. Mercado Austral S.A. es una empresa inventada para el dataset de la pre-entrega 4 del curso de AI Engineering.

## 1. Objetivo y alcance

Este procedimiento describe cómo se inscribe, se modifica y se da de baja a un cliente del programa de fidelización Club Austral. El maestro de clientes vive en el CRM de fidelización y se sincroniza con el POS, que identifica al cliente en cada compra. Los productores de datos son el personal de caja de las sucursales, el equipo de Marketing y los propios clientes que se inscriben por el sitio web o por la aplicación. El Data Steward del dominio pertenece al equipo de Marketing.

## 2. Datos mínimos para la inscripción

Para inscribir a un cliente se necesitan su DNI, su nombre y apellido, su fecha de nacimiento, al menos un medio de contacto (correo electrónico o celular) y la aceptación del tratamiento de sus datos. La casilla de consentimiento es obligatoria y no puede estar tildada de antemano. Las reglas completas sobre el consentimiento están en la Política de Privacidad (GD-POL-003). Sin consentimiento, la inscripción no se completa.

## 3. Validaciones en el alta

El sistema valida que el DNI tenga siete u ocho dígitos, que el correo tenga un formato correcto y que el celular tenga diez dígitos, sin el 0 ni el 15 adelante. La inscripción se bloquea si ya existe un cliente con el mismo DNI.

En las inscripciones por sitio web o por aplicación, el cliente recibe un correo con un enlace de confirmación que vence a los 7 días corridos. Si no lo confirma en ese plazo, la inscripción se descarta.

## 4. Modificaciones

El cliente puede cambiar su correo, su celular y su domicilio desde la aplicación o en cualquier caja. El DNI no se puede modificar en caja: un DNI mal cargado lo corrige únicamente el Data Steward, con una copia del documento del cliente.

## 5. Clientes duplicados y fusión

Dos registros se consideran posibles duplicados si tienen el mismo DNI, cosa que el alta bloquea, o si coinciden el nombre y apellido, la fecha de nacimiento y el celular. El Data Steward revisa los casos detectados todas las semanas. Si confirma que se trata de la misma persona, fusiona los registros dentro de 2 días hábiles.

La fusión conserva el registro más antiguo como registro dorado, suma los puntos acumulados de ambos y deja constancia de los identificadores fusionados. Una fusión solo se revierte con la aprobación del Data Owner.

## 6. Puntos del programa

Los puntos del programa vencen a los 18 meses de haber sido acumulados. Cuando se fusionan dos registros, cada lote de puntos conserva su fecha de vencimiento original.

## 7. Clientes inactivos

Un cliente que no registra compras durante 24 meses pasa a estado Inactivo. Treinta días corridos antes de ese momento se le envía un aviso para que pueda reactivarse comprando o confirmando sus datos. El plazo de conservación de los datos de los clientes inactivos y su anonimización se rigen por el Glosario (GD-GLO-001).

## 8. Bajas pedidas por el cliente

Cuando un cliente pide darse de baja del programa o que se supriman sus datos, el Data Steward registra el pedido y aplica los plazos de la Política de Privacidad (GD-POL-003). La baja de un cliente no elimina sus compras históricas, que se conservan sin datos personales identificables.

## 9. Indicadores del procedimiento

El Data Steward informa todos los meses el porcentaje de clientes con correo confirmado, cuyo objetivo es superar el 70 %, y la cantidad de duplicados detectados cada 10.000 clientes, cuyo objetivo es que sea menor a 15.

## 10. Historial de versiones

- **1.1 (1 de marzo de 2026):** se agregó la revisión semanal de duplicados y el aviso previo a la inactivación.
- **1.0 (1 de septiembre de 2025):** versión inicial.
