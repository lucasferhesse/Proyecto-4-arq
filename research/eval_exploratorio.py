import sys,os,math,random,statistics as st
sys.path.insert(0,'algo');import market,series,trade_original as trade_ref
class Risk:
 def __init__(self,entry=4,exit=2,stop=8,cool=64,mode=3):
  self.entry=entry;self.exit=exit;self.stop=stop;self.cool=cool;self.mode=mode;self.buf=[0]*120;self.idx=self.n=self.ss=self.sl=self.sm=self.tr=self.mr=self.want=self.h=self.lock=0
 def step(self,x):
  i=self.idx; b=self.buf;self.ss+=x-b[(i+100)%120];self.sl+=x-b[i];self.sm+=x-b[(i+60)%120];b[i]=x;self.idx=(i+1)%120;self.n+=1
  if self.n<120:return 0
  d=self.ss*120-self.sl*20;dm=x*60-self.sm
  if d>self.entry*2400:self.tr=1
  elif d<-self.exit*2400:self.tr=0
  if dm<-240:self.mr=1
  elif dm>0:self.mr=0
  want=self.tr or (self.mr and d>=-9600)
  if self.mode:
   self.lock=max(0,self.lock-1)
   if self.want:
    self.h=max(self.h,x)
    if (self.h-x>=self.stop if self.mode==3 else (self.h-x)*100>=self.stop*self.h):self.lock=self.cool;self.tr=self.mr=0;want=0
   if self.lock:want=0
   if want and not self.want:self.h=x
  self.want=bool(want)
  return 127 if want else 191

def fast(p,bot):
 cash=10000; sh=0;pend=0;peak=10000;dd=0;orders=0;wins=0;closed=0;before=10000
 for x in p:
  old=sh;cash,sh,done=market.execute(pend,x,cash,sh)
  if done:orders+=1
  if old==0 and sh>0:before=cash+sh*x+5
  if old>0 and sh==0:closed+=1;wins+=cash>before
  w=cash+sh*x;peak=max(peak,w);dd=max(dd,(peak-w)/peak)
  pend=bot.step(x)
 return (w,dd,orders,wins,closed)

a,b=[series.load_csv('tb/'+f+'.csv') for f in ['practica','practica_meta']]
cfg=[('original',trade_ref.TradeRef),('clip',lambda:Risk(8,8,0,0,0)),('risk8',lambda:Risk()),('risk8b',lambda:Risk(4,4,8,64)),('risk4',lambda:Risk(4,0,4,240)),('risk5',lambda:Risk(4,0,5,240))]
# independent seeds from existing synthetic generators (not used in parameter search)
syn={f:[series.make(f,s,2000) for s in range(100,120)] for f in series.FAMILIES}
# bootstrap first 12000 increments only, test 100 seeds, mix blocks of 64-256
boot=[]
for seed in range(100):
 rng=random.Random(10200+seed); p=rng.randint(80,190); out=[p]
 for i in range(20):
  src=rng.choice([a,b]);k=rng.randint(64,256);j=rng.randint(0,12000-k-1)
  for d in [y-x for x,y in zip(src[j:j+k],src[j+1:j+k+1])]:p=max(1,min(255,p+d));out.append(p)
 boot.append(out[:2000])
for name,m in cfg:
 print(name,'full',*[fast(x,m()) for x in [a,b]],'tail',*[fast(x[12000:],m()) for x in [a,b]])
 for f,ps in list(syn.items())+[('bootstrap',boot)]:
  rs=[fast(p,m()) for p in ps]; print(f,round(math.exp(st.mean(math.log(max(1,r[0])/10000) for r in rs)),3),round(st.mean(r[1] for r in rs),3),round(st.median(r[0] for r in rs)),sum(r[0]>10000 for r in rs),end='; ')
 print()
