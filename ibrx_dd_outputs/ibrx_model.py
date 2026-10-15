#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ImmunityBio (NASDAQ: IBRX) -- Modele de due diligence
=====================================================
Genere TOUTES les figures du rapport (dossier ./figures) ainsi que
./figures/values.tex : macros LaTeX contenant les sorties chiffrees du modele
(rNPV par segment, valeur par action, scenarios, runway...) afin que le texte
du rapport reste strictement coherent avec le modele.

Donnees de marche au 14/10/2026. Sources principales : 10-Q T2 2026, 8-K
(communiques T1/T2 2026, resultats FY2025), communiques FDA/EMA/SFDA,
publications QUILT-3.032 / QUILT-2.005 (voir bibliographie du rapport).

Usage : python3 ibrx_model.py   (aucun argument ; ~20 s)
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle
from datetime import date, timedelta
from scipy import stats

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures")
os.makedirs(OUT, exist_ok=True)
RNG = np.random.default_rng(20261014)

# ---------------------------------------------------------------- style
NAVY = '#1B2A4A'; DKBLUE = '#2C5F8A'; ACCENT = '#E8833A'; GREEN = '#2E7D32'
RED = '#C62828'; PURPLE = '#6A1B9A'; TEAL = '#00796B'; GOLD = '#F9A825'
GRAY = '#7A7A7A'; LIGHT = '#E9EEF5'
plt.rcParams.update({'font.family': 'serif', 'font.size': 10,
                     'figure.dpi': 200, 'savefig.dpi': 200, 'savefig.bbox': 'tight',
                     'axes.grid': True, 'grid.alpha': 0.25,
                     'axes.spines.top': False, 'axes.spines.right': False,
                     'axes.titleweight': 'bold', 'axes.titlesize': 11,
                     'text.parse_math': False})

def save(fig, name):
    fig.savefig(os.path.join(OUT, name + ".pdf"))
    fig.savefig(os.path.join(OUT, name + ".png"))
    plt.close(fig)
    print("  ->", name)

# ================================================================ INPUTS
PRICE = 10.32                 # $ 14/10/2026 (seance de l'approbation papillaire)
PRICE_PREV = 9.80             # cloture 13/10/2026
HI52, LO52 = 12.43, 1.95
SH_BASIC = 1059.84            # M actions au 31/07/2026 (couverture 10-Q T2)
SH_CONV = 88.4                # M actions sous-jacentes a la note Nant ($480M @ $5.427)
SH_OTHER = 115.0              # M warrants + options/RSU dans la monnaie (estimation)
SH_FD = SH_BASIC + SH_CONV + SH_OTHER
CASH_Q2 = 357.4               # $M au 30/06/2026
NOTE_NANT = 480.0             # $M principal note convertible (Nant Capital)
RIPA_LIAB = 404.3             # $M passif "revenue interest" (Oberland), 31/03/2026
CFO_Q1, CFO_Q2 = 75.4, 66.5   # $M cash consomme par l'exploitation
MCAP = PRICE * SH_BASIC / 1000  # $B
MCAP_FD = PRICE * SH_FD / 1000

# Revenus produit net trimestriels ($M) -- historiques puis estimations (E)
Q_LBL = ["T2-24", "T3-24", "T4-24", "T1-25", "T2-25", "T3-25", "T4-25",
         "T1-26", "T2-26", "T3-26E", "T4-26E"]
Q_REV = [1.4, 6.1, 7.2, 16.5, 26.4, 31.8, 38.3, 44.1, 50.7, 56.5, 63.5]
N_ACTUAL = 9

# ================================================================ rNPV
YEARS = np.arange(2026, 2041)
T0 = 2026.8                    # date de valorisation (mi-octobre 2026)
WACC = 0.10
GM = 0.90                      # marge brute biologique a maturite
ROYALTY = 0.075                # RIPA Oberland (paliers 5.625%-12.5%, moyenne ponderee)
OPEX_PCT = 0.33                # SG&A+R&D attribuables, % ventes a maturite
TAX = 0.21
NOL0 = 3000.0                  # $M deficits reportables (ordre de grandeur, 10-K)
LOE = 2036                     # exclusivite biologique 12 ans (avril 2024) ~ 2036
EROSION = 0.12                 # baisse annuelle des ventes post-LOE (biosimilaires lents, niche intravesicale)
TV_DECLINE = 0.10              # valeur terminale 2040 : flux en declin perpetuel de 10%/an

def ramp(launch, peak_year, peak):
    """Courbe logistique d'adoption : S(t) = peak / (1+exp(-k (t - t_mid)))."""
    t_mid = (launch + peak_year) / 2.0
    k = 8.0 / max(peak_year - launch, 1)
    s = peak / (1 + np.exp(-k * (YEARS - t_mid)))
    s[YEARS < launch] = 0.0
    post = YEARS > LOE
    s[post] = s[YEARS == LOE][0] * (1 - EROSION) ** (YEARS[post] - LOE)
    return s

# segment : (lancement, annee pic, ventes pic $M, P(succes), marge contributive)
SEG_BASE = {
    "NMIBC BCG-UR CIS (US)":          (2024, 2030, 650, 1.00, None),
    "NMIBC BCG-UR papillaire (US)":   (2026.8, 2031, 380, 1.00, None),
    "NMIBC BCG-naif (QUILT-2.005)":   (2027.9, 2034, 1600, 0.60, None),
    "Ex-US NMIBC (UE/UK/KSA)":        (2026, 2032, 350, 0.85, 0.30),
    "CPNPC 2L+ (ResQ201A, US/UE)":    (2029, 2035, 1100, 0.20, None),
    "Lymphopenie / pipeline":         (2029, 2035, 700, 0.10, None),
}
CORP_OVERHEAD = 70.0           # $M/an non alloue (plateforme, CAR-NK, vaccins) 2027-2031

def segment_sales(seg):
    return {k: ramp(*v[:3]) for k, v in seg.items()}

def run_dcf(seg, wacc=WACC, opex=OPEX_PCT, royalty=ROYALTY, gm=GM, nol=NOL0):
    """Retourne (dict NPV par segment ponderes P, NPV overhead, ventes totales P-ponderees)."""
    sales = segment_sales(seg)
    disc = 1 / (1 + wacc) ** (YEARS + 0.5 - T0)
    disc[YEARS < 2027] = 0.0      # 2026 deja quasi ecoule
    # profit operationnel pondere par segment
    contrib = {}
    for k, (l, py, pk, p, m) in seg.items():
        margin = (m if m is not None else gm - royalty - opex)
        contrib[k] = p * sales[k] * margin
    pretax = sum(contrib.values()) - np.where((YEARS >= 2027) & (YEARS <= 2031), CORP_OVERHEAD, 0)
    # impots avec utilisation des NOL
    tax = np.zeros_like(pretax); rem = nol
    for i, x in enumerate(pretax):
        if x > 0:
            use = min(rem, x); rem -= use; tax[i] = TAX * (x - use)
    eff = np.where(pretax > 0, 1 - tax / np.where(pretax == 0, 1, pretax), 1)
    tv_f = (1 - TV_DECLINE) / (wacc + TV_DECLINE)   # Gordon avec croissance negative
    npv = {k: float(np.sum(c * eff * disc) + c[-1] * (1 - TAX) * tv_f * disc[-1]) for k, c in contrib.items()}
    npv_ovh = -float(np.sum(np.where((YEARS >= 2027) & (YEARS <= 2031), CORP_OVERHEAD, 0) * disc))
    tot_sales = sum(seg[k][3] * sales[k] for k in seg)
    return npv, npv_ovh, tot_sales, sales

CASH_EST = CASH_Q2 - 62.0      # tresorerie estimee au 30/09/2026 (burn T3 ~ $62M)
def equity_per_share(seg, **kw):
    npv, ovh, _, _ = run_dcf(seg, **kw)
    ev = sum(npv.values()) + ovh
    # note Nant traitee comme convertie (dans la monnaie) -> actions dans SH_FD ;
    # la redevance Oberland est deja deduite des marges (pas de double comptage).
    eq = ev + CASH_EST
    return eq / SH_FD, ev, npv, ovh

