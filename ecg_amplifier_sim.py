# -*- coding: utf-8 -*-
"""
Курсова работа по ИТМ: Проектиране на усилвател за измерване на биоелектричен потенциал (ЕКГ)

Програмата симулира целия измервателен тракт:
  1) синтетичен ЕКГ сигнал (модел ECGSYN, McSharry et al., 2003) + реалистични смущения;
  2) аналоговия усилвател: INA128 (G1) -> ВЧ RC филтър -> неинвертиращ усилвател (G2)
     -> НЧ филтър Sallen-Key (Butterworth, 2-ри ред); всички стойности са тези от схемата;
  3) 12-битов АЦП, fs = 500 Hz;
  4) цифрова обработка: режекторен (notch) филтър 50 Hz и алгоритъм на Pan-Tompkins
     за откриване на R-зъбците и изчисляване на сърдечната честота.

Изход: графики (PNG) и числови резултати (results.json).
Зависимости: numpy, scipy, matplotlib, neurokit2
"""
import json
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from scipy import signal
import neurokit2 as nk

import os
# Резултатите се записват в папките до самия файл на програмата
BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "fig")
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"font.size": 9, "font.family": "DejaVu Sans"})

# ------------------------------------------------------------------
# 1. ПАРАМЕТРИ НА СХЕМАТА (стойности на елементите)
# ------------------------------------------------------------------
RG = 5.6e3                  # Ом, резистор за усилване на INA128 (2 x 2,8 kΩ)
G1 = 1 + 50e3 / RG          # формула (3): усилване на INA128
CMRR_dB = 100.0             # dB, минимален CMRR на INA128P/U при G = 10
VSAT = 5.0 - 1.4            # V, изходен обхват при захранване ±5 V

R_HP, C_HP = 330e3, 1e-6    # ВЧ филтър
fc_HP = 1 / (2 * np.pi * R_HP * C_HP)          # формула (5)

RF2, RG2 = 100e3, 1e3       # неинвертиращ усилвател
G2 = 1 + RF2 / RG2          # формула (6)

R1 = R2 = 27e3              # Sallen-Key
C1, C2 = 100e-9, 220e-9     # C1 към маса, C2 - обратна връзка
fc_LP = 1 / (2 * np.pi * np.sqrt(R1 * R2 * C1 * C2))   # формула (7)
Q_LP = np.sqrt(R1 * R2 * C1 * C2) / (C1 * (R1 + R2))    # формула (8)

# RLD (активно управление на десния крак)
RF_RLD, CF_RLD, RIN_RLD = 1e6, 1.5e-9, 100e3


def rld_gain(f):
    zf = RF_RLD / (1 + 1j * 2 * np.pi * f * RF_RLD * CF_RLD)
    return np.abs(zf) / RIN_RLD                          # формула (4)


N_ADC, FS_ADC_V = 12, 5.0   # 12 бита, обхват ±2,5 V
q = FS_ADC_V / 2 ** N_ADC   # формула (10)
fs = 500                    # Hz, честота на дискретизация на АЦП
fs_sim = 5000               # Hz, "аналогово" време за симулация

# ------------------------------------------------------------------
# 2. АНАЛОГОВА ПРЕДАВАТЕЛНА ФУНКЦИЯ H(s) - формула (9)
# ------------------------------------------------------------------
tau = R_HP * C_HP
b_hp, a_hp = [tau, 0], [tau, 1]
b_lp, a_lp = [1], [R1 * R2 * C1 * C2, C1 * (R1 + R2), 1]
b_tot = G1 * G2 * np.polymul(b_hp, b_lp)
a_tot = np.polymul(a_hp, a_lp)

f = np.logspace(-2, 3, 2000)
_, H = signal.freqs(b_tot, a_tot, worN=2 * np.pi * f)
HdB = 20 * np.log10(np.abs(H))
Hmax = HdB.max()
i_mid = np.argmax(HdB)
f_low = f[:i_mid][np.argmin(np.abs(HdB[:i_mid] - (Hmax - 3)))]
f_high = f[i_mid:][np.argmin(np.abs(HdB[i_mid:] - (Hmax - 3)))]
H50 = 20 * np.log10(np.abs(signal.freqs(b_tot, a_tot, worN=[2 * np.pi * 50])[1][0]))

