#!/usr/bin/env python3
"""Original procedural audio, deterministic seeds, no borrowed recordings or melodies."""
import argparse, json, math, hashlib, subprocess, zipfile, csv, io, shutil
from pathlib import Path
from functools import lru_cache
import numpy as np
from scipy import signal
from scipy.io import wavfile

SR=44100
TAU=2*np.pi
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'out'
BANK=[]
RNG=np.random.default_rng(401016)

def tvec(d): return np.arange(max(2,round(d*SR)),dtype=np.float64)/SR

def filt(x,lo=None,hi=None):
    if lo and hi: sos=signal.butter(2,[lo,hi],btype='bandpass',fs=SR,output='sos')
    elif lo: sos=signal.butter(2,lo,btype='highpass',fs=SR,output='sos')
    else: sos=signal.butter(2,hi,btype='lowpass',fs=SR,output='sos')
    return signal.sosfilt(sos,x,axis=0)

def noise(d,lo=None,hi=8000):
    x=RNG.normal(0,1,len(tvec(d)))
    x=filt(x,lo,hi)
    return x/(np.sqrt(np.mean(x*x))+1e-9)*.35

def fade(x,a=.003,r=.045):
    x=x.copy();n=len(x);aa=min(round(a*SR),n//2);rr=min(round(r*SR),n//2)
    if aa: x[:aa]*=np.linspace(0,1,aa)**.7
    if rr: x[-rr:]*=np.linspace(1,0,rr)**1.5
    return x

def tone(d,f=100,fend=None,decay=4):
    t=tvec(d)
    fs=np.full(len(t),f) if fend is None else f*(fend/f)**(t/max(d,1e-3))
    return np.sin(TAU*np.cumsum(fs)/SR)*np.exp(-decay*t)

def mixat(dst,src,start=0,gain=1):
    i=max(0,round(start*SR));n=min(len(src),len(dst)-i)
    if n>0: dst[i:i+n]+=src[:n]*gain

def ring(d,base=470):
    t=tvec(d);x=np.zeros(len(t))
    for j,ratio in enumerate([1,1.483,2.317,3.93,5.61,7.18]):
        f=base*ratio*RNG.uniform(.98,1.02)
        x+=np.sin(TAU*f*t+RNG.random())*np.exp(-t*(3+j*2))/(1+j)**1.2
    return x

def thump(d=1,f=75): return tone(d,f,f*.48,5)+noise(d,None,300)*np.exp(-tvec(d)*10)

def gun(kind):
    settings={'bolt':(.85,82,1800,.18),'hbolt':(1.05,59,1400,.24),'auto':(.55,130,3800,.085),'slug':(.65,100,2600,.12),'shoota':(.7,72,2200,.15),'cannon':(2.8,43,950,.6),'rail':(1.65,56,2400,.32)}
    d,f,cut,dec=settings[kind];f*=RNG.uniform(.93,1.07)
    t=tvec(d);x=noise(d,60,cut)*np.exp(-t/dec)*1.2
    x+=noise(d,2500,11000)*np.exp(-t/.013)*.55
    x+=tone(d,f,f*.62,1/dec)*.65
    if kind in ('bolt','hbolt'):
        mixat(x,noise(.14,1500,6800)*np.exp(-tvec(.14)*25),.018,.25)
        mixat(x,ring(.24,800),.095,.13)
        mixat(x,thump(.3,130),.075,.34)
    if kind in ('cannon','rail'):
        x+=noise(d,25,130)*np.exp(-t/.7)*.6
        for delay in [.14,.29,.51]:mixat(x,noise(.65,60,900)*np.exp(-tvec(.65)*5),delay,.15)
    return fade(np.tanh(x*1.35),.0006,.08)

def energy(kind):
    cfg={'las':(.4,1600,500),'plasma':(1.1,240,60),'pulse':(.55,850,250),'gauss':(.9,650,170),'shur':(.35,2700,2200),'splint':(.4,3300,1600),'sonic':(1.15,150,110),'organic':(.7,110,60),'lasc':(1.65,380,75),'melta':(1.4,330,90)}
    d,f,e=cfg[kind];t=tvec(d);f*=RNG.uniform(.94,1.06)
    if kind=='organic':
        x=noise(d,150,1700)*np.exp(-t*9)*(1+.6*np.sin(TAU*29*t))+tone(d,125,48,9)
    elif kind in ('shur','splint'):
        x=noise(d,2300,10000)*np.exp(-t*18)
        x+=.16*np.sin(TAU*(f*t+200*t*t))*np.exp(-t*22)
        if kind=='shur':
            mixat(x,noise(.08,3000,9000),.045,.35);mixat(x,noise(.06,4000,10000),.1,.23)
    elif kind=='gauss':
        x=noise(d,600,6500)*(.3+.7*np.maximum(0,np.sin(TAU*(37*t+20*t*t))))*np.exp(-t*5)
        x+=.2*tone(d,f,e,5)
    elif kind=='sonic':
        x=(np.sin(TAU*f*t+4*np.sin(TAU*83*t))+.5*np.sin(TAU*f*1.498*t))*np.exp(-t*4)
        x=filt(np.tanh(x*2),50,2600)
    else:
        x=noise(d,600 if kind=='las' else 80,6500 if kind=='las' else 2400)*np.exp(-t*(16 if kind=='las' else 5))
        x+=.28*tone(d,f,e,8 if kind=='las' else 4)
        x+=.15*noise(d,2500,11000)*np.exp(-t*4)
        if kind in ('plasma','melta','lasc'): x+=.5*thump(d,60)
    return fade(np.tanh(x*1.35),.001,.06)

def explosion(size=1):
    d=1.1+size*1.0;t=tvec(d)
    x=noise(d,25,1200)*np.exp(-t/(.22+size*.18))
    x+=noise(d,1700,9000)*np.exp(-t/.022)*.7
    x+=tone(d,63-size*8,28,2.8/size)*.6
    for _ in range(int(9*size)):
        length=RNG.uniform(.025,.12)
        mixat(x,noise(length,600,6500)*np.exp(-tvec(length)*35),RNG.uniform(.12,d*.8),.13)
    return fade(np.tanh(x*1.4),.001,.12)

def impact(kind):
    d={'clang':1.3,'chain':1.0,'power':1.2,'hit':.5,'thud':.8,'armthud':1.0,'sword_swing':.45,'parry':.9,'hammer':1.45,'stab':.5,'armor_step':.65,'dread_step':1.5,'titan_step':2.8}.get(kind,.8)
    t=tvec(d)
    if kind=='clang' or kind=='parry':
        x=ring(d,RNG.uniform(400,760))*.5+noise(d,2200,12000)*np.exp(-t*95)*.5
        x+=thump(d,140)*.15
    elif kind=='chain':
        freq=100+35*np.sin(np.pi*t/d)
        phase=TAU*np.cumsum(freq)/SR
        x=signal.sawtooth(phase)*(.5+.5*np.sin(TAU*39*t))*.5
        x+=noise(d,1100,6200)*.6
        x*=np.exp(-t*4)
        x+=.4*thump(d,90)
    elif kind=='power':
        x=ring(d,600)*.35+noise(d,700,8000)*np.exp(-t*7)*.35+thump(d,70)*.5
    elif kind=='sword_swing':
        x=noise(d,400,6000)*np.sin(np.pi*t/d)**2
    elif kind in ('hammer','dread_step','titan_step'):
        x=thump(d,42 if kind=='titan_step' else 65)*1.1+ring(d,120 if kind=='titan_step' else 230)*.25
        mixat(x,noise(.28,250,2800)*np.exp(-tvec(.28)*10),.11,.3)
        if kind=='titan_step': x+=noise(d,30,300)*np.exp(-t*2)*.4
    else:
        x=thump(d,95 if kind in ('hit','stab') else 60)*.7
        x+=noise(d,800,3200)*np.exp(-t*25)*.3
        if kind in ('armthud','armor_step'): x+=ring(d,360)*.12
    return fade(np.tanh(x*1.4),.001,.05)

def engine(kind,d=6):
    t=tvec(d);base={'tank':38,'dread':51,'titan':28,'dropship':68,'hover':105,'chain':95,'flame':35,'warp':46}.get(kind,55)
    x=np.zeros(len(t))
    for h in range(1,10):
        f=round(base*h*d)/d
        x+=np.sin(TAU*f*t+0.5*np.sin(TAU*round((1+h*.15)*d)/d*t))/(h**1.2)
    if kind in ('tank','dread','titan'): x*=.7+.3*np.sin(TAU*round(base*.36*d)/d*t)**2
    n=noise(d,80,4000 if kind in ('dropship','flame') else 1700)
    x=.3*filt(np.tanh(x*1.7),30,1800)+n*.7
    if kind=='dropship':x+=.18*np.sin(TAU*round(730*d)/d*t)
    if kind=='warp':x+=.18*np.sin(TAU*round(71*d)/d*t)*np.sin(TAU*round(53*d)/d*t)
    return x

def loop_join(x,seconds=.08):
    # Crossfade the overlap and remove it. Returned sample count is authoritative.
    k=min(round(seconds*SR),len(x)//5)
    w=np.linspace(0,1,k)
    y=x[:-k].copy();y[:k]=x[-k:]*(1-w)+x[:k]*w
    edge=min(128,len(y)//4)
    delta=y[-1]-y[0]
    y[:edge]+=delta*np.linspace(1,0,edge)*.5
    y[-edge:]-=delta*np.linspace(0,1,edge)*.5
    return y

def aircraft(kind):
    d={'approach':6.0,'land':4.0,'depart':5.0,'ramp':2.2,'pod':2.2}[kind]
    t=tvec(d)
    if kind=='ramp':
        x=noise(d,100,1600)*np.sin(np.pi*t/d)**.6*.35
        x+=.15*np.sin(TAU*(130*t+15*t*t))*np.sin(np.pi*t/d)
        mixat(x,impact('armthud'),1.6,.5)
    elif kind=='pod':
        x=noise(d,500,6800)*(np.minimum(t/1.3,1)**2)*np.exp(-np.maximum(t-1.25,0)*10)*.6
        mixat(x,explosion(.9),1.2,.9)
    else:
        x=engine('dropship',d)
        if kind=='approach':x*=np.sin(np.pi*np.minimum(t/d,.8)/1.6)**2
        elif kind=='depart':x*=np.exp(-t*.6)*(1-np.exp(-t*9))
        else:
            x*=.75*np.exp(-t*.55)
            mixat(x,impact('dread_step'),1.5,.65)
    return fade(x,.1,.4)

VOICE_PROFILES={
 'guard':(137,1.0,.2,False),'krieg':(124,.95,.22,True),'marine':(91,.8,.35,True),
 'chaos':(77,.72,.5,True),'khorne':(72,.72,.6,True),'custodes':(101,.86,.28,True),
 'sisters':(218,1.2,.15,False),'ork':(66,.68,.7,False),'aeldari':(178,1.13,.13,True),
 'drukhari':(191,1.16,.25,True),'harl':(204,1.22,.13,True),'tau':(154,1.06,.17,True),
 'votann':(106,.85,.3,True),'mechanicus':(111,.9,.4,True),'gsc':(145,1.02,.32,False),
 'kroot':(173,1.1,.5,False),'nurgle':(59,.64,.65,False),'tzeentch':(275,1.35,.5,False),
 'slaanesh':(241,1.24,.3,False),'nid':(190,1.4,.8,False),'beast':(53,.6,.75,False),
 'necron':(82,.9,.75,True),'necronLord':(65,.8,.75,True)}

def vocal(profile,death=False):
    f,shift,rough,helmet=VOICE_PROFILES[profile]
    d=RNG.uniform(.8,1.35) if death else RNG.uniform(.25,.48)
    if profile in ('beast','nid','nurgle') and death:d*=1.35
    t=tvec(d);u=t/d;f*=RNG.uniform(.87,1.13)
    freq=f*(1.05+.35*np.sin(np.pi*np.minimum(u*1.4,1))-(.5 if death else .22)*u)
    jitter=filt(RNG.normal(size=len(t)),None,40)
    phase=TAU*np.cumsum(freq*(1+.035*np.sin(TAU*7*t)+.04*jitter))/SR
    source=np.zeros(len(t))
    for h in range(1,min(65,int(9000/f))):
        source+=np.sin(h*phase+(.1 if h%2 else 0))/(h**1.15)
    source=source*(.75+.25*np.sin(TAU*(32 if rough>.5 else 19)*t))
    source+=noise(d,150,6000)*(.08+rough*.17)
    forms=[(560*shift,5,1),(1100*shift,7,.65),(2500*shift,9,.25)]
    x=np.zeros(len(t))
    for hz,q,amp in forms:
        b,a=signal.iirpeak(hz,q,fs=SR);x+=signal.lfilter(b,a,source)*amp
    x=np.tanh(x*(3+rough*5))
    if profile in ('nid','kroot','tzeentch'):x+=.15*noise(d,1500,6000)*(np.sin(TAU*54*t)**2)
    if profile in ('necron','necronLord','mechanicus'): x=x*np.sin(TAU*83*t)+noise(d,300,3200)*.15
    if helmet:x=filt(x,220,3100)
    envelope=np.minimum(u/.07,1)*np.maximum(0,1-u)**(.65 if death else 1.3)
    x*=envelope
    return fade(x,.008,.07)

def misc(kind):
    if kind in ('pop','boom','bigboom'):return explosion({'pop':.4,'boom':1.1,'bigboom':2.3}[kind])
    if kind=='rocket':
        d=1.5;t=tvec(d);return fade(noise(d,120,4300)*np.exp(-t*2.7)+thump(d,80)*.4,.01,.12)
    if kind in ('flame','jet'):return fade(engine('flame' if kind=='flame' else 'dropship',1.5),.045,.4)
    if kind=='whistle':
        d=1.5;t=tvec(d);return fade((tone(d,1700,440,0)*.25+noise(d,800,2500)*.4)*np.sin(np.pi*t/d),.05,.08)
    if kind in ('horn','titan_horn'):
        d=3.4;t=tvec(d);x=np.zeros(len(t));base=(49 if kind=='titan_horn' else 73.416)*RNG.uniform(.965,1.035)
        for f in [base,base*1.498,base*2]:
            for h in range(1,12):x+=np.sin(TAU*f*h*t+.01*np.sin(TAU*4*t))/(h**1.5)*.25
        return fade(filt(x,None,2000),.3,.65)
    if kind=='siren':
        d=4;t=tvec(d);fs=RNG.uniform(370,410)+RNG.uniform(115,145)*np.sin(TAU*RNG.uniform(.54,.66)*t);return fade(np.sin(TAU*np.cumsum(fs)/SR)*.6,.1,.2)
    if kind in ('roar','waaagh'):return vocal('beast' if kind=='roar' else 'ork',True)
    if kind=='scream':return vocal('sisters',True)
    if kind in ('thunder','collapse'):return explosion(3.0 if kind=='thunder' else 2.0)
    if kind=='reload':
        x=np.zeros(round(SR*.9))
        for at,g in [(0,.3),(.27,.55),(.53,.4)]:mixat(x,impact('armor_step'),at,g)
        return fade(x,.001,.05)
    if kind=='shield':
        d=1.8;t=tvec(d);return fade(energy('gauss') if False else noise(d,200,9000)*np.exp(-t*3)*(.5+.5*np.sin(TAU*60*t))+tone(d,260,45,4),.002,.1)
    raise ValueError(kind)


def save_sound(key,x,category,variant,loop=False,notes=''):
    x=np.asarray(x,dtype=np.float64);x-=np.mean(x)
    x=filt(x,25,None)
    if loop:x=loop_join(x)
    else:x=fade(x,.0004,.015)
    peak=np.max(np.abs(x));x=x/max(peak,1e-7)*10**(-3/20)
    name=f'{category}/{key}_{variant:02d}.wav'
    dest=OUT/'sfx'/name;dest.parent.mkdir(parents=True,exist_ok=True)
    pcm=np.round(x*32767).astype(np.int16);wavfile.write(dest,SR,pcm)
    BANK.append({'id':key,'category':category,'variant':variant,'path':'sfx/'+name,'sample_rate':SR,'channels':1,'frames':len(x),'duration_seconds':round(len(x)/SR,6),'loop':loop,'loop_start_frame':0 if loop else None,'loop_end_frame_exclusive':len(x) if loop else None,'peak_dbfs':round(20*np.log10(np.max(np.abs(pcm.astype(float)))/32768),3),'notes':notes})

def render_sfx():
    print('Rendering weapon and combat banks',flush=True)
    ballistic=['bolt','hbolt','auto','slug','shoota','cannon','rail']
    energetic=['las','plasma','pulse','gauss','shur','splint','sonic','organic','lasc','melta']
    impacts=['clang','chain','power','hit','thud','armthud','sword_swing','parry','hammer','stab','armor_step','dread_step','titan_step']
    others=['pop','boom','bigboom','rocket','flame','jet','whistle','horn','titan_horn','siren','roar','waaagh','scream','thunder','collapse','reload','shield']
    for key in ballistic+energetic+impacts+others:
        cat='weapons' if key in ballistic+energetic+['rocket','flame','reload'] else 'melee' if key in impacts[:10] else 'events'
        fn=gun if key in ballistic else energy if key in energetic else impact if key in impacts else misc
        for v in range(1,4):save_sound(key,fn(key),cat,v)
    for kind in ['approach','land','depart','ramp','pod']:
        for v in range(1,3):save_sound('dropship_'+kind,aircraft(kind),'vehicles',v)
    for kind in ['tank','dread','titan','dropship','hover','chain','flame','warp']:
        save_sound(kind+'_loop',engine(kind,6.08),'loops',1,True,'Use a persistent loop per nearby emitter; fade in/out over 100–300 ms.')
    for kind in ['tank','dread','titan']:
        for action in ['start','stop']:
            x=engine(kind,2.8)
            t=tvec(2.8)
            x*=np.sin(np.pi*np.minimum(t/2.8,.95)/2)**2 if action=='start' else np.exp(-t*1.4)
            save_sound(kind+'_'+action,fade(x,.04,.2),'vehicles',1)
    print('Rendering non-verbal vocal reactions',flush=True)
    for key in VOICE_PROFILES:
        for death in [False,True]:
            for v in range(1,4):save_sound(key+('_death' if death else '_pain'),vocal(key,death),'reactions',v,notes='Synthetic non-verbal performance; no spoken words or actor recordings.')

# Seven original compositions. All note material is newly specified below.
TRACKS=[
 ('01_iron_oath','Iron Oath',92,38,'D minor',[0,0,8,5,0,10,8,7],[0,7,12,10,7,3,5,2],'march','Imperial advance / Cadia / Macragge'),
 ('02_furnace_legions','Furnace Legions',118,36,'C minor',[0,3,8,7,0,10,5,7],[0,0,7,3,10,7,3,2],'industrial','Mars / forge world / armored engagement'),
 ('03_breach_the_hive','Breach the Hive',136,40,'E minor',[0,10,7,0,8,5,10,7],[12,7,10,7,3,5,2,0],'assault','Close combat / urban breach / mass assault'),
 ('04_beyond_the_pylons','Beyond the Pylons',80,37,'C-sharp Phrygian',[0,1,0,7,8,1,5,7],[0,1,7,8,7,1,5,0],'warp','Chaos / daemons / warp incursion'),
 ('05_god_engine','God Engine',96,34,'B-flat minor',[0,0,5,8,0,10,8,7],[0,12,7,5,3,7,2,0],'titan','Titans / siege / heavy machines'),
 ('06_hunger_in_the_dark','Hunger in the Dark',144,39,'E-flat minor',[0,5,1,0,8,7,5,7],[0,7,1,12,10,1,5,7],'swarm','Tyranids / Orks / overwhelming enemy waves'),
 ('07_last_bastion','Last Bastion',108,41,'F minor',[0,8,3,10,5,8,7,0],[12,15,14,12,7,10,8,7],'finale','Final defense / heroes / decisive battle')]

@lru_cache(maxsize=2048)
def instrument(kind,note,duration):
    d=duration;t=tvec(d);f=440*2**((note-69)/12);x=np.zeros(len(t))
    if kind=='bass':
        x=np.sin(TAU*f*t)+.28*np.sin(TAU*f*2*t)+.1*np.sin(TAU*f*3*t)
        return fade(x,.012,min(.14,d*.4))*.65
    if kind in ('brass','string','pad','choir'):
        maxh=min(28,int(9000/f))
        for h in range(1,maxh):
            if kind=='brass':a=(1/h**1.25)*np.exp(-h*f/4500)
            elif kind=='choir':a=(np.exp(-((h*f-650)/230)**2)+.5*np.exp(-((h*f-1150)/300)**2)+.15*np.exp(-((h*f-2700)/400)**2))/h**.4
            elif kind=='pad':a=1/h**2.1
            else:a=1/h**1.5
            vibrato=.008*np.sin(TAU*4.7*t)*np.minimum(t*2,1)
            x+=a*(np.sin(TAU*f*h*t+h*vibrato)+.25*np.sin(TAU*f*h*1.002*t))
        if kind=='string':x*=np.exp(-t/max(.08,d*.38));return fade(x,.013,min(.09,d*.25))*.4
        attack={'brass':.09,'pad':.55,'choir':.35}[kind]
        return fade(x,min(attack,d*.3),min(.4,d*.3))*.42
    if kind=='bell':
        for h,a in [(1,1),(2.756,.4),(5.404,.2),(8.93,.1)]:x+=a*np.sin(TAU*f*h*t)*np.exp(-t*(.8+h*.2))
        return fade(x,.001,.2)*.3
    raise ValueError(kind)

def drum(kind,variant=0):
    d=.9 if kind=='kick' else .4 if kind=='snare' else .12 if kind=='hat' else 1.8
    t=tvec(d)
    if kind=='kick':x=tone(d,100+variant*5,40,6)*.9+noise(d,None,700)*np.exp(-t*35)*.45
    elif kind=='snare':x=noise(d,700,8500)*np.exp(-t*19)*.9+tone(d,190,160,18)*.3
    elif kind=='hat':x=noise(d,6500,14000)*np.exp(-t*45)*.32
    else:x=ring(d,180+variant*43)*.22+noise(d,400,3000)*np.exp(-t*24)*.4
    return fade(x,.001,.015)

def place(dst,src,at,gain=1,pan=0):
    # Wrap all decays into beginning of loop; no silent gap or truncated tail.
    at=int(round(at*SR))%len(dst)
    gains=np.array([np.sqrt((1-pan)/2),np.sqrt((1+pan)/2)])*gain
    n=min(len(src),len(dst));k=min(n,len(dst)-at)
    dst[at:at+k]+=src[:k,None]*gains
    if k<n:dst[:n-k]+=src[k:n,None]*gains

def render_music():
    tracks=[]; previews=[]
    for ti,(slug,title,bpm,root,key,progression,motif,style,use) in enumerate(TRACKS):
        print('Composing '+title,flush=True)
        beat=60/bpm;bar=4*beat;bars=32;frames=round(bars*bar*SR)
        dst=np.zeros((frames,2),dtype=np.float64)
        kick=drum('kick',ti%3);snare=drum('snare');hat=drum('hat');metal=drum('metal',ti)
        for b in range(bars):
            start=b*bar;section=b//8;r=root+progression[b%8]
            minor=3 if b%8!=6 else 4
            # Dynamic 8-bar sections leave room for gameplay and distinguish the finale.
            intensity=[.72,1,.55,1.05][section]
            if style=='warp':intensity*=.8
            for j,n in enumerate([r+12,r+12+minor,r+19]):
                place(dst,instrument('pad',n,round(bar+.5,4)),start,.24,[-.55,0,.55][j])
                if b%2==0 or style in ('warp','finale'):
                    place(dst,instrument('choir',n+12,round(bar*.95,4)),start+.08,.17*intensity,[-.45,.2,.5][j])
            bassbeats=[0,2] if style in ('march','warp','titan') else [0,1.5,2,3.5]
            for bt in bassbeats:place(dst,instrument('bass',r,round(beat*.75,4)),start+beat*bt,.36*intensity)
            for bt,g in ([(0,.9),(2,.75),(3.5,.45)] if style not in ('warp','titan') else [(0,1),(2.5,.65)]):
                place(dst,kick,start+beat*bt,g*intensity)
            if style!='warp':
                for bt in [1,3]:place(dst,snare,start+beat*bt,.32*intensity,.15)
            if style in ('assault','industrial','swarm','finale'):
                for q in range(8):place(dst,hat,start+q*.5*beat,.6*intensity if q%2 else .35*intensity,(-1)**q*.4)
            ostinato=[0,7,12,7,3,7,10,7] if style!='swarm' else [0,1,7,12,1,7,10,7]
            if section!=2 or b%2==0:
                for q,interval in enumerate(ostinato):
                    place(dst,instrument('string',r+12+interval,round(beat*.41,4)),start+q*.5*beat,.23*intensity,(-1)**q*.55)
            if style in ('industrial','titan','swarm') and b%2==0:place(dst,metal,start+beat*.75,.5*intensity,-.3)
            if b%4==0:place(dst,instrument('bell',root+36+(7 if b%8==4 else 0),4.6),start,.18,.35)
            # Two melodic phrases with answer phrases and a different high final section.
            if section in (1,3) or (style in ('march','finale') and b%2==0):
                for q in range(2):
                    index=(b%4)*2+q;n=root+24+motif[index]
                    if section==3 and b%8>=4:n+=12
                    place(dst,instrument('brass',n,round(beat*(1.65 if q==0 else 1.3),4)),start+q*2*beat,.31*intensity, -.12 if q==0 else .12)
            if b%8==7:
                for q in range(6):place(dst,snare,start+beat*(2.5+q*.25),.12+.045*q,-.3+.12*q)
                place(dst,metal,start+3.5*beat,.24)
        # Circular early reflections and diffuse tail preserve the musical loop boundary.
        wet=filt(dst,180,4800)
        for delay,g in [(.071,.12),(.113,.1),(.193,.07),(.317,.06),(.509,.045),(.773,.035),(1.111,.022)]:
            dst+=np.roll(wet,round(delay*SR),axis=0)[:,::-1]*g
        dst=filt(dst,28,None)
        dst-=np.mean(dst,axis=0)
        rms=np.sqrt(np.mean(dst*dst));dst*=.12/max(rms,1e-9)
        dst=np.tanh(dst*1.2)/1.2
        dst*=min(1,10**(-2/20)/np.max(np.abs(dst)))
        # Very short boundary conditioning; avoids a discontinuity after high-pass filtering.
        k=128; delta=dst[-1]-dst[0]
        dst[:k]+=delta[None,:]*np.linspace(1,0,k)[:,None]*.5
        dst[-k:]-=delta[None,:]*np.linspace(0,1,k)[:,None]*.5
        dest=OUT/'music_wav'/f'{slug}.wav';dest.parent.mkdir(parents=True,exist_ok=True)
        wavfile.write(dest,SR,np.round(dst*32767).astype(np.int16))
        ogg=OUT/'music'/f'{slug}.ogg';ogg.parent.mkdir(parents=True,exist_ok=True)
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(dest),'-c:a','libvorbis','-q:a','5','-metadata','TITLE='+title,'-metadata','ARTIST=Grim Observer Original Audio','-metadata','LOOPSTART=0','-metadata','LOOPEND='+str(frames),str(ogg)],check=True)
        tracks.append({'id':slug,'title':title,'bpm':bpm,'key':key,'bars':bars,'time_signature':'4/4','duration_seconds':round(frames/SR,6),'sample_rate':SR,'channels':2,'frames':frames,'loop':True,'loop_start_frame':0,'loop_end_frame_exclusive':frames,'path':'music/'+slug+'.ogg','wav_master':'music_wav/'+slug+'.wav','suggested_use':use,'style':'Original electronic/cinematic synthesis, no sampled orchestra or recorded choir'})
        # 12-second listening excerpt from active section; add fades only to the preview.
        clip=dst[round(8*bar*SR):round(8*bar*SR)+12*SR].copy()
        for ch in range(2):clip[:,ch]=fade(clip[:,ch],.08,.8)
        previews.append(clip);previews.append(np.zeros((SR//2,2)))
        del dst;instrument.cache_clear()
    preview=np.concatenate(previews)
    save_preview(preview,'Music_Showcase_7_tracks')
    return tracks

def save_preview(audio,name):
    p=OUT/'previews';p.mkdir(parents=True,exist_ok=True)
    tmp=p/(name+'.wav');wavfile.write(tmp,SR,np.round(np.clip(audio,-.95,.95)*32767).astype(np.int16))
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(tmp),'-c:a','libmp3lame','-b:a','192k',str(p/(name+'.mp3'))],check=True)
    tmp.unlink()


def package_and_validate(tracks):
    errors=[];report=[]
    for a in BANK:
        p=OUT/a['path'];sr,x=wavfile.read(p);f=x.astype(float)/32768
        assert sr==SR and x.ndim==1 and len(x)==a['frames']
        assert np.isfinite(f).all() and np.max(np.abs(f))<.9 and np.sqrt(np.mean(f*f))>.001
        if a['loop']:
            boundary=float(abs(f[-1]-f[0]));a['boundary_delta']=round(boundary,6)
            if boundary>.06:errors.append(a['path']+' loop boundary '+str(boundary))
        a['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
    for a in tracks:
        sr,x=wavfile.read(OUT/a['wav_master']);assert len(x)==a['frames'] and x.shape[1]==2
        assert np.max(np.abs(x.astype(float)))<32767
        decoded=subprocess.run(['ffmpeg','-v','error','-i',str(OUT/a['path']),'-f','f32le','-acodec','pcm_f32le','-'],capture_output=True,check=True).stdout
        y=np.frombuffer(decoded,dtype='<f4').reshape(-1,2)
        assert abs(len(y)-a['frames'])<=256
        assert np.isfinite(y).all() and np.max(np.abs(y))<1
        a['ogg_decoded_frames']=len(y)
        a['ogg_boundary_delta']=round(float(np.max(np.abs(y[-1]-y[0]))),6)
        a['wav_boundary_delta']=round(float(np.max(np.abs(x[-1].astype(float)-x[0].astype(float)))/32768),6)
        a['sha256']=hashlib.sha256((OUT/a['path']).read_bytes()).hexdigest()
        report.append({k:a[k] for k in ['id','duration_seconds','ogg_decoded_frames','ogg_boundary_delta','wav_boundary_delta']})
    if errors:raise RuntimeError(errors)
    assert len({a['sha256'] for a in BANK}) == len(BANK), 'Duplicate SFX variant'
    manifest={'version':'1.0','source':'Original offline synthesis; no audio extracted from APK','sound_effects':BANK,'music':tracks}
    (OUT/'audio_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    (OUT/'validation.json').write_text(json.dumps({'checks':'WAV headers, mono/stereo, finite data, no digital clipping, non-silent SFX, loop boundaries, OGG decoded length, SHA256','sfx_files':len(BANK),'music_tracks':len(tracks),'music':report,'limitations':'No real-device listening or integration verification; synthetic vocalizations are not actor performances.'},indent=2))
    demo=[]
    demo_ids=['bolt','hbolt','las','plasma','cannon','rail','clang','parry','chain','power','guard_pain','guard_death','marine_pain','sisters_pain','ork_death','nid_death','necron_death','dropship_approach','dropship_land','dropship_ramp','tank_loop','dread_step','titan_step','titan_horn','bigboom']
    for key in demo_ids:
        a=next(x for x in BANK if x['id']==key);sr,x=wavfile.read(OUT/a['path']);x=x.astype(float)/32768
        x=fade(x[:min(len(x),3*SR)],.002,.08);demo.append(np.stack([x,x],axis=1)*.75);demo.append(np.zeros((int(.35*SR),2)))
    save_preview(np.concatenate(demo),'SFX_Showcase')
    (OUT/'previews'/'SFX_Showcase_order.txt').write_text('\n'.join(demo_ids))
    print('Validated',len(BANK),'SFX and',len(tracks),'music tracks',flush=True)

if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    render_sfx()
    tracks=render_music()
    package_and_validate(tracks)
