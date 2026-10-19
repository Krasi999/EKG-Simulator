# -*- coding: utf-8 -*-
"""Принципна схема на ЕКГ усилвателя (schemdraw)."""
import schemdraw
import schemdraw.elements as elm

schemdraw.config(fontsize=15, lw=1.6)
d = schemdraw.Drawing(show=False)

# ---------------- U1: INA128 ----------------
ina = d.add(elm.Ic(pins=[
    elm.IcPin(name='−IN', pin='2', side='left', slot='6/6'),
    elm.IcPin(name='RG', pin='1', side='left', slot='5/6'),
    elm.IcPin(name='RG', pin='8', side='left', slot='2/6'),
    elm.IcPin(name='+IN', pin='3', side='left', slot='1/6'),
    elm.IcPin(name='VO', pin='6', side='right', slot='1/1'),
    elm.IcPin(name='REF', pin='5', side='bottom', slot='1/1'),
], size=(5, 9), pinspacing=1.5, edgepadW=0.5, label='U1\nINA128\nG = 9,93', lblsize=15))

xL = ina.pin2[0]
# RG = 2 x 2,8 kΩ (средна точка = синфазно напрежение)
xr = xL - 1.0
d += elm.Line().at(ina.pin1).tox(xr)
r_a = d.add(elm.Resistor().down().toy((ina.pin1[1] + ina.pin8[1]) / 2).label('2,8 kΩ', 'bottom', fontsize=14))
mid = r_a.end
d += elm.Dot()
d += elm.Resistor().down().toy(ina.pin8[1]).label('2,8 kΩ', 'bottom', fontsize=14)
d += elm.Line().to(ina.pin8)

# Електроди
xe = xL - 9
d += elm.Line().at(ina.pin2).tox(xe)
d += elm.Dot(open=True).label('RA', 'left')
d += elm.Line().at(ina.pin3).tox(xe)
d += elm.Dot(open=True).label('LA', 'left')

# REF към маса
d += elm.Line().at(ina.REF).down(0.5)
d += elm.Ground()

# ---------------- RLD (U2A буфер + U2B инвертиращ интегратор) ----------------
xm = xL - 2.5
d += elm.Line().at(mid).tox(xm)
d += elm.Line().down().toy(ina.pin3[1] - 3.5)
pA = d.here
# U2A: повторител, насочен наляво
u2a = d.add(elm.Opamp(leads=True).left().anchor('in2').at(pA))
d.add(elm.Label().at((u2a.center[0], u2a.center[1] + 1.3)).label('U2A'))
d += elm.Line().at(u2a.in1).down(0.7)
d += elm.Line().tox(u2a.out[0] - 0.4)
d += elm.Line().toy(u2a.out)
d += elm.Line().at(u2a.out).tox(u2a.out[0] - 0.4)
d += elm.Dot()
rin = d.add(elm.Resistor().left(2.2).label('Rвх 100 kΩ', 'bottom', fontsize=14))
n_inv = rin.end
d += elm.Dot()
u2b = d.add(elm.Opamp(leads=True).left().anchor('in1').at(n_inv))
d.add(elm.Label().at((u2b.center[0], u2b.center[1] + 1.3)).label('U2B'))
d += elm.Line().at(u2b.in2).right(0.6)
d += elm.Ground()
# RF || CF от инвертиращия вход към изхода (под схемата)
yb = u2b.out[1] - 2.2
d += elm.Line().at(n_inv).toy(yb)
d += elm.Dot()
d += elm.Resistor().left().tox(u2b.out[0] - 0.5).label('RF 1 MΩ', 'bottom', fontsize=14)
d += elm.Dot()
d += elm.Line().toy(u2b.out)
d += elm.Line().at((n_inv[0], yb)).down(1.4)
d += elm.Capacitor().left().tox(u2b.out[0] - 0.5).label('CF 1,5 nF', 'bottom', fontsize=14)
d += elm.Line().toy(yb)
d += elm.Line().at(u2b.out).tox(u2b.out[0] - 0.5)
d += elm.Dot()
d += elm.Resistor().left().tox(xe).label('RP 390 kΩ', 'top', fontsize=14)
d += elm.Dot(open=True).label('RL', 'left')

# ---------------- ВЧ филтър 0,48 Hz + U2C (G2 = 101) ----------------
d += elm.Line().at(ina.VO).right(0.5)
chp = d.add(elm.Capacitor().right(2.0).label('C 1 µF', 'top', fontsize=14))
n_hp = chp.end
d += elm.Dot()
d += elm.Resistor().at(n_hp).down(2.5).label('R 330 kΩ', 'top', fontsize=14)
d += elm.Ground()
d += elm.Line().at(n_hp).right(0.8)
u2c = d.add(elm.Opamp(leads=True).right().anchor('in2').flip())
d.add(elm.Label().at((u2c.center[0], u2c.center[1] + 1.3)).label('U2C'))
d += elm.Line().at(u2c.in1).down(1.0)
nfb = d.here
d += elm.Dot()
d += elm.Resistor().right().tox(u2c.out[0] + 0.5).label('Rf 100 kΩ', 'bottom', fontsize=14)
d += elm.Line().toy(u2c.out)
d += elm.Line().at(u2c.out).tox(u2c.out[0] + 0.5)
d += elm.Dot()
d += elm.Resistor().at(nfb).down(2.0).label('Rg 1 kΩ', 'bottom', fontsize=14)
d += elm.Ground()

# ---------------- Sallen-Key НЧ филтър 40 Hz (U2D) ----------------
pout2 = (u2c.out[0] + 0.5, u2c.out[1])
r1 = d.add(elm.Resistor().at(pout2).right(2.5).label('R1 27 kΩ', 'bottom', fontsize=14))
nsk = r1.end
d += elm.Dot()
r2 = d.add(elm.Resistor().right(2.5).label('R2 27 kΩ', 'bottom', fontsize=14))
npl = r2.end
d += elm.Dot()
d += elm.Capacitor().at(npl).down(2.0).label('C1 100 nF', 'bottom', fontsize=14)
d += elm.Ground()
d += elm.Line().at(npl).right(2.4)
u2d = d.add(elm.Opamp(leads=True).right().anchor('in2').flip())
d.add(elm.Label().at((u2d.center[0], u2d.center[1] + 1.3)).label('U2D'))
xo = u2d.out[0] + 0.6
d += elm.Line().at(u2d.in1).down(0.7)
d += elm.Line().tox(xo)
d += elm.Line().toy(u2d.out)
d += elm.Line().at(u2d.out).tox(xo)
d += elm.Dot()
d += elm.Line().at(nsk).up(2.6)
d += elm.Capacitor().right().tox(xo).label('C2 220 nF', 'top', fontsize=14)
d += elm.Line().toy(u2d.out)
d += elm.Line().at((xo, u2d.out[1])).right(1.0)
d += elm.Dot(open=True).label('Uизх → АЦП', 'right')

d.add(elm.Label().at((xe + 1, ina.pin2[1] + 2.2)).label(
    'Захранване ±5 V; U2A…U2D = OPA4277; REF – аналогова маса', halign='left', fontsize=14))

import os
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fig')
os.makedirs(OUT, exist_ok=True)
d.save(os.path.join(OUT, 'fig1_schematic.png'), dpi=220)
print('ok')
