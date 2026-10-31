# Procedimiento de Gestión de Incidentes de Calidad de Datos

**Código:** GD-PRO-002 · **Versión:** 1.1 · **Vigencia:** desde el 1 de marzo de 2026 · **Propietario:** Líder de Gobierno de Datos de Mercado Austral S.A.

> Documento ficticio con fines didácticos. Mercado Austral S.A. es una empresa inventada para el dataset de la pre-entrega 4 del curso de AI Engineering.

## 1. Objetivo

Este procedimiento describe cómo se registra, se resuelve y se cierra un incidente de calidad de datos, desde que se detecta hasta que se verifica la corrección. Se complementa con la Política de Calidad de Datos (GD-POL-001), que define las severidades y los plazos máximos de resolución, y con el esquema de escalamiento de GD-ROL-001. Este documento no repite esos plazos.

## 2. Herramienta

Todos los incidentes se gestionan en la Mesa de Datos, la herramienta de tickets del equipo de Gobierno de Datos. Un incidente que no está registrado en la Mesa de Datos no se cuenta en los indicadores.

## 3. Etapas

1. **Detección.** Puede venir de una alerta automática de una regla de calidad o del reporte de un productor de datos o de una sucursal.
2. **Registro.** El Data Steward del dominio abre el ticket en la Mesa de Datos dentro de los 30 minutos de la detección.
3. **Clasificación.** Se le asigna una severidad según los criterios de GD-POL-001.

<!-- salto -->

4. **Diagnóstico.** Se identifican los registros afectados, la regla que se incumplió y desde cuándo ocurre.
5. **Corrección.** Se corrige en el sistema fuente y nunca en los reportes. Las correcciones de más de 500 registros se aplican entre las 23:00 y las 05:00, con un respaldo previo, y las autoriza el Data Owner.
6. **Verificación.** Se vuelve a ejecutar la regla de calidad que detectó el incidente. Solo si la regla pasa, el incidente puede cerrarse.
7. **Cierre.** El Data Steward cierra el ticket e indica la causa y la acción realizada.

## 4. Incidentes críticos

Un incidente crítico activa un protocolo especial:

- El Data Steward abre de inmediato la Sala de Datos, un canal de chat dedicado donde participan el Data Steward, el Data Custodian, el Data Owner y el analista de guardia del equipo de Gobierno de Datos.
- El equipo de Gobierno de Datos envía un aviso operativo a las sucursales afectadas dentro de los 30 minutos de la detección. El aviso explica el síntoma y cómo seguir operando mientras se resuelve, por ejemplo cobrando con el procedimiento manual de contingencia.
- La Sala de Datos publica el estado del incidente cada hora hasta que se resuelve.

<!-- salto -->

## 5. Informe post-incidente

Dentro de los 3 días hábiles posteriores al cierre de un incidente crítico, el Data Steward entrega un informe post-incidente con la cronología, el impacto, la causa raíz y las acciones preventivas. La causa raíz se determina con el método de los 5 porqués. El informe se presenta al Comité de Gobierno de Datos en su siguiente reunión ordinaria.

## 6. Reaperturas

Si un incidente cerrado vuelve a ocurrir dentro de los 10 días hábiles, se reabre el mismo ticket y se cuenta como reincidencia. No se abre uno nuevo.

## 7. Indicadores

- Cumplimiento de los plazos de resolución: el objetivo es 95 %.
- Tasa de reapertura: el objetivo es que sea menor al 5 %.
- Tiempo medio de resolución, por severidad.

El Líder de Gobierno de Datos publica estos indicadores en el tablero de incidentes y los incluye en el reporte mensual al Comité.

## 8. Historial de versiones

- **1.1 (1 de marzo de 2026):** se agregó el protocolo de la Sala de Datos y el informe post-incidente.
- **1.0 (1 de septiembre de 2025):** versión inicial.
