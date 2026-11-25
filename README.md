# Proyecto 4 · Pochoco Trader · Grupo 7 — versión competitiva

Arquitectura de Computadores 2026-2 · Universidad de los Andes · Profesor Jorge Gómez Mir

Integrantes: Lucas Fernández · Maximiliano Ferrando · Renato Rivadeneira · Matías Ureta.

Agente Assembly RV32E sobre Pochoco SoC (Go Board), conectado por SPI a una FPGA maestra. La versión optimizada conserva la interfaz y el hardware del repositorio de entrada. Combina tendencia 20/120, reversión media 60, stop de 8, cooldown de 64 ticks y filtro de saltos de 32. Solo procesa precios recibidos; no contiene series precargadas en el programa de competencia.

## Resultados recalculados

| Serie (20.000 ticks) | Original | Optimizado |
|---|---:|---:|
| practica.csv | $16.372 | $17.394 |
| practica_meta.csv | $14.960 | $24.317 |

127 palabras de código, 17/17 pruebas del assembler, 73/73 comparaciones de referencia y 89.254 decisiones del HEX emulado sin diferencias. **Pendiente:** testbench RTL, síntesis y placa, no reejecutados porque las herramientas FPGA no están disponibles en este entorno. No usar el PDF ni los logs históricos como evidencia de la versión optimizada.

La auditoría, decisiones metodológicas, riesgos, métricas de 389 escenarios, fuentes de pruebas y resultados se encuentran en [`research/README.md`](research/README.md). La versión original se conserva en `research/trade_original.s` y `algo/trade_original.py`.

## Uso

```bash
make hex
make verify-opt
make validate-opt
python3 algo/trade_ref.py tb/practica.csv
python3 algo/trade_ref.py tb/practica_meta.csv
```

Con OSS CAD Suite, antes de competir:

```bash
make tb
make check SERIE=tb/practica.csv N=20000 TICK=2500
make check SERIE=tb/practica_meta.csv N=20000 TICK=2500
make check SERIE=tb/peor_caso.csv N=199 TICK=2500
make profile
make bin
make prog
```

En Windows (Git Bash), agregar `PYTHON=python` si corresponde. `make prog` requiere placa conectada. **No ejecutar `make demo` durante la competencia**, pues esa variante usa precios de prueba precargados. Confirmar con el enunciado oficial completo que las reglas de recorte y comisión coinciden con el testbench incluido. La competencia real puede usar una distribución desconocida y no existe garantía de ganancia.
