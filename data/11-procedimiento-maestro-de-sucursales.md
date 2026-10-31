# Procedimiento de Alta y Mantenimiento del Maestro de Sucursales

**Código:** GD-PRO-006 · **Versión:** 1.0 · **Vigencia:** desde el 1 de marzo de 2026 · **Data Owner:** Gerente de Operaciones

> Documento ficticio con fines didácticos. Mercado Austral S.A. es una empresa inventada para el dataset de la pre-entrega 4 del curso de AI Engineering.

## 1. Objetivo y alcance

Este procedimiento describe cómo se registran las sucursales de Mercado Austral S.A., cómo se mantienen sus datos y cómo se cierran. También cubre los cambios de la estructura organizacional y de los centros de costos, que pertenecen a los dominios de sucursales y de plan de cuentas.

## 2. Formatos de sucursal

La compañía opera tres formatos: Hiper, Super y Express. El formato determina el surtido, la zona de precios y el depósito que abastece a la sucursal.

## 3. Datos obligatorios

Toda sucursal debe tener cargados su código, su nombre, su domicilio, su formato, la superficie de ventas en metros cuadrados, el horario de atención, el depósito abastecedor, la zona de precios, el centro de costos y el nombre del gerente de la sucursal. El código de sucursal tiene cuatro dígitos, lo asigna el Data Steward en orden correlativo y nunca se reutiliza, ni siquiera si la sucursal cierra.

## 4. Alta de una sucursal nueva

El área de Operaciones presenta la solicitud al menos 20 días hábiles antes de la fecha prevista de apertura. El alta sigue cinco pasos:

1. **Solicitud.** Operaciones completa el formulario con los datos obligatorios.
2. **Código y centro de costos.** El Data Steward asigna el código y el Gerente de Finanzas aprueba el centro de costos dentro de 3 días hábiles.
3. **Configuración logística.** Se configuran el depósito abastecedor y la ruta de entrega en el WMS.
4. **Precios y surtido.** Se cargan la zona de precios y el surtido inicial en el ERP y en los POS.
5. **Prueba previa a la apertura.** Se hace una compra de prueba en cada caja y el Data Steward confirma que la sucursal figura con los mismos datos en los cuatro sistemas.

## 5. Modificaciones

Los cambios de horario, de domicilio o de gerente los aprueba el Data Steward dentro de 1 día hábil. Los cambios de zona de precios se aplican únicamente el primer lunes de cada mes. Un cambio de formato se trata como una reapertura y requiere la aprobación del Data Owner.

## 6. Cierres

En un cierre temporal, por obras o por una contingencia, la sucursal pasa al estado Cerrada temporalmente, se bloquean sus cajas y conserva su código. En un cierre definitivo, la sucursal pasa al estado Inactiva. Su historial no se elimina y su código no se vuelve a asignar.

## 7. Estructura organizacional y plan de cuentas

Los cambios en el organigrama, como una nueva gerencia o un cambio de dependencia, los informa Recursos Humanos al Data Steward dentro de los 2 días hábiles posteriores a su aprobación. El alta de un centro de costos o de una cuenta contable la aprueba el Gerente de Finanzas, que es el Data Owner del plan de cuentas, y se aplica solo al inicio de un mes contable.

## 8. Historial de versiones

- **1.0 (1 de marzo de 2026):** versión inicial.