fig, ax = plt.subplots(2, 1, figsize=(6.3, 3.8), sharex=True)
ax[0].semilogx(f, HdB, color="#1f4e79")
ax[0].axhline(Hmax - 3, ls="--", lw=0.8, color="gray")
for fx in (f_low, f_high):
    ax[0].axvline(fx, ls=":", lw=0.8, color="#c00000")
ax[0].set_ylabel("|H(jf)|, dB")
ax[0].set_ylim(0, 70)
ax[0].grid(True, which="both", lw=0.3)
ax[0].text(f_low * 1.15, 8, f"{f_low:.2f} Hz".replace(".", ","), color="#c00000")
ax[0].text(f_high * 1.15, 8, f"{f_high:.1f} Hz".replace(".", ","), color="#c00000")
ax[1].semilogx(f, np.degrees(np.unwrap(np.angle(H))), color="#1f4e79")
ax[1].set_ylabel("Фаза, °")
ax[1].set_xlabel("Честота f, Hz")
ax[1].grid(True, which="both", lw=0.3)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig3_bode.png"), dpi=200)

# ------------------------------------------------------------------
# 3. ВХОДЕН СИГНАЛ НА ЕЛЕКТРОДИТЕ
# ------------------------------------------------------------------
dur, HR_true = 12, 72
ecg_mV = nk.ecg_simulate(duration=dur, sampling_rate=fs_sim, heart_rate=HR_true,
                         method="ecgsyn", random_state=7)
t = np.arange(len(ecg_mV)) / fs_sim
rng = np.random.default_rng(1)
ecg = ecg_mV * 1e-3                                    # V
v_offset = 0.30                                        # V, DC от електродите
v_wander = 0.5e-3 * np.sin(2 * np.pi * 0.25 * t)       # V, дишане
v_mains_d = 0.10e-3 * np.sin(2 * np.pi * 50 * t)       # V, диференциален 50 Hz
v_emg = 20e-6 * rng.standard_normal(len(t))            # V, мускулен шум
Vcm_body = 1.0                                         # V, синфазен 50 Hz върху тялото
vcm = Vcm_body / (1 + rld_gain(50)) * np.sin(2 * np.pi * 50 * t)
v_diff = ecg + v_offset + v_wander + v_mains_d + v_emg

# ------------------------------------------------------------------
# 4. АНАЛОГОВ ТРАКТ (дискретизиран с билинейно преобразуване)
# ------------------------------------------------------------------
v_ina = G1 * v_diff + G1 * vcm / 10 ** (CMRR_dB / 20)  # формула (2)
v_ina = np.clip(v_ina, -VSAT, VSAT)
bz, az = signal.bilinear(b_hp, a_hp, fs_sim)
zi = signal.lfilter_zi(bz, az) * v_ina[0]              # установен режим
v_hp, _ = signal.lfilter(bz, az, v_ina, zi=zi)
v_g2 = np.clip(G2 * v_hp, -VSAT, VSAT)
bz, az = signal.bilinear(b_lp, a_lp, fs_sim)
v_out, _ = signal.lfilter(bz, az, v_g2, zi=signal.lfilter_zi(bz, az) * v_g2[0])

# ------------------------------------------------------------------
# 5. АЦП: дискретизация 500 Hz, квантуване 12 бита
# ------------------------------------------------------------------
dec = fs_sim // fs
x_adc = np.clip(v_out[::dec], -FS_ADC_V / 2, FS_ADC_V / 2 - q)
code = np.round(x_adc / q).astype(int)
x = code * q
tn = np.arange(len(x)) / fs

