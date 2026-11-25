# Investigación y evaluación de la versión competitiva

## 1. Alcance y reglas verificadas

Fuentes: `tb/tb_proyecto_4.sv` (testbench del curso), `rtl/pochoco_spi_slave.v`, `rtl/pochoco_mem_bram.v`, `rtl/espino_core/espino_alu.v`, `algo/market.py`, código y README de la versión recibida. No se incluyó el enunciado oficial separado ni el generador real de precios de la FPGA maestra. El PDF adjunto al repositorio corresponde a una versión anterior, no a la que se auditó. Por tanto, no se conoce la distribución del mercado oculto, cómo se elige la serie de competencia, si hay una clasificación combinada de rondas o penalizaciones adicionales fuera del testbench. Confirmar estas condiciones con el profesor antes de programar.

- Capital inicial 10.000; cero acciones. Patrimonio final: caja + acciones * último precio. No se exige liquidación final en el testbench.
- Una sola serie de precios; cada mensaje SPI de 8 bits entrega el precio actual. Los CSV de práctica tienen 20.000 ticks cada uno. El testbench usa por defecto 2.000 (configurable).
- La decisión escrita al observar p[t] se ejecuta a p[t+1], no a p[t]. Se puede pedir hasta 63 acciones; la maestra recorta compras a caja disponible y ventas a tenencia. No hay venta en corto ni deuda en el modelo. Comisión fija de 5 por orden realmente ejecutada, no por solicitud de cantidad cero tras el recorte. `0x00` mantener; `0x7f` comprar hasta 63; `0xbf` vender hasta 63. Durante el calentamiento se emite `0x00`.
- Períodos 10 ms, 1 ms y 0,1 ms; reloj 25 MHz. SPI oficial 9.500 ns; presupuesto conservador de la ronda 3 = 2.262 ciclos (división entera).
- Si una decisión no se actualiza a tiempo puede repetirse la anterior; no se asume que esto esté permitido como estrategia. Se mantiene el protocolo y se busca no perder precios.
- No se almacenan las series de práctica en el programa de competencia. Se almacenan solo los últimos 120 precios recibidos. El objetivo de demo está separado y no se usa para competir.

## 2. Auditoría de la versión recibida

La referencia `algo/trade_original.py` y el Assembly archivado `research/trade_original.s` reproducen el híbrido 20/120 con margen 8, reversión de media de 60, entrada -4 y salida >0, filtro de caída -4. Se verificó el HEX original contra la referencia en 40.199 ticks. El reporte histórico de 31.558 y el PDF de 11.413/13.851 no representan esta versión. Patrimonios recalculados de la versión recibida: 16.372 y 14.960.

| Hallazgo | Evidencia y consecuencia |
|---|---|
| Señal de tendencia con salida a -8 | Estado persistente en `tr_done` y `decide`: puede mantener posición aun cuando el precio retrocede mucho. No hay stop ni protección por salto. |
| Costos de cantidad | `afford` repite hasta 63 iteraciones y `sell_mul` hasta 63; se puede invocar `afford` dos veces por tick. Es innecesario duplicar la contabilidad cuando el testbench recorta q automáticamente. |
| Multiplicaciones por constantes | `mul_m`, `mul_l` y `mul_s` recorren los 8 bits de la constante, aunque las ventanas sean fijas. Algebraicamente, L/S=6. |
| Riesgo de latencia | En el emulador de instrucciones, el peor caso observado original fue 868 instrucciones antes de DECISION; el README declaraba 1.907 ciclos en el caso forzado, cerca de 2.262. La cifra del README no se revalidó en RTL. |
| Riesgo de comisiones | El original compra cantidades pequeñas al volver a entrar o completar la posición. El límite de 63 impide una entrada instantánea para posiciones grandes. |
| Evidencia histórica | `docs/tb_oficial_20000.txt` y perfiles corresponden a otras versiones. No deben presentarse como resultados del nuevo HEX. |
| Validación insuficiente | Los parámetros originales se ajustaron a las dos series completas. No existe una muestra real independiente de la competencia. |

No se detectó una incompatibilidad funcional del algoritmo original en las decisiones emuladas; sus debilidades son de estrategia, latencia y evidencia. No se realizó una auditoría formal exhaustiva del RTL ni del generador real, que no está adjunto.

## 3. Experimentos y selección

Se probaron decenas de miles de configuraciones (incluyen combinaciones repetidas en búsquedas aleatorias). `p4search.cpp`: 4.641 configuraciones de reversión, cruce, momentum inverso e híbridos; `adapt.cpp`: dos expertos con puntaje causal de desempeño y selección con histéresis; `long.cpp`: búsqueda de ventanas hasta 1.024, incluida tendencia pura; `regime.cpp`: filtros por volatilidad y umbrales dinámicos; `risk.cpp`: ajuste de entrada/salida, stop y cooldown. Cada programa usa solo los primeros 12.000 precios de cada serie para puntuar (4 segmentos de 3.000 por serie, reinicio de capital y estado), aunque imprime también los resultados completos y sufijos para evaluación exploratoria. La búsqueda está limitada a estrategias sencillas y no es un óptimo global. No se implementaron indicadores populares por sí mismos ni modelos ML sin ventaja demostrada. El generador sintético del repositorio NO es el generador de la competencia.

