"""Validacion posterior a congelar ENTRY=4 EXIT=2 STOP=8 COOL=64 SHOCK=32.
Las semillas 400..419 no participaron en la busqueda; son escenarios hipoteticos,
no una muestra del mercado oculto. Los bloques usan solo sufijos de practica.
"""
import csv, math, random, statistics as st, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'algo'))
import market,series,trade_ref,trade_original

def measure(p,bot):
    cash,sh,pend,peak,dd,orders,wins,closed=10000,0,0,10000,0.,0,0,0
    before=10000; absdd=0; maxw=10000
    for x in p:
        old=sh;cash,sh,done=market.execute(pend,x,cash,sh)
        orders+=done
        if old==0 and sh>0: before=cash+sh*x+5
        if old>0 and sh==0: closed+=1; wins+=cash>before
        w=cash+sh*x;peak=max(peak,w);maxw=max(maxw,w);dd=max(dd,(peak-w)/peak);absdd=max(absdd,peak-w)
        pend=bot.step(x)
    return dict(final=w,drawdown=dd,drawdown_abs=absdd,orders=orders,fees=orders*5,wins=wins,closed=closed,maxw=maxw)

def stats(rows):
    a=[r['original_final'] for r in rows]; b=[r['optimizado_final'] for r in rows]
    geo=lambda xs:math.exp(st.mean(math.log(max(x,1)/10000) for x in xs))
    return dict(n=len(rows),geo_original=geo(a),geo_optimizado=geo(b),median_original=st.median(a),median_optimizado=st.median(b),stdev_original=st.pstdev(a),stdev_optimizado=st.pstdev(b),worst_original=min(a),worst_optimizado=min(b),wins_vs_original=sum(y>x for x,y in zip(a,b)),ties=sum(y==x for x,y in zip(a,b)),dd_original=st.mean(r['original_drawdown'] for r in rows),dd_optimizado=st.mean(r['optimizado_drawdown'] for r in rows),positive_original=sum(x>10000 for x in a),positive_optimizado=sum(x>10000 for x in b))

def main():
    a,b=[series.load_csv(ROOT/'tb'/f) for f in ['practica.csv','practica_meta.csv']]
    cases=[('practica_completa','practica',a),('practica_completa','meta',b),('sufijo_explorado','practica',a[12000:]),('sufijo_explorado','meta',b[12000:])]
    for f in series.FAMILIES:
        for seed in range(400,420):
            p=series.make(f,seed,2000);cases.append(('sintetica_'+f,str(seed),p))
            p=[80+round((x-1)*140/254) for x in p];cases.append(('rango80_220_'+f,str(seed),p))
    for seed in range(100):
        rng=random.Random(40400+seed);p=rng.randint(80,190);out=[p]
        while len(out)<2000:
            src=rng.choice([a,b]);k=rng.randint(64,256);j=rng.randint(12000,len(src)-k-1)
            for x,y in zip(src[j:j+k],src[j+1:j+k+1]):p=max(1,min(255,p+y-x));out.append(p)
        cases.append(('bootstrap_sufijos',str(seed),out[:2000]))
    stress={'constante':[120]*2000,'alternancia':[1,255]*1000,'bajista': [max(1,255-i//8) for i in range(2000)],'alcista':[min(255,1+i//8) for i in range(2000)],'crash':[180]*150+[min(255,180+i//2) for i in range(200)]+[20]*1650}
    for k,p in stress.items():cases.append(('estres',k,p))
    rows=[]
    for group,name,p in cases:
        row=dict(group=group,name=name,ticks=len(p))
        for label,bot in [('original',trade_original.TradeRef()),('optimizado',trade_ref.TradeRef())]:row.update({label+'_'+k:v for k,v in measure(p,bot).items()})
        rows.append(row)
    out=ROOT/'research';
    with (out/'validation_cases.csv').open('w',newline='') as fh:
        w=csv.DictWriter(fh,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    groups={g:[r for r in rows if r['group']==g] for g in dict.fromkeys(r['group'] for r in rows)}
    groups['sinteticas_total']=[r for r in rows if r['group'].startswith('sintetica_')]
    groups['rango80_220_total']=[r for r in rows if r['group'].startswith('rango80_220_')]
    ss=[dict(group=g,**stats(rs)) for g,rs in groups.items()]
    with (out/'validation_summary.csv').open('w',newline='') as fh:
        w=csv.DictWriter(fh,fieldnames=list(ss[0]));w.writeheader();w.writerows(ss)
    for r in rows[:4]+groups['estres']:print(r)
    for r in ss:print(r['group'],r['n'],'geo',round(r['geo_original'],3),round(r['geo_optimizado'],3),'med',r['median_original'],r['median_optimizado'],'wins',r['wins_vs_original'],'dd',round(r['dd_original'],3),round(r['dd_optimizado'],3),'worst',r['worst_original'],r['worst_optimizado'])
    print('Total casos:',len(rows),'max W',max(r[x+'_maxw'] for r in rows for x in ['original','optimizado']))
if __name__=='__main__':main()