# ------------------------------------------------------------------
# 6. ЦИФРОВ РЕЖЕКТОРЕН ФИЛТЪР 50 Hz - формула (11)
# ------------------------------------------------------------------
b_n, a_n = signal.iirnotch(50, Q=30, fs=fs)
y = signal.lfilter(b_n, a_n, x)


def amp_at(sig, f0, fsamp):
    w = np.hanning(len(sig))
    S = np.abs(np.fft.rfft(sig * w)) * 2 / w.sum()
    ff = np.fft.rfftfreq(len(sig), 1 / fsamp)
    return S[np.argmin(np.abs(ff - f0))]


skip = 2 * fs
a50_before = amp_at(x[skip:], 50, fs)
a50_after = amp_at(y[skip:], 50, fs)

# ------------------------------------------------------------------
# 7. АЛГОРИТЪМ НА PAN-TOMPKINS - формули (12)-(16)
# ------------------------------------------------------------------
b_bp, a_bp = signal.butter(2, [5, 15], btype="band", fs=fs)
s_bp = signal.lfilter(b_bp, a_bp, y)
T = 1 / fs
s_d = np.zeros_like(s_bp)                            # (12) производна
s_d[4:] = (1 / (8 * T)) * (-s_bp[:-4] - 2 * s_bp[1:-3] + 2 * s_bp[3:-1] + s_bp[4:])
s_sq = s_d ** 2                                      # (13) повдигане на квадрат
N = int(round(0.150 * fs))                           # (14) прозорец 150 ms
s_mwi = np.convolve(s_sq, np.ones(N) / N)[:len(s_sq)]

pk, _ = signal.find_peaks(s_mwi, distance=int(0.2 * fs))  # рефрактерен период 200 ms
learn = s_mwi[:2 * fs]
SPKI, NPKI = 0.25 * learn.max(), 0.5 * learn.mean()
THR = NPKI + 0.25 * (SPKI - NPKI)
qrs_i, thr_hist = [], []
for p in pk:
    PEAKI = s_mwi[p]
    if PEAKI > THR:
        SPKI = 0.125 * PEAKI + 0.875 * SPKI          # (15)
        qrs_i.append(p)
    else:
        NPKI = 0.125 * PEAKI + 0.875 * NPKI
    THR = NPKI + 0.25 * (SPKI - NPKI)                # (16)
    thr_hist.append((p, THR))

# R-зъбецът: максимум на филтрирания ЕКГ в прозорец 250 ms преди пика на MWI
r_peaks = []
for p in qrs_i:
    lo = max(0, p - int(0.25 * fs))
    r_peaks.append(lo + int(np.argmax(y[lo:p + 1])))
r_peaks = np.array(sorted(set(r_peaks)))
r_peaks = r_peaks[r_peaks > skip]                    # след установяване на филтрите

rr = np.diff(r_peaks) / fs
HR_est = 60 / rr.mean()                              # (17)

# Референтни R-зъбци от чистия сигнал (за оценка на точността)
ecg_ref = signal.resample_poly(ecg_mV, 1, dec)
_, info = nk.ecg_peaks(ecg_ref, sampling_rate=fs)
ref = np.array(info["ECG_R_Peaks"])
ref = ref[ref > skip]
tol = int(0.05 * fs)
TP = sum(np.any(np.abs(r_peaks - r) <= tol) for r in ref)
FN = len(ref) - TP
FP = len(r_peaks) - TP
Se = TP / (TP + FN) * 100
PPV = TP / (TP + FP) * 100
delay_ms = np.mean([np.min(np.abs(r_peaks - r)) for r in ref]) / fs * 1000

# ------------------------------------------------------------------
# 8. ГРАФИКИ ВЪВ ВРЕМЕВАТА ОБЛАСТ
# ------------------------------------------------------------------
w0, w1 = 4.0, 8.0
m_sim = (t >= w0) & (t < w1)
m = (tn >= w0) & (tn < w1)
fig, ax = plt.subplots(4, 1, figsize=(6.3, 6.6), sharex=True)
ax[0].plot(t[m_sim], (v_diff[m_sim] - v_offset) * 1e3, lw=0.6, color="#444")
ax[0].set_ylabel("mV")
ax[0].set_title("а) Диференциално напрежение на електродите (без DC отместването 0,3 V)",
                fontsize=8.5, loc="left")