VPS_BASE, EV_BASE, NPV_BASE, OVH_BASE = equity_per_share(SEG_BASE)

def scen(mult_peak=1.0, p_naive=None, p_lung=None, p_pipe=None, wacc=WACC, opex=OPEX_PCT, delay=0.0, mult_cis=1.0):
    s = {}
    for k, (l, py, pk, p, m) in SEG_BASE.items():
        pk2 = pk * mult_peak
        if "CIS" in k or "papillaire" in k:
            pk2 = pk * mult_cis
        p2 = p
        if "naif" in k and p_naive is not None: p2 = p_naive
        if "CPNPC" in k and p_lung is not None: p2 = p_lung
        if "pipeline" in k and p_pipe is not None: p2 = p_pipe
        l2 = l + (delay if "naif" in k else 0); py2 = py + (delay if "naif" in k else 0)
        s[k] = (l2, py2, pk2, p2, m)
    return equity_per_share(s, wacc=wacc, opex=opex)[0]

SCEN = [  # nom, prob, valeur, description
    ("Catastrophe", 0.12, scen(mult_peak=0.55, mult_cis=0.6, p_naive=0.0, p_lung=0.0, p_pipe=0.0, opex=0.40, wacc=0.12),
     "QUILT-2.005 negatif, erosion par Inlexzo/creto, dilution"),
    ("Bear", 0.23, scen(mult_peak=0.8, mult_cis=0.85, p_naive=0.35, p_lung=0.10, delay=1.0, opex=0.36),
     "BCG-naif retarde/etroit, croissance ralentie"),
    ("Base", 0.33, VPS_BASE, "Modele central (rNPV)"),
    ("Bull", 0.18, scen(mult_peak=1.35, mult_cis=1.2, p_naive=0.85, p_lung=0.30, wacc=0.095, opex=0.30),
     "BCG-naif approuve 2027, rBCG resout l'offre"),
    ("Blue sky", 0.06, scen(mult_peak=1.9, mult_cis=1.4, p_naive=1.0, p_lung=0.6, p_pipe=0.35, wacc=0.09, opex=0.28),
     "Plateforme IL-15 validee (CPNPC US, lymphopenie)"),
]
# Scenario M&A : rachat (bull-ish) avec prime de 35% sur valeur intrinseque bull
VAL_MA = PRICE * 1.30          # prime de controle ~30% sur le cours (mediane deals 26-52%)
SCEN.append(("M\\&A", 0.08, VAL_MA, "Rachat a +30% (accord Soon-Shiong requis)"))
PSUM = sum(s[1] for s in SCEN)
assert abs(PSUM - 1.0) < 1e-9, PSUM
EV_WEIGHTED = sum(s[1] * s[2] for s in SCEN)
UPSIDE = EV_WEIGHTED / PRICE - 1

# --- implied: peak sales required to justify price (base economics)
def implied_mult():
    lo, hi = 0.5, 6.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if scen(mult_peak=mid, mult_cis=mid) < PRICE: lo = mid
        else: hi = mid
    return mid
IMPL_MULT = implied_mult()
BASE_PEAK_TOTAL_RISK = sum(v[2] * v[3] for v in SEG_BASE.values())

print(f"VPS base = {VPS_BASE:.2f}  EV ops = {EV_BASE:.0f}  weighted = {EV_WEIGHTED:.2f}  upside={UPSIDE:+.1%}")
for s in SCEN: print(f"   {s[0]:12s} p={s[1]:.2f}  ${s[2]:.2f}")
print(f"Multiplicateur de pic implicite pour justifier ${PRICE}: x{IMPL_MULT:.2f}")

# ================================================================ FIG 1 : MOA
def fig_moa():
    fig, ax = plt.subplots(figsize=(11, 6.2)); ax.set_xlim(0, 11); ax.set_ylim(0, 6.4); ax.axis('off')
    ax.grid(False)
    def box(x, y, w, h, txt, fc, tc='white', fs=8.3, bold=True):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04,rounding_size=0.12",
                                    fc=fc, ec=NAVY, lw=1.2))
        ax.text(x + w / 2, y + h / 2, txt, ha='center', va='center', color=tc, fontsize=fs,
                fontweight='bold' if bold else 'normal')
    def arr(x1, y1, x2, y2, c=NAVY, ls='-'):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle='-|>', mutation_scale=14,
                                     color=c, lw=1.6, linestyle=ls))
    ax.text(5.5, 6.15, "ANKTIVA (N-803, nogapendekin alfa inbakicept) : superagoniste IL-15 + BCG intravesical",
            ha='center', fontsize=11.5, fontweight='bold', color=NAVY)
    box(0.2, 4.0, 2.9, 1.4, "ANKTIVA\nIL-15N72D : IL-15Rα-Su/Fc\n(complexe pre-associe)", NAVY)
    box(0.2, 2.0, 2.9, 1.4, "BCG / rBCG\n(TICE Merck ou rBCG\nSerum Institute)", DKBLUE)
    box(4.2, 3.0, 2.8, 1.5, "Vessie : instillation\nintravesicale hebdomadaire\n(induction + entretien)", TEAL)
    box(8.0, 4.5, 2.8, 1.0, "Cellules NK\nproliferation + cytotoxicite", GREEN)
    box(8.0, 3.1, 2.8, 1.0, "Lymphocytes T CD8+\nmemoire (Tscm)", GREEN)
    box(8.0, 1.7, 2.8, 1.0, "Immunite innee BCG\n(macrophages, Th1)", PURPLE)
    box(0.2, 0.15, 10.6, 0.8, "Effet clinique : RC 62-71% (CIS), DFS 12 mois 58% (papillaire seul),\n"
        "preservation vesicale > 80% a 36 mois, profil de SAE comparable au BCG seul", ACCENT, fs=8.8)
    arr(3.1, 4.7, 4.2, 4.1); ax.text(3.65, 4.75, "trans-presentation\nIL-2/15Rβγ", fontsize=7.3, ha='center', color=NAVY, style='italic')
    arr(3.1, 2.7, 4.2, 3.4); ax.text(3.65, 2.55, "adjuvant\ninne", fontsize=7.3, ha='center', color=NAVY, style='italic')
    arr(7.0, 4.2, 8.0, 5.0); arr(7.0, 3.75, 8.0, 3.6); arr(7.0, 3.3, 8.0, 2.2)
    arr(9.4, 1.7, 9.4, 0.95, c=GRAY, ls='--')
    ax.text(0.2, 1.5, "Differenciation : pas de liaison IL-2Rα (CD25) ⇒ pas d'expansion des Treg ; "
            "demi-vie prolongee par le domaine Fc (IgG1) ;\nagit sur l'immunite innee (NK) et adaptative (CD8+) ; "
            "le BCG reste le partenaire obligatoire (contrainte d'approvisionnement).", fontsize=7.8, color=NAVY, va='center')
    save(fig, "fig01_mechanism")

