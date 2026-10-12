"""
Write paper/numbers.tex from the reports in eval/results/, so every number in
the paper comes from a result file. Missing results become a red "??".

    python paper/make_numbers.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(os.path.dirname(HERE), "eval", "results")
macros = {}


def load(name):
    path = os.path.join(RESULTS, f"{name}.json")
    return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else None


def pct(x):
    return f"{100 * x:.1f}"


def ci_pct(ci):
    return f"[{100 * ci[0]:.1f}, {100 * ci[1]:.1f}]"


# ---------------------------------------------------------------- translation
SYS = {"nllb-600m": "SixHundred", "nllb-1.3b": "OneThree", "nllb-3.3b": "ThreeB"}
mt = load("mt_flores_devtest")
if mt:
    for direction, tag in (("kam_to_en", "KamEn"), ("en_to_kam", "EnKam")):
        tiers = mt["directions"].get(direction, {}).get("tiers", {})

        def mark(v, tier):
            """dagger: significantly better than 600M; ddagger: significantly worse (p < 0.05)."""
            base = tiers[tier].get("nllb-600m")
            if not base or v.get("p_vs_baseline", 1) >= 0.05:
                return ""
            return "$^\\dagger$" if v["chrf++"] > base["chrf++"] else "$^\\ddagger$"

        for s, name in SYS.items():
            t0 = tiers.get("T0", {}).get(s)
            if not t0:
                continue
            sig = mark(t0, "T0")
            macros[f"mt{tag}{name}"] = f"{t0['chrf++']:.1f}"
            macros[f"mt{tag}{name}CI"] = f"{t0['chrf++']:.1f}{sig} {{\\scriptsize[{t0['chrf++_ci95'][0]:.1f}, {t0['chrf++_ci95'][1]:.1f}]}}"
            macros[f"mt{tag}{name}BLEU"] = f"{t0['bleu']:.1f}"
            t1 = tiers.get("T1", {}).get(s)
            if t1:
                sig1 = mark(t1, "T1")
                macros[f"mt{tag}{name}Tone"] = f"{t1['chrf++']:.1f}{sig1} {{\\scriptsize[{t1['chrf++_ci95'][0]:.1f}, {t1['chrf++_ci95'][1]:.1f}]}}"
                if s == "nllb-3.3b":
                    macros["mtTildeGain"] = f"{t1['chrf++'] - t0['chrf++']:.1f}"

    c = mt.get("controls", {})
    if "600m_fp32_vs_fp16" in c:
        v = c["600m_fp32_vs_fp16"]
        macros["ctrlFpThirtyTwo"] = f"{v['chrf++_fp32']:.1f}"
        macros["ctrlFpSixteen"] = f"{v['chrf++_fp16']:.1f}"
        macros["ctrlFpIdentical"] = f"{v['identical_outputs']:,}"
    if "3.3b_local_vs_space" in c:
        v = c["3.3b_local_vs_space"]
        macros["ctrlLocalN"] = str(v["n"])
        macros["ctrlLocalSpace"] = f"{v['chrf++_space']:.1f}"
        macros["ctrlLocalLocal"] = f"{v['chrf++_local']:.1f}"
        macros["ctrlLocalSixHundred"] = f"{v['chrf++_600m']:.1f}"
        macros["ctrlLocalIdentical"] = str(v["identical_outputs"])

# ---------------------------------------------------------------- ASR
asr = load("asr_fleurs_test")
if asr:
    for s, name in (("farmerline", "Farmerline"), ("mms", "Mms")):
        r = asr["systems"].get(s)
        if not r:
            continue
        for tier, tn in (("K0", "Kzero"), ("K1", "Kone")):
            v = r[tier]
            macros[f"asr{name}{tn}"] = f"{pct(v['cer'])} {{\\scriptsize{ci_pct(v['cer_ci95'])}}}"
            macros[f"asr{name}WER{tn}"] = f"{pct(v['wer'])} {{\\scriptsize{ci_pct(v['wer_ci95'])}}}"
            macros[f"asr{name}{tn}F"] = pct(v["cer_female"])
            macros[f"asr{name}{tn}M"] = pct(v["cer_male"])
        macros[f"asr{name}CER"] = pct(r["K0"]["cer"])
        macros["asrNFemale"] = str(r["K0"]["n_female"])
        macros["asrNMale"] = str(r["K0"]["n_male"])

# ---------------------------------------------------------------- TTS
tts = load("tts_asr_roundtrip")
if tts:
    names = {"real": "Real", "omnivoice-female": "OmniFemale", "omnivoice-male": "OmniMale", "mms-swh": "Swh", "mms-kik": "Kik"}
    paired = tts.get("paired_vs_mms-swh", {})
    for v, name in names.items():
        r = tts["voices"].get(v)
        if not r:
            continue
        p = paired.get(v, {}).get("p_value_one_sided")
        sig = "$^\\dagger$" if p is not None and p < 0.05 else ""
        macros[f"tts{name}CER"] = pct(r["cer_k1"])
        macros[f"tts{name}Row"] = (f"{pct(r['cer_k1'])}{sig} {{\\scriptsize{ci_pct(r['cer_k1_ci95'])}}} & "
                                   f"{pct(r['wer_k1'])} {{\\scriptsize{ci_pct(r['wer_k1_ci95'])}}}")

ALL = ["ctrlFpThirtyTwo", "ctrlFpSixteen", "ctrlFpIdentical", "ctrlLocalN", "ctrlLocalSpace", "ctrlLocalLocal",
       "ctrlLocalSixHundred", "ctrlLocalIdentical", "mtKamEnSixHundred", "mtKamEnThreeB", "mtEnKamThreeB", "mtTildeGain", "asrFarmerlineCER", "asrMmsCER",
       "asrNFemale", "asrNMale", "ttsOmniFemaleCER", "ttsOmniMaleCER", "ttsRealCER", "ttsSwhCER", "ttsKikCER"]
for tag in ("KamEn", "EnKam"):
    for name in SYS.values():
        ALL += [f"mt{tag}{name}CI", f"mt{tag}{name}BLEU"] + ([f"mt{tag}{name}Tone"] if tag == "EnKam" else [])
for name in ("Farmerline", "Mms"):
    for tn in ("Kzero", "Kone"):
        ALL += [f"asr{name}{tn}", f"asr{name}WER{tn}", f"asr{name}{tn}F", f"asr{name}{tn}M"]
ALL += [f"tts{n}Row" for n in ("Real", "OmniFemale", "OmniMale", "Swh", "Kik")]

with open(os.path.join(HERE, "numbers.tex"), "w", encoding="utf-8") as f:
    f.write("% Generated by paper/make_numbers.py from eval/results/*.json -- do not edit.\n")
    for k in sorted(set(ALL) | set(macros)):
        if k.endswith("Row") and k not in macros:
            macros[k] = "\\tbd & \\tbd"
        f.write(f"\\newcommand{{\\{k}}}{{{macros.get(k, chr(92) + 'tbd')}}}\n")
print(f"{len(macros)} numbers written; {len(set(ALL) - set(macros))} still missing")