ax[1].plot(tn[m], x[m], lw=0.7, color="#1f4e79")
ax[1].set_ylabel("V")
ax[1].set_title("б) Изход на аналоговия усилвател след 12-битовия АЦП", fontsize=8.5, loc="left")
ax[2].plot(tn[m], y[m], lw=0.7, color="#1f4e79")
rp = r_peaks[(r_peaks / fs >= w0) & (r_peaks / fs < w1)]
ax[2].plot(rp / fs, y[rp], "o", ms=4, mfc="none", color="#c00000", label="открит R-зъбец")
ax[2].legend(loc="upper center", bbox_to_anchor=(0.36, 1.0), fontsize=7.5)
ax[2].set_ylim(-0.9, 1.9)
ax[2].set_ylabel("V")
ax[2].set_title("в) След цифровия режекторен филтър 50 Hz", fontsize=8.5, loc="left")
mw = s_mwi / s_mwi[skip:].max()
ax[3].plot(tn[m], mw[m], lw=0.7, color="#2e7d32", label="MWI")
th = np.interp(tn, [p / fs for p, _ in thr_hist], [v for _, v in thr_hist]) / s_mwi[skip:].max()
ax[3].plot(tn[m], th[m], "--", lw=0.8, color="#c00000", label="праг THRESHOLD I1")
ax[3].legend(loc="upper center", ncol=2, fontsize=7.5)
ax[3].set_ylim(-0.05, 1.45)
ax[3].set_ylabel("отн. ед.")
ax[3].set_xlabel("Време t, s")
ax[3].set_title("г) Pan-Tompkins: сигнал след интегриране с плъзгащ прозорец", fontsize=8.5, loc="left")
for a in ax:
    a.grid(True, lw=0.3)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig4_signals.png"), dpi=200)

res = {
    "G1": G1, "G2": G2, "G_total": G1 * G2, "G_total_dB": 20 * np.log10(G1 * G2),
    "fc_HP": fc_HP, "tau_HP": tau, "fc_LP": fc_LP, "Q_LP": Q_LP,
    "f_low_-3dB": f_low, "f_high_-3dB": f_high, "Hmax_dB": Hmax, "H50_dB": H50,
    "H50_rel_dB": H50 - Hmax,
    "RLD_A_50Hz": rld_gain(50), "RLD_dB_50Hz": 20 * np.log10(1 + rld_gain(50)),
    "RLD_fc": 1 / (2 * np.pi * RF_RLD * CF_RLD),
    "ina_out_offset_V": G1 * v_offset, "Vsat": VSAT,
    "q_mV": q * 1e3, "SNR_ideal_dB": 6.02 * N_ADC + 1.76,
    "a50_before_mV": a50_before * 1e3, "a50_after_mV": a50_after * 1e3,
    "notch_atten_dB": 20 * np.log10(a50_before / a50_after),
    "R_amp_out_V": float(np.percentile(y[skip:], 99.9)),
    "HR_true": HR_true, "HR_est": HR_est, "beats_ref": int(len(ref)),
    "TP": int(TP), "FP": int(FP), "FN": int(FN), "Se": Se, "PPV": PPV,
    "mean_abs_err_ms": delay_ms,
}
with open(os.path.join(BASE, "results.json"), "w", encoding="utf-8") as fh:
    json.dump(res, fh, indent=2, ensure_ascii=False)
for k, v in res.items():
    print(f"{k:20s} {v:.4g}" if isinstance(v, float) else f"{k:20s} {v}")

print("\nГрафиките са записани в:", OUT)
print("Числовите резултати са записани в:", os.path.join(BASE, "results.json"))
print("Затворете прозорците с графиките, за да приключи програмата.")
plt.show()