# ================================================================ FIG 2 : business model
def fig_business():
    fig, ax = plt.subplots(figsize=(11, 5.6)); ax.set_xlim(0, 11); ax.set_ylim(0, 5.8); ax.axis('off'); ax.grid(False)
    def box(x, y, w, h, t, fc):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04,rounding_size=0.12", fc=fc, ec=NAVY))
        ax.text(x + w / 2, y + h / 2, t, ha='center', va='center', color='white', fontsize=7.8, fontweight='bold')
    def arr(a, b, c=NAVY):
        ax.add_patch(FancyArrowPatch(a, b, arrowstyle='-|>', mutation_scale=13, color=c, lw=1.4))
    def lab(x, y, t, c=NAVY):
        ax.text(x, y, t, ha='center', fontsize=7.3, color=c, style='italic',
                bbox=dict(fc='white', ec='none', alpha=0.85, pad=0.5))
    box(4.0, 2.3, 3.0, 1.1, "ImmunityBio\n(production propre + CDMO)", NAVY)
    box(0.2, 4.3, 2.8, 0.9, "Serum Institute\n(rBCG, exclusif mondial)", DKBLUE)
    box(0.2, 0.4, 2.8, 0.9, "Oberland / Infinity\nRIPA : $375M engages", PURPLE)
    box(4.0, 4.4, 3.0, 0.9, "Nant Capital (P. Soon-Shiong)\nnote conv. $480M @ $5.427", PURPLE)
    box(8.0, 4.3, 2.8, 0.9, "Urologues (communautaires\n+ academiques) J-code", TEAL)
    box(8.0, 2.3, 2.8, 1.1, "Payeurs : Medicare\nPart B + commerciaux", GREEN)
    box(8.0, 0.4, 2.8, 0.9, "Partenaires ex-US\n(UE, UK, KSA, EAU)", ACCENT)
    box(4.0, 0.4, 3.0, 0.9, "Ventes nettes 2025 : $113M\nS1-26 : $94.8M (+121%)", GREEN)
    arr((3.0, 4.6), (4.0, 3.3)); lab(3.25, 3.8, "rBCG (EAP)")
    arr((7.0, 3.1), (8.0, 4.5)); lab(7.2, 4.05, "ANKTIVA\n(buy & bill)")
    arr((8.0, 2.75), (7.0, 2.75)); lab(7.5, 2.95, "ASP + 6%", GREEN)
    arr((3.0, 1.05), (4.0, 2.4), PURPLE); lab(2.95, 1.75, "capital non dilutif", PURPLE)
    arr((4.25, 2.3), (3.0, 0.75), RED); lab(4.0, 1.45, "redevance\n5.6-12.5% ventes", RED)
    arr((5.5, 4.4), (5.5, 3.4), PURPLE); lab(5.5, 3.8, "dette subordonnee", PURPLE)
    arr((7.0, 2.4), (8.0, 0.95), ACCENT); lab(7.75, 1.55, "licences", ACCENT)
    arr((5.5, 2.3), (5.5, 1.3))
    ax.text(5.5, 5.6, "Modele economique : biologique a forte marge (buy-and-bill), finance par dette liee + royalties",
            ha='center', fontsize=10.5, fontweight='bold', color=NAVY)
    save(fig, "fig02_business_model")

# ================================================================ FIG 3 : revenue trimestriel
def fig_revenue():
    fig, ax = plt.subplots(figsize=(9, 4.4))
    x = np.arange(len(Q_LBL))
    cols = [NAVY] * N_ACTUAL + [ACCENT] * (len(Q_LBL) - N_ACTUAL)
    bars = ax.bar(x, Q_REV, color=cols, edgecolor='white', hatch=None)
    for i in range(N_ACTUAL, len(Q_LBL)): bars[i].set_hatch('//'); bars[i].set_alpha(0.8)
    for i, v in enumerate(Q_REV):
        ax.text(i, v + 1, f"{v:.1f}", ha='center', fontsize=8)
        if i >= 4:
            g = Q_REV[i] / Q_REV[i - 1] - 1
            ax.text(i, v / 2, f"+{g:.0%}\nQoQ", ha='center', fontsize=7, color='white')
    ax.set_xticks(x); ax.set_xticklabels(Q_LBL, rotation=0, fontsize=8)
    ax.set_ylabel("Ventes nettes produit ($M)")
    ax2 = ax.twinx(); ax2.grid(False)
    ax2.plot(x, [4 * q for q in Q_REV], color=GREEN, marker='o', ms=4, lw=1.6, label="Run-rate annualise (x4)")
    ax2.set_ylabel("Run-rate annualise ($M)", color=GREEN); ax2.spines['right'].set_visible(True)
    ax.set_title("ANKTIVA : 8 trimestres consecutifs de croissance sequentielle")
    ax.bar([0], [0], color=ACCENT, hatch='//', label="Estimations (modele)"); ax.bar([0], [0], color=NAVY, label="Publie (8-K/10-Q)")
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc='upper left', fontsize=8)
    save(fig, "fig03_revenue_quarterly")

# ================================================================ FIG 4 : cours 12 mois
ANCHORS = [(date(2025, 10, 14), 2.45), (date(2025, 10, 31), 2.40), (date(2025, 11, 28), 2.36),
           (date(2025, 12, 30), 1.95), (date(2026, 1, 9), 2.70), (date(2026, 1, 16), 4.90),
           (date(2026, 1, 30), 6.12), (date(2026, 2, 24), 12.27), (date(2026, 2, 27), 9.76),
           (date(2026, 3, 31), 7.17), (date(2026, 4, 30), 7.13), (date(2026, 5, 29), 7.54),
           (date(2026, 6, 30), 9.13), (date(2026, 7, 31), 7.11), (date(2026, 8, 17), 7.92),
           (date(2026, 8, 31), 7.91), (date(2026, 9, 30), 9.48), (date(2026, 10, 1), 9.28),
           (date(2026, 10, 9), 10.51), (date(2026, 10, 13), 9.80), (date(2026, 10, 14), 10.32)]
def price_path():
    days, px = [], []
    for (d0, p0), (d1, p1) in zip(ANCHORS[:-1], ANCHORS[1:]):
        n = (d1 - d0).days
        for k in range(n):
            t = k / n
            base = np.exp((1 - t) * np.log(p0) + t * np.log(p1))
            br = np.sin(np.pi * t) * RNG.normal(0, 0.035)  # pont brownien approx.
            days.append(d0 + timedelta(days=k)); px.append(base * np.exp(br))
    days.append(ANCHORS[-1][0]); px.append(ANCHORS[-1][1])
    keep = [i for i, d in enumerate(days) if d.weekday() < 5]
    return [days[i] for i in keep], np.array([px[i] for i in keep])

def fig_stock():
    d, p = price_path()
    fig, ax = plt.subplots(figsize=(10, 4.6))
    ax.plot(d, p, color=NAVY, lw=1.4)
    ax.fill_between(d, p, alpha=0.08, color=NAVY)
    ev = [(date(2026, 1, 14), "SFDA : CPNPC +\nNMIBC (KSA)", GREEN),
          (date(2026, 1, 15), "FY25 prelim.\n$113M (+700%)", GREEN),
          (date(2026, 2, 10), "CE conditionnelle\nUE (33 pays)", GREEN),
          (date(2026, 3, 26), "IDMC : puissance\nQUILT-2.005 OK", DKBLUE),
          (date(2026, 3, 31), "Financement\n$100M (dont $75M RIPA)", PURPLE),
          (date(2026, 5, 19), "sBLA papillaire\nacceptee (PDUFA 6/1/27)", DKBLUE),
          (date(2026, 8, 4), "T2-26 : $50.7M\nperte nette $230M", ACCENT),
          (date(2026, 10, 14), "FDA : label\npapillaire (anticipe)", RED)]
    for i, (dt, t, c) in enumerate(ev):
        idx = min(range(len(d)), key=lambda j: abs((d[j] - dt).days))
        y = p[idx]
        yt = y + (3.2 if i % 2 == 0 else 5.0)
        if yt > 15.5: yt = y - 3.5
        ax.annotate(t, (d[idx], y), xytext=(d[idx], yt), fontsize=6.8, ha='center', color=c,
                    arrowprops=dict(arrowstyle='-', color=c, lw=0.8))
        ax.plot(d[idx], y, 'o', color=c, ms=4)
    ax.axhline(HI52, ls=':', color=GREEN, lw=1); ax.text(d[5], HI52 + 0.2, f"Plus haut 52s ${HI52}", fontsize=7, color=GREEN)
    ax.axhline(LO52, ls=':', color=RED, lw=1); ax.text(d[5], LO52 - 0.8, f"Plus bas 52s ${LO52}", fontsize=7, color=RED)
    ax.set_ylim(0, 17); ax.set_ylabel("Cours ($)")
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b-%y'))
    ax.set_title(f"IBRX : x{PRICE / ANCHORS[0][1]:.1f} en 12 mois (${ANCHORS[0][1]:.2f} → ${PRICE:.2f})")
    save(fig, "fig04_stock_12m")

