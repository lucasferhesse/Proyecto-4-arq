"""Emulador funcional independiente para el subconjunto RV32E del agente.
Lee el HEX real; emula MMIO y BRAM de 512 palabras. NO es simulacion RTL/SPI
ni medicion de ciclos. Cuenta instrucciones retiradas por precio->DECISION.
"""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'algo'))
import trade_ref, series
MASK=0xffffffff
SPI=0x80010000
PERIPH=0x80000000

def signed(x,bits=32):
    return x-(1<<bits) if x & (1<<(bits-1)) else x

def decode(w):
    op=w&127; rd=(w>>7)&31; f=(w>>12)&7; a=(w>>15)&31; b=(w>>20)&31
    ii=signed(w>>20,12); si=signed(((w>>25)<<5)|rd,12)
    bi=signed(((w>>31)<<12)|(((w>>7)&1)<<11)|(((w>>25)&63)<<5)|(((w>>8)&15)<<1),13)
    ji=signed(((w>>31)<<20)|(((w>>12)&255)<<12)|(((w>>20)&1)<<11)|(((w>>21)&1023)<<1),21)
    return op,rd,f,a,b,ii,si,bi,ji,w

class CPU:
    def __init__(self, words):
        assert len(words)<0x5f0//4
        self.mem=words+[0xa5a5a5a5]*(512-len(words)) # force explicit initialization
        self.code=[decode(w) for w in words]; self.r=[0]*16; self.pc=0
        self.new=False;self.p=0;self.tx=0;self.event=False;self.read=False
        self.steps=0;self.start=0;self.ic=0;self.max_ic=0;self.max_total=0
        self.last_read=None; self.last_write=None
    def step(self):
        pc=self.pc; assert pc%4==0 and 0<=pc//4<len(self.code),hex(pc)
        op,rd,f,a,b,ii,si,bi,ji,w=self.code[pc//4];r=self.r;self.pc=pc+4
        val=None;self.steps+=1
        if op==0x37:val=w&0xfffff000
        elif op==0x13:
            assert a<16
            if f==0:val=r[a]+ii
            elif f==7:val=r[a]&ii
            elif f==6:val=r[a]|ii
            elif f==4:val=r[a]^ii
            else:raise AssertionError(('unsupported OPIMM',hex(w)))
        elif op==0x33:
            assert a<16 and b<16
            if f==0:val=r[a]-r[b] if (w>>30)&1 else r[a]+r[b]
            elif f==7:val=r[a]&r[b]
            elif f==6:val=r[a]|r[b]
            elif f==4:val=r[a]^r[b]
            else:raise AssertionError(('unsupported OP',hex(w)))
        elif op==0x03:
            assert a<16 and f==2
            addr=(r[a]+ii)&MASK; assert addr%4==0
            if addr==SPI:val=int(self.new)
            elif addr==SPI+4:
                assert self.new,'PRICE read without new price'
                val=self.p;self.new=False;self.read=True;self.last_read=self.steps
            else:
                assert 0x5f0<=addr<2048,hex(addr);val=self.mem[addr//4]
        elif op==0x23:
            assert a<16 and b<16 and f==2
            addr=(r[a]+si)&MASK; assert addr%4==0
            if addr==SPI+8:
                self.tx=r[b]&255;self.event=True
                if self.read:
                    self.ic=self.steps-self.last_read+1;self.max_ic=max(self.ic,self.max_ic);self.last_write=self.steps
            elif addr in (PERIPH,PERIPH+4):pass
            else:
                assert 0x5f0<=addr<2048,hex(addr);self.mem[addr//4]=r[b]
        elif op==0x63:
            assert a<16 and b<16
            x,y=r[a],r[b]
            cond={0:x==y,1:x!=y,4:signed(x)<signed(y),5:signed(x)>=signed(y),6:x<y,7:x>=y}[f]
            if cond:self.pc=pc+bi
        elif op==0x6f:
            val=pc+4;self.pc=pc+ji
        elif op==0x67:
            assert a<16;val=pc+4;self.pc=(r[a]+ii)&~1
        else:raise AssertionError(('unsupported opcode',hex(w)))
        if val is not None:
            assert rd<16
            if rd:r[rd]=val&MASK
        assert r[0]==0
    def price(self,p):
        assert not self.new and 1<=p<=255
        self.new=True;self.p=p;self.event=False;self.read=False
        begin=self.steps
        while True:
            self.step()
            assert self.steps-begin<2000,'CPU did not respond'
            if self.event:
                if self.read:break
                self.event=False # initial DECISION=0 before first price read
        total=self.steps-begin;self.max_total=max(total,self.max_total)
        return self.tx,total

def run():
    words=[int(w,16) for w in (ROOT/'sw/trade.hex').read_text().split()]
    cases={f:series.load_csv(ROOT/'tb'/f) for f in ['practica.csv','practica_meta.csv','peor_caso.csv']}
    for f in series.FAMILIES:
        for seed in [201,202,203]:cases[f'{f}-{seed}']=series.make(f,seed,2000)
    cases['constante']=[120]*2000
    cases['extremos']=[1,255]*1000
    cases['caida']=[200]*300+list(range(200,0,-1))+[1]*1000
    cases['subida']=[1]*300+list(range(1,256))+[255]*1000
    n=worst=first=other=0
    for name,p in cases.items():
        cpu=CPU(words); ref=trade_ref.TradeRef();case_worst=0
        for i,x in enumerate(p):
            got,ic=cpu.price(x);expected=ref.step(x)
            assert got==expected,(name,i,got,expected)
            if i==0:first=max(first,ic)
            else:other=max(other,ic)
        worst=max(worst,cpu.max_ic);n+=len(p)
        print(f'{name}: {len(p)} decisiones iguales; max IC PRICE->DECISION={cpu.max_ic}')
    print(f'TOTAL {n} decisiones, {len(cases)} series, 0 diferencias')
    print(f'IC max PRICE->DECISION={worst}; inicio->primer DECISION={first}; entre decisiones={other}')
    print('El conteo IC no equivale a ciclos medidos en RTL.')
if __name__=='__main__':run()
