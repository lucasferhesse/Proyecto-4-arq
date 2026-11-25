"""compare.py - Compara las decisiones de trade.s (simulacion) con la referencia
en Python y resume las mediciones por tick (IC, ciclos, CPI, tiempo).

Uso: python3 sim/compare.py data/serie.csv sim/out/decisiones_asm.txt sim/out/perfil.csv
"""
import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "algo"))
import market      # noqa: E402
import series      # noqa: E402
from trade_ref import TradeRef   # noqa: E402

F_CLK = 25_000_000
ROUNDS = [("Ronda 1", 10e-3), ("Ronda 2", 1e-3), ("Ronda 3", 0.1e-3)]
SPI_CYCLES = 2 * 13 * 9 + 10    # CS + 8 bits a 0,96 MHz + sincronizacion (aprox.)


def main(csv_path, asm_path, prof_path, expected_n=None):
    prices = series.load_csv(csv_path)
    ref = market.run(prices, TradeRef())["decisions"]
    asm = [int(x, 16) for x in open(asm_path).read().split()]
    expected_n = len(ref) if expected_n is None else int(expected_n)
    if expected_n <= 0 or expected_n > len(ref) or len(asm) != expected_n:
        print(f"ERROR: esperadas {expected_n} decisiones; recibidas {len(asm)}; serie {len(ref)}")
        return False
    n = expected_n
    diff = [i for i in range(n) if ref[i] != asm[i]]
    print(f"Decisiones comparadas: {n}  |  distintas: {len(diff)}")
    for i in diff[:10]:
        print(f"  tick {i}: precio {prices[i]}  referencia {ref[i]:02x}  trade.s {asm[i]:02x}")

    rows = list(csv.DictReader(open(prof_path)))
    rows = [r for r in rows if 0 <= int(r["tick"]) < n]
    if sorted(int(r["tick"]) for r in rows) != list(range(n)):
        print("ERROR: perfil incompleto o ticks duplicados")
        return False
    for kind in ("decision", "tick"):
        c = [int(r[f"ciclos_{kind}"]) for r in rows]
        ic = [int(r[f"ic_{kind}"]) for r in rows]
        avg_c, avg_ic = sum(c) / len(c), sum(ic) / len(ic)
        k = max(range(len(c)), key=lambda i: c[i])
        print(f"\nHasta {'escribir DECISION' if kind == 'decision' else 'terminar el tick'}:")
        print(f"  promedio : IC = {avg_ic:7.1f}  ciclos = {avg_c:7.1f}  CPI = {avg_c / avg_ic:.3f}"
              f"  tiempo = {1e6 * avg_c / F_CLK:6.2f} us")
        print(f"  peor caso: IC = {ic[k]:7d}  ciclos = {c[k]:7d}  CPI = {c[k] / ic[k]:.3f}"
              f"  tiempo = {1e6 * c[k] / F_CLK:6.2f} us   (tick {rows[k]['tick']})")
    worst = max(int(r["ciclos_tick"]) for r in rows)
    print("\nPresupuesto por ronda (ciclos a 25 MHz, descontando ~%d de la transaccion SPI):" % SPI_CYCLES)
    for name, T in ROUNDS:
        budget = int(T * F_CLK) - SPI_CYCLES
        print(f"  {name}: {budget:7d} disponibles  peor caso usa {worst:5d} = {100 * worst / budget:5.1f} %")
    return len(diff) == 0


if __name__ == "__main__":
    sys.exit(0 if main(*sys.argv[1:5]) else 1)