# ================================================================ FIG 5 : donnees cliniques comparees
CLIN = [  # nom, RC CIS %, n, DoR mediane (mois), statut
    ("ANKTIVA+BCG\n(QUILT-3.032)", 62, 77, 26.6, NAVY),
    ("TAR-200 / Inlexzo\n(SunRISe-1 C2)", 82, 85, 25.8, GRAY),
    ("Cretostimogene\n(BOND-003)", 75.7, 110, 27.0, GRAY),
    ("Nadofaragene\nAdstiladrin", 51, 103, 9.7, GRAY),
    ("Pembrolizumab\n(KEYNOTE-057)", 41, 96, 16.2, GRAY),
]
def fig_clinical():
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 4.2))
    names = [c[0] for c in CLIN]; y = np.arange(len(CLIN))
    cr = np.array([c[1] for c in CLIN]); n = np.array([c[2] for c in CLIN])
    lo, hi = [], []
    for r, k in zip(cr / 100, n):
        a, b = stats.beta.ppf([0.025, 0.975], r * k + 0.5, (1 - r) * k + 0.5)  # Jeffreys
        lo.append(r - a); hi.append(b - r)
    cols = [c[4] for c in CLIN]
    axs[0].barh(y, cr, color=cols, xerr=[np.array(lo) * 100, np.array(hi) * 100], capsize=3, ecolor='k')
    for i, v in enumerate(cr): axs[0].text(v + hi[i] * 100 + 2, i, f"{v:.0f}% (n={n[i]})", va='center', fontsize=8)
    axs[0].set_yticks(y); axs[0].set_yticklabels(names, fontsize=8); axs[0].invert_yaxis()
    axs[0].set_xlim(0, 115); axs[0].set_xlabel("Reponse complete CIS (%), IC95% Jeffreys")
    axs[0].set_title("Taux de RC - BCG-UR CIS (essais monobras)")
    dor = [c[3] for c in CLIN]
    axs[1].barh(y, dor, color=[TEAL if i == 0 else GRAY for i in range(len(CLIN))])
    for i, v in enumerate(dor): axs[1].text(v + 0.4, i, f"{v:.1f} m", va='center', fontsize=8)
    axs[1].set_yticks(y); axs[1].set_yticklabels([]); axs[1].invert_yaxis()
    axs[1].set_xlabel("Duree mediane de reponse (mois)"); axs[1].set_title("Durabilite (DoR mediane)")
    save(fig, "fig05_clinical_comparison")

# ================================================================ FIG 6 : KM papillaire (reconstruit)
def weibull_from_point(s12, shape):
    # S(t)=exp(-(t/lam)^k) ; S(12)=s12
    lam = 12 / (-np.log(s12)) ** (1 / shape); return lam
def fig_km():
    fig, ax = plt.subplots(figsize=(9, 4.4))
    arms = [("ANKTIVA+BCG (QUILT-3.032 cohorte B, n=80)", 0.582, 0.75, 80, NAVY),
            ("Pembrolizumab (KEYNOTE-057 cohorte B, n=132)", 0.435, 0.80, 132, GRAY),
            ("Nadofaragene (papillaire, n=48)", 0.44, 0.85, 48, ACCENT)]
    t = np.linspace(0, 36, 361)
    for name, s12, k, n, c in arms:
        lam = weibull_from_point(s12, k)
        # simulation d'une cohorte de taille n + censure administrative uniforme 18-48 mois
        T = lam * RNG.weibull(k, n); C = RNG.uniform(18, 48, n)
        obs = np.minimum(T, C); ev = T <= C
        order = np.argsort(obs); obs, ev = obs[order], ev[order]
        s, times, surv = 1.0, [0], [1.0]
        at = n
        for ti, ei in zip(obs, ev):
            if ei: s *= (1 - 1 / at); times.append(ti); surv.append(s)
            at -= 1
        times.append(36); surv.append(s)
        ax.step(times, surv, where='post', color=c, lw=1.2, alpha=0.55)
        ax.plot(t, np.exp(-(t / lam) ** k), color=c, lw=2, label=f"{name} : DFS12={s12:.0%}")
    ax.axvline(12, ls=':', color=GRAY); ax.set_xlim(0, 36); ax.set_ylim(0, 1.02)
    ax.set_xlabel("Mois depuis inclusion"); ax.set_ylabel("Survie sans maladie (DFS)")
    ax.set_title("BCG-UR papillaire seul : DFS reconstruite (Weibull calee sur DFS 12 mois publiee)")
    ax.legend(fontsize=7.5, loc='lower left')
    save(fig, "fig06_km_papillary")

# ================================================================ FIG 7 : Bayesien QUILT-2.005
# Reconstruction des effectifs evaluables a 9 mois coherente avec 84% vs 52%, p=0.0455
QA_X, QA_N = 16, 19   # ANKTIVA+BCG : 84.2%
QB_X, QB_N = 11, 21   # BCG seul : 52.4%
def bayes_quilt():
    a = RNG.beta(1 + QA_X, 1 + QA_N - QA_X, 200000)
    b = RNG.beta(1 + QB_X, 1 + QB_N - QB_X, 200000)
    d = a - b
    rr = np.log((1 - b) / (1 - a))   # log rapport de risque de perte de RC (proxy HR)
    return a, b, d, rr
def fig_bayes():
    a, b, d, rr = bayes_quilt()
    p_pos = (d > 0).mean(); p_15 = (d > 0.15).mean()
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 4.2))
    xs = np.linspace(0, 1, 400)
    axs[0].plot(xs, stats.beta.pdf(xs, 1 + QA_X, 1 + QA_N - QA_X), color=NAVY, lw=2, label=f"ANKTIVA+BCG ({QA_X}/{QA_N})")
    axs[0].plot(xs, stats.beta.pdf(xs, 1 + QB_X, 1 + QB_N - QB_X), color=GRAY, lw=2, label=f"BCG seul ({QB_X}/{QB_N})")
    axs[0].fill_between(xs, stats.beta.pdf(xs, 1 + QA_X, 1 + QA_N - QA_X), alpha=0.15, color=NAVY)
    axs[0].fill_between(xs, stats.beta.pdf(xs, 1 + QB_X, 1 + QB_N - QB_X), alpha=0.15, color=GRAY)
    axs[0].set_xlabel("Taux de RC maintenue a 9 mois"); axs[0].set_ylabel("Densite a posteriori")
    axs[0].set_title("Posteriors Beta(1+x, 1+n-x)"); axs[0].legend(fontsize=8)
    axs[1].hist(d, bins=120, density=True, color=DKBLUE, alpha=0.75)
    axs[1].axvline(0, color=RED, lw=1.5); axs[1].axvline(0.15, color=ACCENT, ls='--', lw=1.3)
    q = np.percentile(d, [2.5, 50, 97.5])
    axs[1].set_title(f"Δ = p_A - p_B : mediane {q[1]:+.2f} [IC95% {q[0]:+.2f}; {q[2]:+.2f}]")
    axs[1].text(0.02, 0.95, f"P(Δ>0) = {p_pos:.1%}\nP(Δ>15 pts) = {p_15:.1%}\n"
                f"HR implicite (perte RC) med. = {np.exp(-np.median(rr)):.2f}",
                transform=axs[1].transAxes, va='top', fontsize=8.5, bbox=dict(fc='white', ec=NAVY))
    axs[1].set_xlabel("Difference absolue de RC maintenue")
    save(fig, "fig07_bayes_quilt2005")
    return p_pos, p_15, q, np.exp(-np.median(rr))

# ================================================================ FIG 8 : puissance + PPoS MC
FINAL_N = 120   # evaluables par bras pour la RC maintenue a l'analyse finale (hypothese)
def power_two_prop(p1, p2, n, alpha=0.05):
    pbar = (p1 + p2) / 2; se0 = np.sqrt(2 * pbar * (1 - pbar) / n); se1 = np.sqrt(p1 * (1 - p1) / n + p2 * (1 - p2) / n)
    z = stats.norm.ppf(1 - alpha / 2)
    return stats.norm.cdf((abs(p1 - p2) - z * se0) / se1)
