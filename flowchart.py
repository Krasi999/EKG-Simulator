# -*- coding: utf-8 -*-
"""Блокова схема на алгоритъма за цифрова обработка (schemdraw.flow)."""
import schemdraw
from schemdraw import flow
import schemdraw.elements as elm

schemdraw.config(fontsize=9, lw=1.0)
d = schemdraw.Drawing(show=False)
W = 5.6
d += (s := flow.Start(w=3, h=0.9).label('Начало'))
d += flow.Arrow().down(0.5)
d += flow.Box(w=W, h=1.1).label('Инициализация: fs = 500 Hz,\nN = 75, обучение 2 s → SPKI, NPKI')
d += flow.Arrow().down(0.5)
d += (rd := flow.Data(w=W, h=0.9).label('Отчет x[n] от 12-битовия АЦП'))
d += flow.Arrow().down(0.5)
d += flow.Box(w=W, h=0.9).label('Режекторен филтър 50 Hz, ф-ла (11)')
d += flow.Arrow().down(0.5)
d += flow.Box(w=W, h=0.9).label('Лентов филтър 5–15 Hz')
d += flow.Arrow().down(0.5)
d += (b_last := flow.Box(w=W, h=1.3).label('Производна (12) → квадрат (13)\n→ интегриране с плъзгащ\nпрозорец 150 ms (14)'))

# втора колона
d += flow.Arrow().right(1.2).at(b_last.E)
d += (dec1 := flow.Decision(w=3.6, h=1.8, S='да', N='не').label('Локален\nмаксимум\n(≥ 200 ms)?'))
d += flow.Arrow().down(0.6).at(dec1.S)
d += (dec2 := flow.Decision(w=3.6, h=1.8, E='не', S='да').label('PEAKI >\nTHRESHOLD I1?'))
d += flow.Arrow().down(0.6).at(dec2.S)
d += (bs := flow.Box(w=3.8, h=1.4).label('R-зъбец: SPKI по (15)\nRR интервал,\nЧСС по (17)'))
d += flow.Arrow().right(0.9).at(dec2.E)
d += (bn := flow.Box(w=2.8, h=1.0).label('Шумов пик:\nобнови NPKI'))
d += flow.Arrow().down(0.6).at(bs.S)
d += (bt := flow.Box(w=3.8, h=0.9).label('Обнови праг (16)'))
d += flow.Line().at(bn.S).toy(bt.E)
d += flow.Arrow().tox(bt.E)

# обратна връзка към четене на следващ отчет
xr = rd.W[0] - 0.8
d += flow.Line().at(bt.S).down(0.5)
d += flow.Line().tox(xr)
d += flow.Line().toy(rd.W)
d += flow.Arrow().tox(rd.W)
d += flow.Line().at(dec1.N).up(0.5)
d += flow.Line().tox(dec1.N[0] - 2.6)
d += flow.Line().toy(rd.E)
d += flow.Arrow().tox(rd.E)

import os
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fig')
os.makedirs(OUT, exist_ok=True)
d.save(os.path.join(OUT, 'fig2_flowchart.png'), dpi=220)
print('ok')
