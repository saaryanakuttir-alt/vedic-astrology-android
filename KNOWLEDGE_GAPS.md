# Knowledge gaps - what the app does NOT have yet, and what is needed to add it

Rule for this project: only implement what is known from a reliable source; use the AstroSage report
(`AstroSageKundli_1789856497766.pdf`, Sammya Das, 29 May 1992 07:06 Howrah) ONLY to check numbers, never to copy
text. Everything below is deliberately left out or approximate until the missing knowledge is available.
Each item says what is missing and what a source would need to provide, so the next build can pick it up.

## Planet strength (Shadbala / Bhavabala) - `engine/shadbala.py`
Implemented and matching AstroSage: Uchcha, Ojayugma, Kendra, Dig, Nathonnatha, Paksha, Tribhaga, Vara, Ayana, Naisargika.
Shown as comparative "strength points", NOT the traditional rupa totals, because these are missing:

| Missing | Why | What is needed |
|---|---|---|
| Drik Bala | Now computed in `shadbala.py` as `drik` from kb/shadbala_rules.json (Sphuta Drishti with special-aspect additions, benefic minus malefic over four, plus the full drishti of Mercury and Jupiter) but NOT added to the total. The earlier attempt matched AstroSage for Mars and the Moon only | AstroSage's Drik values for the reference chart (the PDF is not in the project folder) to test against before it joins the total |
| Cheshta Bala | Needs mean and true planetary longitudes (seeghrochcha / cheshta-kendra) | The exact formula and the mean-longitude constants; or the accepted motion-based table |
| Abda Bala and Masa Bala | Year lord and month lord need the traditional calendar (ahargana) count; the Mesha-sankranti weekday did not match AstroSage | The exact rule for the lord of the year and of the month |
| Yuddha Bala | Planetary war adjustment | The exact adjustment rule |
| Saptavargaja Bala | Matches AstroSage for Sun, Moon, Mars, Jupiter but differs for Mercury, Venus, Saturn (differences of -45, +15, +15 virupas) | Which friendship convention AstroSage uses in each varga, and how own-sign is scored in D3/D12/D30 |
| Hora Bala | AstroSage counts the hora from midnight; the classical count is from sunrise | Confirmation of the intended convention |
| Bhavabala (Bhavadhipati, Bhavadig, Bhavadrishti) | Only the ruler's Shadbala is easy; the direction and aspect parts are not known | The Bhava dig-bala rule (by sign type) and the Bhava drishti-bala formula |
| Drekkana Bala | Now follows BPHS 27.6 (male planets in the 1st decanate, female in the 2nd, Mercury and Saturn in the 3rd); the code had the 2nd and 3rd swapped. AstroSage shows 1 for every planet and does not add it | Confirmation of whether it should be included |

## Varshaphal (yearly chart) - `engine/varshaphal.py`
Implemented and matching AstroSage for 2026: return moment (within 31 s), rising sign, Muntha, all Mudda periods.
Added in v2.4.0 (`engine/tajika.py`, `kb/tajika_rules.json`): **Tajika aspects by sign**, Ithasala (Poorna, Vartamana, Bhavishyat) and Ishrafa by degree within half the sum of the orbs, the **sixteen Tajika yogas** judged between the year's ascendant lord and each house lord, **Pancha-vargiya bala** (checked cell by cell against a published Prokerala report for two years), the **five office-bearers and the year lord (Varshesh)**, and **26 Sahams** (only those where Hayanaratna/Neelakanthi and Raman agree; the children, death, illness, imprisonment and adultery Sahams are left out). Still open: the Hadda table differs between texts for Aquarius (Raman's order is used); the Moon-as-Varshesh rule and Saham verdict wording are simplified; Tajika yogas with retrograde slower planets are not special-cased. The Mudda-dasha starting rule (birth Moon nakshatra + completed years) was inferred from one year and should be confirmed with a second reference year.

## KP system - `engine/kp.py`
Matches AstroSage for all 12 cusp sign/star/sub lords. KP-new ayanamsa is modelled as Lahiri minus 5'24" (matches to 2"); confirm the exact definition. Cusp degrees differ by about 1-2' from AstroSage because AstroSage rounds the birth longitude to whole arc-minutes; planet sub lords can differ when a position is within an arc-minute of a boundary. Added in v2.4.0 (`engine/kp_judgement.py`, `kb/kp_house_groups.json`): what each **cusp sub lord** says, judged through its star lord (main level) and itself (weaker level) against 22 KP house groups (from the KP Readers as compiled in the AstroSage KP house-grouping table), with the 12th-from rule for opposing houses and retrograde delay; and **KP horary 1-249** (the table is computed from the sub divisions, 249 rows with the six sign-boundary splits at 22/23, 62/63, 105/106, 145/146, 188/189, 228/229, matching published tables; the ascendant is set at the start of the sub and the other cusps are Placidus for the moment of judgement). Still open: Rahu/Ketu as agents use only the sign lord (not conjunctions or aspects), and only one main cusp is judged per matter.