def ppos_mc(nsim=20000):
    a = RNG.beta(1 + QA_X, 1 + QA_N - QA_X, nsim); b = RNG.beta(1 + QB_X, 1 + QB_N - QB_X, nsim)
    # shrinkage vers l'a priori sceptique (effet d'interim surestime) : 50% du delta
    b2 = b; a2 = b + 0.5 * (a - b)
    xa = RNG.binomial(FINAL_N, np.clip(a2, 0, 1)); xb = RNG.binomial(FINAL_N, np.clip(b2, 0, 1))
    pa, pb = xa / FINAL_N, xb / FINAL_N; pbar = (xa + xb) / (2 * FINAL_N)
    z = (pa - pb) / np.sqrt(2 * pbar * (1 - pbar) / FINAL_N + 1e-12)
    xa_raw = RNG.binomial(FINAL_N, a); zr = (xa_raw / FINAL_N - pb) / np.sqrt(
        2 * ((xa_raw + xb) / (2 * FINAL_N)) * (1 - (xa_raw + xb) / (2 * FINAL_N)) / FINAL_N + 1e-12)
    return (z > 1.96).mean(), (zr > 1.96).mean(), a2 - b2
def fig_power():
    ppos_shr, ppos_raw, dshr = ppos_mc()
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 4.2))
    deltas = np.linspace(0.0, 0.35, 100)
    for n, c in [(60, GRAY), (120, NAVY), (183, TEAL)]:
        axs[0].plot(deltas * 100, [power_two_prop(0.55 + dd, 0.55, n) for dd in deltas], color=c, lw=2, label=f"n={n}/bras")
    axs[0].axhline(0.8, ls='--', color=ACCENT); axs[0].axvline(15, ls=':', color=RED)
    axs[0].set_xlabel("Difference vraie de RC maintenue (pts, base BCG 55%)"); axs[0].set_ylabel("Puissance (alpha=5% bilateral)")
    axs[0].set_title("Puissance QUILT-2.005 (test de Wald 2 proportions)"); axs[0].legend(fontsize=8)
    axs[1].hist(dshr * 100, bins=80, color=PURPLE, alpha=0.7, density=True)
    axs[1].set_title("Monte-Carlo (20 000 essais) : PPoS analyse finale")
    axs[1].set_xlabel("Delta vrai simule apres retrecissement 50% (pts)")
    axs[1].text(0.03, 0.95, f"PPoS (posterior brut) = {ppos_raw:.0%}\nPPoS (retrecissement 50%) = {ppos_shr:.0%}\n"
                f"n final suppose = {FINAL_N}/bras", transform=axs[1].transAxes, va='top', fontsize=8.5,
                bbox=dict(fc='white', ec=PURPLE))
    save(fig, "fig08_power_mc")
    return ppos_raw, ppos_shr

# ================================================================ FIG 9 : sensibilites
def fig_sensitivity():
    base = VPS_BASE
    tests = [
        ("Pic ventes total x0.7 / x1.3", scen(mult_peak=0.7, mult_cis=0.7), scen(mult_peak=1.3, mult_cis=1.3)),
        ("P(succes) BCG-naif 0.35 / 0.85", scen(p_naive=0.35), scen(p_naive=0.85)),
        ("WACC 12.5% / 8.5%", scen(wacc=0.125), scen(wacc=0.085)),
        ("Opex % ventes 40% / 26%", scen(opex=0.40), scen(opex=0.26)),
        ("P(succes) CPNPC 0.05 / 0.45", scen(p_lung=0.05), scen(p_lung=0.45)),
        ("Retard BCG-naif +2 ans / 0", scen(delay=2.0), base),
    ]
    tests.sort(key=lambda t: abs(t[2] - t[1]))
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.4), gridspec_kw={'width_ratios': [1.25, 1]})
    for i, (n, lo, hi) in enumerate(tests):
        axs[0].barh(i, lo - base, left=base, color=RED, alpha=0.8)
        axs[0].barh(i, hi - base, left=base, color=GREEN, alpha=0.8)
        axs[0].text(min(lo, hi) - 0.1, i, f"${min(lo, hi):.2f}", ha='right', va='center', fontsize=7.5)
        axs[0].text(max(lo, hi) + 0.1, i, f"${max(lo, hi):.2f}", ha='left', va='center', fontsize=7.5)
    axs[0].axvline(base, color=NAVY, lw=1.5); axs[0].axvline(PRICE, color=ACCENT, ls='--', lw=1.5)
    axs[0].text(PRICE, len(tests) - 0.4, f"cours ${PRICE}", color=ACCENT, fontsize=8, ha='center')
    axs[0].set_yticks(range(len(tests))); axs[0].set_yticklabels([t[0] for t in tests], fontsize=8)
    axs[0].set_xlabel("Valeur rNPV par action diluee ($)"); axs[0].set_title(f"Tornado (base ${base:.2f})")
    axs[0].set_xlim(0, max(PRICE + 2, max(t[2] for t in tests) + 2))
    mults = np.linspace(0.6, 2.6, 11); ps = np.linspace(0.2, 1.0, 9)
    Z = np.array([[scen(mult_peak=m, mult_cis=m, p_naive=p) for m in mults] for p in ps])
    im = axs[1].imshow(Z, origin='lower', aspect='auto', cmap='RdYlGn',
                       extent=[mults[0], mults[-1], ps[0], ps[-1]], vmin=0, vmax=2 * PRICE)
    cs = axs[1].contour(mults, ps, Z, levels=[PRICE], colors=NAVY, linewidths=2)
    axs[1].clabel(cs, fmt={PRICE: f"${PRICE}"}, fontsize=8)
    axs[1].set_xlabel("Multiplicateur des pics de ventes (base = 1)"); axs[1].set_ylabel("P(succes) BCG-naif")
    axs[1].set_title("Valeur/action : pics x P(succes)"); fig.colorbar(im, ax=axs[1], label="$/action")
    axs[1].grid(False)
    save(fig, "fig09_sensitivity")

# ================================================================ FIG 10 : TAM
def fig_tam():
    yrs = np.arange(2024, 2034)
    # ventes mondiales NMIBC haut risque (Md$) ; base ~2.0 Md$ 2024, TCAC segmentaire
    seg = {"BCG-naif haut risque": (0.9, 0.17), "BCG-UR CIS": (0.55, 0.20),
           "BCG-UR papillaire": (0.35, 0.19), "Risque intermediaire (LG-IR)": (0.25, 0.22)}
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.3), gridspec_kw={'width_ratios': [1.5, 1]})
    bottom = np.zeros(len(yrs)); cols = [NAVY, DKBLUE, TEAL, GOLD]
    for (k, (b0, g)), c in zip(seg.items(), cols):
        v = b0 * (1 + g) ** (yrs - 2024)
        axs[0].fill_between(yrs, bottom, bottom + v, color=c, alpha=0.85, label=k); bottom += v
    axs[0].set_ylabel("Marche NMIBC (Md$)"); axs[0].legend(fontsize=7.5, loc='upper left')
    axs[0].set_title(f"TAM NMIBC : {bottom[0]:.1f} Md$ (2024) → {bottom[-1]:.1f} Md$ (2033)")
    pts = {"Nouveaux cas vessie US/an": 85, "dont NMIBC (~75%)": 64, "Haut risque (~50%)": 30,
           "BCG-UR / an": 8, "Prevalents BCG-UR": 20}
    axs[1].barh(list(pts.keys())[::-1], list(pts.values())[::-1], color=[GRAY, PURPLE, TEAL, DKBLUE, NAVY])
    for i, v in enumerate(list(pts.values())[::-1]): axs[1].text(v + 1, i, f"{v}k", va='center', fontsize=8)
    axs[1].set_xlabel("Patients (milliers, US)"); axs[1].set_title("Entonnoir epidemiologique US")
    save(fig, "fig10_tam")

# ================================================================ FIG 11 : comparables
def fig_comps():
    comps = [("ImmunityBio (IBRX)", MCAP, 1.1, NAVY), ("CG Oncology (CGON)", 5.5, 3.0, GRAY),
             ("UroGen (URGN)", 2.3, 0.75, GRAY), ("enGene (ENGN)", 0.13, 0.4, GRAY)]
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 3.8))
    n = [c[0] for c in comps]; m = [c[1] for c in comps]
    axs[0].barh(n, m, color=[c[3] for c in comps]); axs[0].invert_yaxis()
    for i, v in enumerate(m): axs[0].text(v + 0.15, i, f"{v:.2f} Md$", va='center', fontsize=8)
    axs[0].set_xlabel("Capitalisation (Md$, debut oct. 2026)"); axs[0].set_title("Pairs NMIBC cotes"); axs[0].set_xlim(0, 13.5)
    r = [c[1] / c[2] for c in comps]
    axs[1].barh(n, r, color=[ACCENT if i == 0 else GRAY for i in range(len(comps))]); axs[1].invert_yaxis()
    for i, v in enumerate(r): axs[1].text(v + 0.2, i, f"{v:.1f}x", va='center', fontsize=8)
    axs[1].set_yticklabels([]); axs[1].set_xlabel("Cap. / pic de ventes ajuste du risque (x)\n(Guggenheim pour IBRX/CGON ; estimations internes URGN/ENGN)", fontsize=8)
    axs[1].set_title("Prime de valorisation relative")
    save(fig, "fig11_comparables")

