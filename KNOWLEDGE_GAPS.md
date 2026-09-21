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
| Drik Bala | Tried the Parashara drishti-pinda table with special aspects; only Mars and Moon matched AstroSage (Sun, Mercury, Jupiter, Venus, Saturn did not) | The exact aspect-value table (including how Mars 4th/8th, Jupiter 5th/9th, Saturn 3rd/10th are added), the rule for Mercury and the Moon being benefic or malefic, and whether the sum is halved |
| Cheshta Bala | Needs mean and true planetary longitudes (seeghrochcha / cheshta-kendra) | The exact formula and the mean-longitude constants; or the accepted motion-based table |
| Abda Bala and Masa Bala | Year lord and month lord need the traditional calendar (ahargana) count; the Mesha-sankranti weekday did not match AstroSage | The exact rule for the lord of the year and of the month |
| Yuddha Bala | Planetary war adjustment | The exact adjustment rule |
| Saptavargaja Bala | Matches AstroSage for Sun, Moon, Mars, Jupiter but differs for Mercury, Venus, Saturn (differences of -45, +15, +15 virupas) | Which friendship convention AstroSage uses in each varga, and how own-sign is scored in D3/D12/D30 |
| Hora Bala | AstroSage counts the hora from midnight; the classical count is from sunrise | Confirmation of the intended convention |
| Bhavabala (Bhavadhipati, Bhavadig, Bhavadrishti) | Only the ruler's Shadbala is easy; the direction and aspect parts are not known | The Bhava dig-bala rule (by sign type) and the Bhava drishti-bala formula |
| Drekkana Bala | AstroSage shows 1 for every planet and does not add it | Confirmation of whether it should be included |

## Varshaphal (yearly chart) - `engine/varshaphal.py`
Implemented and matching AstroSage for 2026: return moment (within 31 s), rising sign, Muntha, all Mudda periods.
Missing: **year lord (Varshesh)** (needs the five officers and Pancha-vargiya bala), **Sahams** (formula list; only ones that are certain should be added, and the children- and death-related ones stay excluded), the other **Tajika yogas** (Nakta, Yamaya, Manahoo, Kambool, Radda, Duphali-kuttha ...), and **Tajika aspects by sign**. The Mudda-dasha starting rule (birth Moon nakshatra + completed years) was inferred from one year and should be confirmed with a second reference year.

## KP system - `engine/kp.py`
Matches AstroSage for all 12 cusp sign/star/sub lords. KP-new ayanamsa is modelled as Lahiri minus 5'24" (matches to 2"); confirm the exact definition. Cusp degrees differ by about 1-2' from AstroSage because AstroSage rounds the birth longitude to whole arc-minutes; planet sub lords can differ when a position is within an arc-minute of a boundary. Missing: KP **house-wise result interpretation** (which sub lord signifies what) and **horary 1-249** tables.

## Dashas and Jaimini - `engine/more_dashas.py`
Char Dasha, Yogini dates (within 2-3 days) and karakas match. Missing or unconfirmed: the **dual-lord rule** for Scorpio and Aquarius (the rule used reproduces AstroSage for this chart only), the Char dasha **second cycle**, **Yogini/Char antardasha** rules for a second reference chart, **Swamsa** (kept as the same chart as Karakamsa) and **Avastha** tables.

## Other AstroSage sections not built
**Lal Kitab** (chart rules, planet-in-house effects, debts, 36-year dasha, Varshphal) - not enough reliable knowledge to write it. **Prastharashtakvarga** is built; **Sarvashtakvarga reductions** (Trikona/Ekadhipatya Shodhana) and **Kakshya** are not. **Ascendant / nakshatra / character prose** is original text at a shorter length than AstroSage's pages; more depth needs more source material.

## Conventions that differ from AstroSage (not errors, but worth knowing)
Rahu/Ketu aspect only the 7th here (AstroSage: 5th, 7th, 9th). Moon-Mars natural friendship: neutral here, friendly there. Vimshottari dates use 365.25-day years (AstroSage dates differ by 3-4 days). Paya is not computed. The Moon in D7 differs (D7 is not shown in this app).

## Remedies - `engine/remedy_plan.py`
Built on the remedy knowledge base already in the app plus these rules: a planet is considered only when it is weak/troubled AND active now (running Mahadasha/Antardasha, or Saturn during Sade Sati/Dhaiya); a gemstone only for a planet that rules a trine house and no difficult house. Missing: **gemstone weight and metal rules by planet and by person**, the **classical list of functional benefics and malefics per ascendant** (currently derived from house lordship only), and **transit-based** (Gochara) triggers. These need a qualified source before the app should say more.

## Languages - `engine/i18n.py`
Bengali step 1 is built (interface and app-composed text). **Not translated yet**: the classical knowledge-base paragraphs (`engine/kb/*.json`
and the text `engine/rule_engine.py` composes around them, about 155,000 words), the PDF report, and the Hindi language. These need a full
translation with a native proofreader. Bengali numerals are not used (digits stay 0-9, except ordinals such as ১ম).