## Dashas and Jaimini - `engine/more_dashas.py`
Char Dasha, Yogini dates (within 2-3 days) and karakas match. Missing or unconfirmed: the **dual-lord rule** for Scorpio and Aquarius (the rule used reproduces AstroSage for this chart only), the Char dasha **second cycle**, **Yogini/Char antardasha** rules for a second reference chart, **Swamsa** (kept as the same chart as Karakamsa) and **Avastha** tables.

## Other AstroSage sections not built
**Lal Kitab** - added in v2.4.0 as a separate module (`engine/lal_kitab.py`, `kb/lal_kitab.json`): the fixed-house chart, pakka ghar / exalted / debilitated / good / weak houses (kept only where two references agree), planet-in-house readings built from those facts, the nine debts (rin) with shared family remedies, the **35-year cycle** (Saturn 6, Rahu 6, Ketu 3, Jupiter 6, Sun 2, Moon 1, Venus 3, Mars 6, Mercury 2) and **Lal Kitab Varshphal** from the 120-year table (two independent copies agree on all 120 rows). Still open: Rahu/Ketu exaltation houses differ between texts; sleeping planets and houses, Lal Kitab aspects and the long per-house Lal Kitab prose are not built. **Prastharashtakvarga** is built, and v2.4.0 adds **Trikona and Ekadhipatya Shodhana**, **Shodhya Pinda** and **Kakshya** (`engine/ashtakvarga_reductions.py`, checked against a published worked example). **Ascendant / nakshatra / character prose** is original text at a shorter length than AstroSage's pages; more depth needs more source material.

## Conventions that differ from AstroSage (not errors, but worth knowing)
Rahu/Ketu aspect only the 7th here (AstroSage: 5th, 7th, 9th). Moon-Mars natural friendship: neutral here, friendly there. Vimshottari dates use 365.25-day years (AstroSage dates differ by 3-4 days). Paya is not computed. Gochara: Rahu's favourable transit houses now follow kb/gochara_vedha.json (3rd, 6th, 11th from the Moon); the older code also counted the 10th. Vedha is applied, with the fast Moon ignored as an obstructer in the monthly outlook. The Moon in D7 differs (D7 is not shown in this app).

## Remedies - `engine/remedy_plan.py`
Built on the remedy knowledge base already in the app plus these rules: a planet is considered only when it is weak/troubled AND active now (running Mahadasha/Antardasha, or Saturn during Sade Sati/Dhaiya); a gemstone only for a planet that rules a trine house and no difficult house. Originally missing: **gemstone weight and metal rules by planet and by person**, the **classical list of functional benefics and malefics per ascendant**, and **transit-based** (Gochara) triggers. The last two were added in Nov 2026 (see below).

**Nov 2026:** the functional benefic/malefic list per ascendant is now read from `kb/functional_nature.json` (BPHS ch.34): a functional malefic never gets a gemstone, a functional benefic or yogakaraka may even if it also rules the 8th or 12th, and planets BPHS leaves unlabelled keep the house-lordship rule. Transit triggers are now in: Jupiter counts as active while it transits a difficult house from the Moon (Gochara with Vedha, `kb/gochara_vedha.json`). Rahu and Ketu are left out of that trigger because one of them is nearly always in a difficult house. Still missing: gemstone weight and metal rules (no classical rule exists, see kb/gemstones.json).

## Languages - `engine/i18n.py`
Bengali step 1 is built (interface and app-composed text). **Not translated yet**: the classical knowledge-base paragraphs (`engine/kb/*.json`
and the text `engine/rule_engine.py` composes around them, about 155,000 words), the PDF report, and the Hindi language. These need a full
translation with a native proofreader. Bengali numerals are not used (digits stay 0-9, except ordinals such as ১ম).

## Languages (v2.0.0)
Bengali is complete on screen (interface, knowledge base, composed text). Not yet: Bengali PDF report; Hindi (same route via `i18n_src/hi.py`). A few names/terms intentionally stay English (person names, FAQ, PDF, yoga ids like YOGA-24, the credit line). Open question for the owner: Bengali digits vs Latin digits for dates/years.

## Compact (free) edition - `engine/edition.py` (v2.1.0)
Not a content gap so much as unfinished packaging: there's a "lite" edition now (see README_ANDROID.md's 2.1.0 section) but no Premium edition to sell yet - `EDITION` only distinguishes "full" and "lite". Still open: which price/store listing Premium becomes (a paid upgrade of the same lite app vs. a separate purchase - affects whether "full" stays a third build or lite gains an in-app unlock), a distinct app icon for Compact (currently shares `icon.png` with the full app), and whether the free edition should tease the locked features (Home's subtitle mentions them in text only; no lock icons on cards) to drive Premium conversions.