# ================================================================ FIG 12 : precedents M&A
MA = [  # cible / acquereur / annee, valeur Md$, prime %, EV/pic ventes approx
    ("Seagen / Pfizer (2023)", 43.0, 33, "Padcev (vessie)"),
    ("Intra-Cellular / J&J (2025)", 14.6, 39, "CNS"),
    ("ImmunoGen / AbbVie (2023)", 10.1, 95, "ovaire"),
    ("Blueprint / Sanofi (2025)", 9.5, 27, "SM/onco"),
    ("Merus / Genmab (2025)", 8.0, 41, "tete-cou"),
    ("Mirati / BMS (2023)", 4.8, 52, "poumon KRAS"),
    ("SpringWorks / Merck KGaA (2025)", 3.9, 26, "tumeurs rares"),
    ("Ambrx / J&J (2024)", 2.0, 105, "ADC"),
]
def fig_ma():
    fig, ax = plt.subplots(figsize=(10, 4.6))
    names = [m[0] for m in MA] + ["IBRX (cap. actuelle)", "IBRX (cap. diluee)"]
    vals = [m[1] for m in MA] + [MCAP, MCAP_FD]
    cols = [GRAY if "Seagen" not in m[0] else TEAL for m in MA] + [NAVY, ACCENT]
    ax.barh(names, vals, color=cols); ax.invert_yaxis()
    for i, v in enumerate(vals):
        lab = f"{v:.1f} Md$" + (f"  (prime {MA[i][2]}%, {MA[i][3]})" if i < len(MA) else "")
        ax.text(v + 0.4, i, lab, va='center', fontsize=7.8)
    ax.set_xlabel("Valeur de transaction (Md$)"); ax.set_xlim(0, 58)
    ax.set_title("Precedents M&A oncologie stade commercial vs valorisation IBRX")
    save(fig, "fig12_ma_precedents")

def fig_premium():
    prem = np.linspace(0, 0.8, 50)
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 4.0))
    for base, lab, c in [(PRICE, "sur cours actuel", NAVY), (VPS_BASE, "sur rNPV base", GRAY),
                         (SCEN[3][2], "sur rNPV bull", GREEN)]:
        axs[0].plot(prem * 100, base * (1 + prem), color=c, lw=2, label=f"Prime {lab} (${base:.2f})")
    axs[0].axhline(PRICE, ls='--', color=ACCENT); axs[0].axvspan(26, 52, color=GOLD, alpha=0.15, label="Prime mediane deals 26-52%")
    axs[0].set_xlabel("Prime de controle (%)"); axs[0].set_ylabel("Prix implicite ($/action)")
    axs[0].legend(fontsize=7.5); axs[0].set_title("Prix d'acquisition implicite")
    peak = np.linspace(1, 6, 50)
    for mult, c in [(3, GRAY), (5, DKBLUE), (7, TEAL)]:
        eqv = (peak * mult * 1000 + CASH_EST) / SH_FD
        axs[1].plot(peak, eqv, color=c, lw=2, label=f"{mult}x pic de ventes")
    axs[1].axhline(PRICE, ls='--', color=ACCENT, label=f"cours ${PRICE}")
    axs[1].set_xlabel("Pic de ventes non ajuste (Md$)"); axs[1].set_ylabel("$/action dilue")
    axs[1].set_title("Valeur de rachat : multiple x pic de ventes"); axs[1].legend(fontsize=7.5)
    save(fig, "fig13_premium")

# ================================================================ FIG 14 : financials
QF = ["T4-24", "T1-25", "T2-25", "T3-25", "T4-25", "T1-26", "T2-26", "T3-26E", "T4-26E", "T1-27E", "T2-27E", "T3-27E", "T4-27E"]
CASH_Q = [149.8, 125.0, 153.7, 257.8, 242.8, 380.9, 357.4]
def project_cash():
    cash = CASH_Q[:]; rev = [56.5, 63.5, 78, 85, 92, 99]   # 2027E = 354 M$ (coherent avec le DCF)
    opex_cash = [118, 120, 121, 122, 123, 124]   # COGS+SG&A+R&D cash + redevance
    burn = [o - r for o, r in zip(opex_cash, rev)]
    for b in burn: cash.append(cash[-1] - b)
    return cash, burn
SHARES_Q = [826, 880, 915, 985, 1010, 1047, 1060, 1062, 1066, 1070, 1074, 1078, 1082]
DEBT_Q = [505, 505, 505, 505, 505, 480, 480, 480, 480, 480, 480, 480, 480]
RIPA_Q = [310, 315, 320, 325, 325, 404, 412, 420, 428, 436, 444, 452, 460]
def fig_fin():
    cash, burn = project_cash()
    fig, ax = plt.subplots(figsize=(10, 4.6)); x = np.arange(len(QF))
    ax.bar(x - 0.2, cash, width=0.4, color=[NAVY if i < 7 else DKBLUE for i in range(len(QF))], label="Tresorerie + titres ($M)")
    ax.bar(x + 0.2, DEBT_Q, width=0.4, color=RED, alpha=0.75, label="Note conv. Nant ($M)")
    ax.bar(x + 0.2, RIPA_Q, bottom=DEBT_Q, width=0.4, color=PURPLE, alpha=0.6, label="Passif RIPA Oberland ($M)")
    for i in range(7, len(QF)): ax.patches[i].set_hatch('//')
    ax.set_xticks(x); ax.set_xticklabels(QF, fontsize=7.5); ax.set_ylabel("$M")
    ax2 = ax.twinx(); ax2.grid(False); ax2.spines['right'].set_visible(True)
    ax2.plot(x, SHARES_Q, color=ACCENT, marker='o', lw=2, label="Actions en circulation (M)")
    ax2.set_ylabel("Actions (M)", color=ACCENT); ax2.set_ylim(700, 1200)
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=7.5, loc='upper left', ncol=2)
    ax.set_title("Bilan : tresorerie (publiee puis projetee) vs dette liee + RIPA, et dilution")
    save(fig, "fig14_financials")
    return cash, burn

# ================================================================ FIG 15 : revenue ramp par segment
def fig_ramp():
    _, _, tot, sales = run_dcf(SEG_BASE)
    fig, ax = plt.subplots(figsize=(10, 4.6)); bottom = np.zeros(len(YEARS))
    cols = [NAVY, DKBLUE, TEAL, GOLD, PURPLE, GRAY]
    for (k, v), c in zip(SEG_BASE.items(), cols):
        y = v[3] * sales[k]
        ax.bar(YEARS, y, bottom=bottom, color=c, label=f"{k} (P={v[3]:.0%})"); bottom += y
    ax.plot(YEARS, bottom, color=ACCENT, marker='o', ms=3)
    for yr in (2027, 2030, 2034):
        i = list(YEARS).index(yr); ax.text(yr, bottom[i] + 40, f"${bottom[i] / 1000:.2f}Md", ha='center', fontsize=8)
    ax.axvline(LOE + 0.5, ls='--', color=RED); ax.text(LOE + 0.6, bottom.max() * 0.9, "LOE ~2036\n(biosimilaires)", color=RED, fontsize=8)
    ax.set_ylabel("Ventes ponderees par la probabilite ($M)"); ax.legend(fontsize=7, loc='upper left')
    ax.set_title("Trajectoire de ventes modelisee (ajustee du risque), par segment")
    save(fig, "fig15_revenue_ramp")
    return dict(zip(YEARS, bottom))

