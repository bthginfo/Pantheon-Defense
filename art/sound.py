"""Synthesize and mix original music and gameplay sound cues."""
from math import exp, pi, sin, tau
from pathlib import Path
from random import Random
from struct import pack
from subprocess import run
from sys import argv
from tempfile import TemporaryDirectory
import wave

RATE = 24000
OUT = Path(__file__).resolve().parent.parent / "public" / "assets" / "audio"
OUT.mkdir(parents=True, exist_ok=True)
SELECTED = set(argv[1:])

def mix(left, right, start, duration, voice, gain, pan=0):
    onset = int(start * RATE)
    for k in range(int(duration * RATE)):
        sample = voice(k / RATE) * gain
        index = (onset+k) % len(left)
        left[index] += sample * (.77 - .23*pan)
        right[index] += sample * (.77 + .23*pan)

def pluck(note, decay=4.2, metal=0.12):
    f = 440 * 2 ** ((note-69)/12)
    def voice(t):
        attack = min(1,t/.012)
        fundamental = sin(tau*f*t)
        harmonics = .33*sin(tau*f*2*t)*exp(-2.9*t)+.14*sin(tau*f*3*t)*exp(-5.5*t)
        buzz = metal*sin(tau*f*4.06*t)*exp(-9*t)
        return attack*exp(-decay*t)*(fundamental+harmonics+buzz)
    return voice

def drone(note, duration):
    f=440*2**((note-69)/12)
    def voice(t):
        phase = t/duration
        envelope = sin(pi*min(1,max(0,phase)))**1.5
        return envelope*(sin(tau*f*t+.12*sin(2*t))+ .45*sin(tau*f*1.995*t)+.22*sin(tau*f*3*t))
    return voice

def drum(frequency, decay=9):
    rng=Random(7741)
    def voice(t):
        return exp(-decay*t)*(sin(tau*(frequency*t+2.4*(1-exp(-t*18))))*.83+rng.uniform(-.12,.12))
    return voice

def chime(notes, decay, spread, duration):
    voices=[pluck(n,decay,.19) for n in notes]
    def voice(t):
        return sum(f(t-i*spread) for i,f in enumerate(voices) if t>=i*spread)/len(voices)
    return voice

def save(name, left, right):
    peak=max(.78, max(abs(x) for x in left),max(abs(x) for x in right))
    with TemporaryDirectory(prefix="pantheon-sound-") as directory:
        src=Path(directory)/"source.wav"
        with wave.open(str(src),"wb") as f:
            f.setparams((2,2,RATE,0,"NONE","not compressed"))
            packet=bytearray()
            for a,b in zip(left,right):
                packet += pack("<hh",int(26000*a/peak),int(26000*b/peak))
            f.writeframes(packet)
        run(["ffmpeg","-nostdin","-v","error","-y","-i",str(src),"-c:a","libvorbis","-q:a","5",
            str(OUT / f"{name}.ogg")],check=True)

def score(name, scale, roots, pattern, pulse):
    if SELECTED and name not in SELECTED:
        return
    duration=28.8
    left=[0.] * round(duration*RATE)
    right=left.copy()
    for measure,root in enumerate(roots):
        at=measure*3.6
        mix(left,right,at-0.35,4.3,drone(root-12,4.3),.16,-.18)
        mix(left,right,at+0.09,4.1,drone(root+7,4.1),.058,.58)
        for step,n in enumerate(pattern[measure%len(pattern)]):
            if n is None:
                continue
            t=at+step*.45+.013*sin(step+measure)
            note=scale[n%len(scale)]+(12 if n>=len(scale) else 0)
            mix(left,right,t,1.45,pluck(note,4.1,.18),.17-.025*(step%3),-.48 if step%2==0 else .42)
            mix(left,right,t+.145,.85,pluck(note,5.9,.1),.029,.71 if step%2==0 else -.65)
        for step in pulse:
            mix(left,right,at+step*.45,.46,drum(42+step*5),.105 if step==0 else .057,.11)
    save(name,left,right)

score("aegean",[57,60,62,64,67,69],[45,45,48,43]*2,
      [(0,None,2,3,4,None,3,2),(0,None,4,None,3,2,1,None),
       (2,3,None,5,None,4,2,0),(1,None,2,None,0,None,2,None)],(0,3,5))
score("rome",[53,56,58,60,61,65],[41,41,44,37]*2,
      [(0,2,3,None,2,0,None,1),(0,None,1,2,None,1,0,None),
       (3,4,5,None,3,None,2,1),(2,1,0,None,2,1,0,None)],(0,2,4,6))
score("japan",[57,58,62,64,65,69],[45,46,50,45]*2,
      [(0,None,None,2,None,3,2,None),(1,None,2,None,4,None,3,2),
       (3,None,4,None,5,4,None,3),(2,None,1,None,0,None,None,0)],(0,5))

def cue(name, duration, parts):
    if SELECTED and name not in SELECTED:
        return
    left=[0.] * round(duration*RATE)
    right=left.copy()
    for start, function, gain, pan in parts:
        mix(left,right,start,duration-start,function,gain,pan)
    save(name,left,right)

cue("place",.39,[(0,pluck(62,14),.55,-.10),(0,drum(85,25),.15,.17)])
cue("impact",.25,[(0,drum(155,35),.56,.12),(.01,pluck(44,24,.5),.22,-.22)])
cue("magic",.55,[(0,pluck(78,12,.35),.29,.14),(.022,pluck(84,8),.31,-.31)])
cue("merge",.84,[(0,chime([55,62,67,74],8,.067,.84),.68,0),(.197,drum(76,13),.22,.16)])
cue("cast",1.35,[(0,chime([49,56,61,66,73,78],4,.068,1.35),.81,0),(.35,drum(61,5),.38,0)])
cue("boss",1.35,[(0,drum(28,3.6),.63,0),(.25,drone(40,1.1),.21,-.2),(.42,drum(27,4.2),.39,.22)])
cue("wave",.84,[(0,drum(68,7.4),.36,0),(.12,pluck(59,6),.32,-.24),(.29,pluck(66,6),.32,.22)])
cue("victory",1.8,[(0,chime([53,60,65,69,72,77],3.0,.108,1.8),.86,0),(.26,drone(48,1.53),.23,0)])
cue("reserve",.53,[(0,pluck(58,12,.24),.45,-.19),(.072,pluck(70,7),.41,.18)])
cue("stack",.46,[(0,drum(104,14),.26,-.2),(.068,pluck(62,9),.34,.16),(.13,pluck(69,8),.29,.02)])
cue("oracle",1.02,[(0,drone(56,.92),.27,-.13),(.12,chime([64,66,73,76],6,.093,.9),.56,.12)])
cue("ritual",1.42,[(0,drum(48,8),.47,0),(.14,drone(48,1.23),.28,.24),(.24,chime([48,55,60,64,72],4,.094,1.16),.66,-.1)])