Las búsquedas mostraron un problema de generalización: por ejemplo, una reversión tras caída de 3 en 3 ticks, con salida 2 sobre media de 32, dio 27.017 y 9.828 en las dos series (sufijos 12.156 y 6.595). La mejor reversión por cruces de algunas ventanas obtuvo alrededor de 31.975 en práctica y 6.207 en meta. Expertos adaptativos y ventanas más largas no dieron una mejora suficientemente equilibrada. Se prefirió la familia de control de riesgo porque mantenía el híbrido original, reducía riesgo de cola y tenía resultados mejores en ambos archivos completos. El stop de 8, cooldown de 64 y umbrales 4/2 fueron la primera configuración de `risk.cpp` según la función de entrenamiento por rendimiento logarítmico, drawdown y equilibrio entre las dos series. `eval_exploratorio.py` compara variantes sin filtro de salto. Tras observar la alternancia extrema se añadió una protección simple, umbral 32, comprobada sobre nuevas semillas 400–419. El umbral de shock se eligió como control estructural, no como óptimo estadístico.

Importante: los últimos 8.000 ticks no se usaron para puntuar configuraciones en las búsquedas C++, pero sí fueron examinados durante la comparación y selección; no son un conjunto de prueba completamente ciego. Además, el original ya se había ajustado a las dos series completas. Se usaron nuevas semillas sintéticas como validación posterior a congelar la versión final, sin ajustar de nuevo los parámetros. Bootstrap de los sufijos no equivale a nuevas series reales. No se afirma que una familia de precios sea más probable que otra.

### Señales estadísticas observadas

Las dos series tienen muchos incrementos cero (55,98% y 60,55%), autocorrelación lag 1 de diferencias -0,112 y -0,079 y lag 2 de -0,017 y -0,043. La reversión a 16–64 ticks es más visible en práctica que en meta. No hay prueba de periodicidad explotable ni de predictibilidad estable en la serie oculta. La autocorrelación lag 1 no basta porque la orden se ejecuta en el próximo precio y captura la variación posterior. Los datos no proporcionan volumen, libro de órdenes ni múltiples activos. No se usa información futura.

## 4. Solución integrada

`sw/trade.s` conserva el buffer circular y calcula tres sumas móviles en O(1). Se fija el objetivo de posición:

1. Calentamiento de 120 muestras sin operar.
2. Tendencia se activa si media20 − media120 > 4; se desactiva si < -2; en medio mantiene estado.
3. Reversión se activa si p − media60 < -4 y se desactiva si p > media60. Se permite si media20 − media120 >= -4, o si ya hay tendencia positiva. El objetivo es la unión de tendencia y reversión filtrada.
4. Si el precio cae 8 unidades respecto del máximo observado desde que se activó el objetivo comprado, se fuerza salida, se reinician estados y se esperan 64 ticks (incluye el tick del disparo). Un salto absoluto >=32 entre precios consecutivos activa la misma protección; si persiste, el contador se reinicia. No es stop garantizado al precio indicado: hay un tick de retraso.
5. Con objetivo comprado se pide hasta 63; fuera de mercado se pide vender hasta 63. La maestra ejecuta solo lo que alcanza. Las solicitudes sin fill equivalen económicamente a mantener, no generan comisión según el testbench. Si el enunciado completo prohíbe solicitudes sin fill o impone otra penalización, esta simplificación debe revisarse.

La aritmética usa `6*sum20 - sum120` (tres sumas y resta) y `60*p = (16*p-p)*4`. No hay MUL/DIV/shift ni lazos por orden. Se conservan RTL, SPI, pines, reloj, memoria 512 palabras. 127 palabras de programa (508 bytes); RAM de trabajo: 120 palabras (480 bytes) en 0x600–0x7DF + dos palabras en 0x5F0–0x5F7. Sin superposición; máximo precio 255. El demo también ensambla, pero jamás debe programarse durante competencia.

## 5. Resultados reproducibles

| Serie completa | Original | Optimizado | Órdenes orig/nuevo | DD% orig/nuevo | % episodios cerrados ganadores orig/nuevo |
|---|---:|---:|---:|---:|---:|
| práctica | 16.372 | 17.394 | 373 / 517 | 36,76 / 23,04 | 61,45 / 58,72 |
| meta | 14.960 | 24.317 | 216 / 416 | 28,55 / 31,13 | 52,54 / 50,00 |