# ================================================================ FIG 16 : waterfall
def fig_waterfall():
    items = [(k, v) for k, v in NPV_BASE.items()] + [("Overhead plateforme", OVH_BASE), ("Tresorerie nette est.", CASH_EST)]
    fig, ax = plt.subplots(figsize=(10.5, 4.8)); cum = 0
    for i, (k, v) in enumerate(items):
        c = GREEN if v >= 0 else RED
        if "Tresorerie" in k: c = TEAL
        ax.bar(i, v, bottom=cum, color=c, edgecolor='white')
        ax.text(i, cum + v + (60 if v >= 0 else -160), f"{v / SH_FD:+.2f}$\n({v:,.0f}M)", ha='center', fontsize=7.2)
        cum += v
    ax.bar(len(items), cum, color=NAVY); ax.text(len(items), cum + 60, f"${cum / SH_FD:.2f}\n({cum:,.0f}M)", ha='center', fontsize=8, fontweight='bold')
    mc = PRICE * SH_FD
    ax.bar(len(items) + 1, mc, color=ACCENT); ax.text(len(items) + 1, mc + 60, f"${PRICE:.2f}\n({mc:,.0f}M)", ha='center', fontsize=8, fontweight='bold')
    labels = ["CIS\nUS", "Papillaire\nUS", "BCG-naif\n(P=60%)", "Ex-US\nNMIBC", "CPNPC\n(P=20%)", "Pipeline\n(P=10%)",
              "Overhead\nplateforme", "Tresorerie\nest. 30/09", "Valeur\nintrinseque", "Cap. diluee\nau cours"]
    ax.set_xticks(range(len(labels))); ax.set_xticklabels(labels, fontsize=7.5)
    ax.set_ylabel("$M (diluee)"); ax.set_title("Somme des parties rNPV vs capitalisation diluee")
    ax.set_ylim(0, max(mc, cum) * 1.15)
    save(fig, "fig16_waterfall")

# ================================================================ FIG 17 : scenarios
def fig_scen():
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.3), gridspec_kw={'width_ratios': [1.4, 1]})
    names = [s[0].replace("\\&", "&") for s in SCEN]; p = [s[1] for s in SCEN]; v = [s[2] for s in SCEN]
    cols = [RED, ACCENT, DKBLUE, GREEN, TEAL, PURPLE]
    axs[0].bar(names, v, color=cols)
    lo = [x * 0.8 for x in v]; hi = [x * 1.2 for x in v]
    axs[0].errorbar(names, v, yerr=[np.array(v) - lo, np.array(hi) - np.array(v)], fmt='none', ecolor='k', capsize=4)
    for i, (pp, vv) in enumerate(zip(p, v)): axs[0].text(i, hi[i] + 0.4, f"${vv:.2f}\np={pp:.0%}", ha='center', fontsize=8)
    axs[0].axhline(PRICE, color=ACCENT, ls='--', lw=1.5, label=f"Cours ${PRICE}")
    axs[0].axhline(EV_WEIGHTED, color=NAVY, ls='-', lw=1.5, label=f"EV pondere ${EV_WEIGHTED:.2f}")
    axs[0].set_ylabel("$/action (fourchette ±20%)"); axs[0].legend(fontsize=8); axs[0].set_title("Scenarios probabilises")
    axs[0].set_ylim(0, max(hi) * 1.25)
    # distribution MC du payoff
    sims = RNG.choice(len(SCEN), size=50000, p=p)
    vals = np.array(v)[sims] * np.exp(RNG.normal(0, 0.18, 50000))
    axs[1].hist(vals, bins=80, color=DKBLUE, alpha=0.8, density=True)
    axs[1].axvline(PRICE, color=ACCENT, ls='--'); axs[1].axvline(vals.mean(), color=NAVY)
    axs[1].set_title(f"Distribution MC : P(valeur > cours) = {(vals > PRICE).mean():.0%}")
    axs[1].set_xlabel("$/action")
    save(fig, "fig17_scenarios")
    return (vals > PRICE).mean()

# ================================================================ FIG 18 : risk matrix
RISKS = [  # nom, probabilite, impact (1-5), categorie couleur
    ("Dilution / refinancement note Nant", 0.65, 3.5, PURPLE),
    ("Concurrence Inlexzo (J&J) / creto", 0.70, 4.0, RED),
    ("QUILT-2.005 non concluant / FDA", 0.35, 4.8, RED),
    ("Offre BCG / rBCG insuffisante", 0.45, 3.0, ACCENT),
    ("Gouvernance (controle Soon-Shiong)", 0.80, 2.5, PURPLE),
    ("Relation FDA conflictuelle (RTF 2025)", 0.40, 3.2, ACCENT),
    ("Remboursement / ASP erosion", 0.30, 2.6, TEAL),
    ("Echec CPNPC ResQ201A", 0.60, 1.8, GRAY),
    ("Fabrication (CRL 2023 historique)", 0.15, 4.0, ACCENT),
    ("Volatilite / momentum retail", 0.85, 2.0, GRAY),
]
def fig_risk():
    fig, ax = plt.subplots(figsize=(9.5, 5.6))
    xx, yy = np.meshgrid(np.linspace(0, 1, 100), np.linspace(1, 5, 100))
    ax.contourf(xx, yy, xx * yy, levels=20, cmap='RdYlGn_r', alpha=0.18)
    for i, (n, p, imp, c) in enumerate(RISKS):
        ax.scatter(p, imp, s=900 * p * imp / 3, color=c, alpha=0.7, edgecolor='k')
        ax.text(p, imp, str(i + 1), ha='center', va='center', color='white', fontweight='bold', fontsize=9)
    ax.set_xlim(0, 1); ax.set_ylim(1, 5.3); ax.set_xlabel("Probabilite (horizon 24 mois)"); ax.set_ylabel("Impact sur la valeur (1-5)")
    leg = "\n".join(f"{i + 1}. {r[0]}" for i, r in enumerate(RISKS))
    ax.text(1.02, 0.98, leg, transform=ax.transAxes, va='top', fontsize=7.8, bbox=dict(fc='white', ec=NAVY))
    ax.set_title("Matrice des risques (taille = probabilite x impact)")
    save(fig, "fig18_risk_matrix")

# ================================================================ FIG 19 : timeline
CATS = [(date(2026, 10, 14), "FDA : label papillaire seul (fait)", GREEN, 0.8),
        (date(2026, 11, 5), "Resultats T3-26", ACCENT, -0.8),
        (date(2026, 12, 15), "Topline final QUILT-2.005", RED, 1.7),
        (date(2026, 12, 31), "Depot sBLA BCG-naif\n(guidance 2026)", RED, -1.7),
        (date(2027, 1, 6), "Ex-PDUFA papillaire\n(deja acte)", GRAY, 2.6),
        (date(2027, 2, 25), "FY26 + guidance 2027", ACCENT, -2.6),
        (date(2027, 3, 15), "Acceptation sBLA\nBCG-naif (60 j)", DKBLUE, 0.9),
        (date(2027, 6, 15), "Lancements UE\n(pays par pays)", TEAL, -1.0),
        (date(2027, 9, 30), "Approvisionnement rBCG\n(BLA / EAP elargi)", PURPLE, 1.6),
        (date(2027, 12, 31), "PDUFA BCG-naif\n(standard, est.)", RED, -1.7),
        (date(2028, 6, 30), "Lecture interim ResQ201A\n(CPNPC)", GRAY, 1.0)]
def fig_timeline():
    fig, ax = plt.subplots(figsize=(12, 5.2))
    d0, d1 = date(2026, 9, 1), date(2028, 9, 1)
    ax.plot([d0, d1], [0, 0], color=NAVY, lw=3)
    for d, t, c, h in CATS:
        ax.plot([d, d], [0, h], color=c, lw=1.2); ax.plot(d, 0, 'o', color=c, ms=7)
        ax.text(d, h + (0.12 if h > 0 else -0.12), f"{d.strftime('%b %y')}\n{t}", ha='center',
                va='bottom' if h > 0 else 'top', fontsize=6.8, color=c, fontweight='bold')
    ax.set_ylim(-3.6, 3.6); ax.set_yticks([]); ax.grid(False); ax.spines['left'].set_visible(False)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b-%y')); ax.set_xlim(d0, d1)
    ax.set_title("Calendrier des catalyseurs (rouge = binaire majeur)")
    save(fig, "fig19_timeline")

# ================================================================ FIG 20 : capital / dilution
def fig_cap():
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 4.0))
    parts = [SH_BASIC, SH_CONV, SH_OTHER]; labs = ["Actions ordinaires", "Note conv. Nant", "Warrants/options (est.)"]
    axs[0].pie(parts, labels=[f"{l}\n{p:.0f}M" for l, p in zip(labs, parts)], colors=[NAVY, PURPLE, GOLD],
               autopct='%1.0f%%', startangle=90, textprops={'fontsize': 8}, pctdistance=0.75,
               wedgeprops=dict(width=0.45, edgecolor='white'))
    axs[0].set_title(f"Base diluee : {SH_FD:.0f}M actions")
    yrs = ["2021", "2022", "2023", "2024", "2025", "T2-26"]; sh = [397, 452, 545, 826, 1010, 1060]
    axs[1].bar(yrs, sh, color=[GRAY] * 5 + [NAVY])
    for i, v in enumerate(sh): axs[1].text(i, v + 15, f"{v}", ha='center', fontsize=8)
    cagr = (sh[-1] / sh[0]) ** (1 / 4.5) - 1
    axs[1].set_title(f"Actions en circulation (TCAC {cagr:.0%}/an)"); axs[1].set_ylabel("M actions")
    save(fig, "fig20_capital_dilution")
    return cagr

# ================================================================ FIG 21 : reverse DCF + VE/ventes
def fig_evsales():
    ev = (MCAP * 1000 + NOTE_NANT + RIPA_LIAB - CASH_EST) / 1000
    fwd = sum(Q_REV[-4:])                      # ventes produit 2026E (T1-T4)
    sales = run_dcf(SEG_BASE)[3]
    rev27 = sum(SEG_BASE[k][3] * sales[k][1] for k in SEG_BASE)
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 4.1))
    m = np.linspace(0.5, 4.0, 40)
    v = [scen(mult_peak=x, mult_cis=x) for x in m]
    axs[0].plot(m * BASE_PEAK_TOTAL_RISK / 1000, v, color=NAVY, lw=2)
    axs[0].axhline(PRICE, ls='--', color=ACCENT); axs[0].axvline(IMPL_MULT * BASE_PEAK_TOTAL_RISK / 1000, ls=':', color=RED)
    axs[0].axvline(BASE_PEAK_TOTAL_RISK / 1000, ls=':', color=GRAY)
    axs[0].text(IMPL_MULT * BASE_PEAK_TOTAL_RISK / 1000 + 0.1, 2, f"implicite :\n{IMPL_MULT * BASE_PEAK_TOTAL_RISK / 1000:.1f} Md$", color=RED, fontsize=8)
    axs[0].text(BASE_PEAK_TOTAL_RISK / 1000 + 0.1, 14, f"modele base :\n{BASE_PEAK_TOTAL_RISK / 1000:.1f} Md$", color=GRAY, fontsize=8)
    axs[0].set_xlabel("Pic de ventes cumule ajuste du risque (Md$)"); axs[0].set_ylabel("$/action dilue")
    axs[0].set_title("Reverse DCF : ce que le cours anticipe")
    yrs = ["2025", "2026E", "2027E"]; rv = [113, fwd, rev27]
    axs[1].bar(yrs, [ev * 1000 / r for r in rv], color=[GRAY, NAVY, DKBLUE])
    for i, r in enumerate(rv): axs[1].text(i, ev * 1000 / r + 2, f"{ev * 1000 / r:.0f}x\n(ventes {r:.0f} M$)", ha='center', fontsize=8)
    axs[1].set_ylabel("VE / ventes (x)"); axs[1].set_title(f"VE {ev:.1f} Md$ : multiples de ventes")
    axs[1].set_ylim(0, ev * 1000 / 113 * 1.2)
    save(fig, "fig21_reverse_dcf")
    return ev, fwd, rev27

# ================================================================ RUN
if __name__ == "__main__":
    print("Generation des figures ...")
    fig_moa(); fig_business(); fig_revenue(); fig_stock(); fig_clinical(); fig_km()
    p_pos, p_15, dq, hr_imp = fig_bayes()
    ppos_raw, ppos_shr = fig_power()
    fig_sensitivity(); fig_tam(); fig_comps(); fig_ma(); fig_premium()
    cash_path, burn = fig_fin(); sales_path = fig_ramp(); fig_waterfall()
    p_above = fig_scen(); fig_risk(); fig_timeline(); cagr = fig_cap(); ev_ent, rev26, rev27 = fig_evsales()

    # runway : premier trimestre ou la tresorerie projetee < 100 M$
    runway_q = next((QF[i] for i, c in enumerate(cash_path) if c < 100), "T1-28E")
    macros = {
        "Price": f"{PRICE:.2f}", "PricePrev": f"{PRICE_PREV:.2f}", "HiLo": f"{LO52:.2f}--{HI52:.2f}",
        "ShBasic": f"{SH_BASIC:,.0f}", "ShFD": f"{SH_FD:,.0f}", "ShConv": f"{SH_CONV:.1f}", "ShOther": f"{SH_OTHER:.0f}",
        "Mcap": f"{MCAP:.1f}", "McapFD": f"{MCAP_FD:.1f}", "EntVal": f"{ev_ent:.1f}",
        "CashQtwo": f"{CASH_Q2:.1f}", "CashEst": f"{CASH_EST:.0f}", "RevA": f"{rev26:.0f}", "RevB": f"{rev27:.0f}",
        "EVsales": f"{ev_ent * 1000 / rev26:.0f}",
        "VPSBase": f"{VPS_BASE:.2f}", "EVBase": f"{EV_BASE:,.0f}", "OvhBase": f"{OVH_BASE:,.0f}",
        "EqBase": f"{EV_BASE + CASH_EST:,.0f}",
        "EVW": f"{EV_WEIGHTED:.2f}", "Upside": f"{UPSIDE * 100:+.0f}", "PAbove": f"{p_above * 100:.0f}",
        "ImplMult": f"{IMPL_MULT:.2f}", "RiskPeak": f"{BASE_PEAK_TOTAL_RISK / 1000:.2f}",
        "PPos": f"{p_pos * 100:.1f}", "PFifteen": f"{p_15 * 100:.0f}", "DMed": f"{dq[1] * 100:.0f}",
        "DLo": f"{dq[0] * 100:.0f}", "DHi": f"{dq[2] * 100:.0f}", "HRimp": f"{hr_imp:.2f}",
        "PPoSRaw": f"{ppos_raw * 100:.0f}", "PPoSShr": f"{ppos_shr * 100:.0f}",
        "SalesTT": f"{sales_path[2030] / 1000:.2f}", "SalesTF": f"{sales_path[2034] / 1000:.2f}",
        "ShareCAGR": f"{cagr * 100:.0f}", "Runway": runway_q, "Wacc": f"{WACC * 100:.1f}",
        "CashEndTwentySeven": f"{cash_path[-1]:.0f}",
    }
    for i, (k, v) in enumerate(NPV_BASE.items()):
        macros[f"Npv{'ABCDEF'[i]}"] = f"{v:,.0f}"; macros[f"Vps{'ABCDEF'[i]}"] = f"{v / SH_FD:.2f}"
    for i, s in enumerate(SCEN):
        macros[f"Sc{'ABCDEF'[i]}"] = f"{s[2]:.2f}"; macros[f"ScP{'ABCDEF'[i]}"] = f"{s[1] * 100:.0f}"
        macros[f"ScC{'ABCDEF'[i]}"] = f"{s[1] * s[2]:.2f}"
    with open(os.path.join(OUT, "values.tex"), "w") as f:
        f.write("% Genere automatiquement par ibrx_model.py -- ne pas editer\n")
        for k, v in macros.items():
            f.write(f"\\newcommand{{\\m{k}}}{{{v.replace(',', '{,}')}}}\n")
    for k, v in macros.items(): print(f"  {k:20s} {v}")
    print("OK :", len([f for f in os.listdir(OUT) if f.endswith('.pdf')]), "figures")