El porcentaje de episodios ganadores se calcula desde una entrada estando sin acciones hasta quedar de nuevo sin acciones, con comisiones. No es el porcentaje de órdenes individuales y excluye posiciones abiertas al final. El porcentaje baja en las dos series aunque aumenta el patrimonio; importa el tamaño de ganancias/pérdidas, no solo la tasa de aciertos. Las comisiones suben de 1.865 a 2.585 y de 1.080 a 2.080 respectivamente. La mejora es neta de esas comisiones. No todas las métricas mejoran.

| Grupo posterior a selección | Casos | Nuevo gana al original | Factor geométrico original/nuevo | DD% promedio original/nuevo |
|---|---:|---:|---:|---:|
| Sintéticas (7 familias x 20 semillas) | 140 | 105 | 0,542 / 1,937 | 55,2 / 28,2 |
| Las mismas trayectorias escaladas a 80–220 | 140 | 113 | 0,566 / 1,342 | 38,7 / 16,4 |
| Bootstrap de sufijos (bloques de incrementos) | 100 | 50 | 0,978 / 1,014 | 15,5 / 14,0 |

El factor geométrico es exp(media(log(Wfinal/10000))). No es probabilidad de ganar. Las dos filas sintéticas están correlacionadas entre sí (mismas trayectorias reescaladas). Bootstrap mantiene dependencia dentro del bloque, altera la secuencia entre bloques, es solo estrés y no una distribución validada. En bootstrap la mediana baja de 9.787,5 a 9.722 y el mínimo de 6.436 a 6.158; la ventaja no es sistemática. El CSV incluye desviación estándar, mediana, peor caso y empates por grupo. En los sufijos explorados, práctica pierde frente al original (10.992 vs 11.271), meta mejora (14.412 vs 10.049). Una caída instantánea fuerte puede causar pérdidas superiores al 90% incluso con stop; alternancia 1/255 mejora de 84 a 10.000; en subida gradual mejora de 10.000 a 153.516; precio constante y caída monótona dan 10.000 para ambos. Los escenarios extremos son artificiales y no estimaciones de rentabilidad real.

## 6. Verificación y límites

- Assembler: 17/17; 127 palabras; referencia incremental contra ventanas directas: 73/73 series.
- El emulador de `research/verify_hex.py` interpreta instrucciones del HEX, incluyendo memoria con basura inicial, registros RV32E, ramas y MMIO. 89.254 decisiones en 28 series, cero diferencias frente a Python. No emula el RTL ni SPI a nivel de ciclos.
- Conteo máximo observado entre leer PRICE y escribir DECISION: 76 instrucciones (original: 868 en pruebas). Entre decisiones: 91, excluyendo inicio. Desde inicio hasta primera decisión: 405 instrucciones. Estas cifras no son mediciones de ciclos de reloj. Por inspección, después de leer PRICE no existe ningún bucle en el nuevo programa. Con reloj y microarquitectura originales, la carga computacional debería ser mucho menor, pero hace falta medición RTL real.
- No se dispone de Icarus, Yosys ni nextpnr en este entorno. `make tb` falla por falta de Icarus. No se afirma 4/4 en la versión nueva ni Fmax ni síntesis realizada. El RTL y pinout son idénticos al ZIP recibido. Confirmar en Go Board, incluyendo primer tick, reset y tres rondas.
- El nuevo algoritmo sigue siendo all-in/all-out con entrada y salida gradual por el tope 63. Riesgo residual alto en mercados erráticos, cambios de régimen, gaps y caídas entre ticks. Un stop absoluto depende de la escala de precios. No es un sistema óptimo ni una garantía del primer lugar.

## 7. Reproducción (desde raíz)

```bash
make hex
make verify-opt       # assembler, referencia y emulador de HEX; solo Python
make validate-opt     # 389 casos (280 sintéticos, 100 bootstrap, 5 estrés, 4 práctica)
python3 algo/trade_ref.py tb/practica.csv
python3 algo/trade_ref.py tb/practica_meta.csv
# Repetir búsquedas, requiere C++17:
g++ -O3 -std=c++17 research/risk.cpp -o /tmp/risk && /tmp/risk
# Repetir con p4search.cpp, adapt.cpp, long.cpp, regime.cpp
# Verificación real antes de competir (requiere OSS CAD Suite):
make tb
make check SERIE=tb/practica.csv N=20000 TICK=2500
make check SERIE=tb/practica_meta.csv N=20000 TICK=2500
make check SERIE=tb/peor_caso.csv N=199 TICK=2500
make profile
make bin
make prog             # solo después de pasar pruebas; placa conectada
```

`sim/compare.py` ahora exige N decisiones y N filas de perfil; `make` regenera los precios al cambiar SERIE; el testbench propio falla si detecta atraso. El testbench oficial se conserva sin cambios. El informe PDF histórico del repositorio se archivó en `docs/` y no debe usarse como informe de esta versión.

Para volver a la versión original: copiar `research/trade_original.s` a `sw/trade.s`, copiar `algo/trade_original.py` a `algo/trade_ref.py`, ejecutar `make hex` y repetir validación física. Conservar una copia del ZIP antes de sobrescribir.
