"""make_learn_kb.py - writes engine/kb/learn.json: the Learn Astrology lessons and glossary.

Original teaching text (Parashari basics as in BPHS and Phaladeepika, written plainly). The v1.2 content policy applies. Run from android_app/: python tools/make_learn_kb.py
"""
import json
import os

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "engine", "kb", "learn.json")

LESSONS = [
    {"id": "what", "title": "What Vedic astrology is", "try": None, "sections": [
        ["A map of the sky", "A birth chart (kundli) is a map of where the Sun, the Moon and the planets were, seen from your "
         "birthplace, at the moment you were born. Vedic astrology (Jyotish) reads that map to describe tendencies in "
         "character and the timing of life's chapters."],
        ["The sidereal zodiac", "Vedic astrology measures the zodiac against the fixed stars (the sidereal zodiac). Western "
         "astrology uses the seasons instead, so the two differ by about 24 degrees today; that is why your Vedic Sun sign is "
         "often one sign earlier than your Western one. The difference is called the ayanamsa; this app uses the Lahiri "
         "ayanamsa, the standard in India."],
        ["Parashari astrology", "The main school, used throughout this app, comes from the Brihat Parashara Hora Shastra "
         "(BPHS). Other systems in the app, such as KP, Tajika and Lal Kitab, are labelled separately."],
        ["Tendencies, not fate", "A chart shows inclinations and favourable or testing periods. Your choices, effort and "
         "circumstances shape how they play out. Read the chart as a weather forecast, not a verdict."],
    ]},
    {"id": "signs", "title": "The 12 signs (Rashis)", "try": "lagna", "sections": [
        ["Twelve parts of the sky", "The zodiac is a circle of 360 degrees split into twelve signs of 30 degrees each, from "
         "Aries (Mesha) to Pisces (Meena). A sign is the 'flavour' of a placement: how a planet expresses itself."],
        ["Element", "Each sign belongs to an element. Fire (Aries, Leo, Sagittarius): energy and initiative. Earth (Taurus, "
         "Virgo, Capricorn): practicality and stability. Air (Gemini, Libra, Aquarius): thought and connection. Water (Cancer, "
         "Scorpio, Pisces): feeling and sensitivity."],
        ["Quality", "Movable signs (Aries, Cancer, Libra, Capricorn) start things; fixed signs (Taurus, Leo, Scorpio, "
         "Aquarius) hold steady; dual signs (Gemini, Virgo, Sagittarius, Pisces) adapt."],
        ["Ruler", "Every sign has a ruling planet: Mars rules Aries and Scorpio; Venus rules Taurus and Libra; Mercury rules "
         "Gemini and Virgo; the Moon rules Cancer; the Sun rules Leo; Jupiter rules Sagittarius and Pisces; Saturn rules "
         "Capricorn and Aquarius. The ruler of a sign is called its lord."],
    ]},
    {"id": "planets", "title": "The 9 planets (Grahas)", "try": "sun_moon", "sections": [
        ["Nine grahas", "Vedic astrology uses seven visible planets (the Sun, Moon, Mars, Mercury, Jupiter, Venus and "
         "Saturn) and the two lunar nodes, Rahu and Ketu, the points where the Moon's path crosses the Sun's. Uranus, Neptune "
         "and Pluto are not used."],
        ["What each one stands for", "The Sun: self, vitality, authority, father. The Moon: mind, feelings, mother, comfort. "
         "Mars: energy, courage, siblings, property. Mercury: intellect, speech, trade. Jupiter: wisdom, teachers, faith, "
         "growth. Venus: love, beauty, comfort, partnership. Saturn: discipline, work, patience, delay. Rahu: ambition, the "
         "unusual and the foreign. Ketu: detachment, insight, letting go."],
        ["Natural benefics and malefics", "Jupiter, Venus, a well-placed Mercury and a bright (waxing) Moon are natural "
         "benefics: they tend to give easily. The Sun, Mars, Saturn, Rahu and Ketu are natural malefics: they tend to test "
         "and push. A 'malefic' is not bad; it gives through effort."],
        ["The Moon and the Ascendant", "The rising sign shows the body and the way you meet life; the Moon shows the mind. "
         "That is why Vedic astrology often reads the chart from both."],
    ]},
    {"id": "houses", "title": "The 12 houses (Bhavas)", "try": "houses", "sections": [
        ["Twelve areas of life", "The rising sign (Lagna) becomes the 1st house, the next sign the 2nd, and so on. Each house "
         "is an area of life: 1 self and body; 2 money, family, speech; 3 courage, effort, siblings, short journeys; 4 home, "
         "mother, comfort, property; 5 learning, creativity, romance; 6 work, service, rivals, health habits; 7 marriage and "
         "partners; 8 sudden changes, research, shared money; 9 luck, father, teachers, faith; 10 career and status; 11 gains, "
         "income, friends; 12 expenses, rest, foreign lands, letting go."],
        ["House groups", "Kendras (1, 4, 7, 10) are the pillars: planets there act strongly. Trikonas (1, 5, 9) are the "
         "houses of fortune. Dusthanas (6, 8, 12) are the testing houses. Upachayas (3, 6, 10, 11) are houses of growth, "
         "where even difficult planets improve with time."],
        ["Empty houses", "An empty house is not a bad house. It is judged by its lord: where that planet sits and how strong "
         "it is."],
    ]},
    {"id": "lords", "title": "House lords: how areas connect", "try": "lords", "sections": [
        ["Every house has a lord", "The lord of a house is the ruler of the sign on that house. If Gemini is on your 10th "
         "house, Mercury is your 10th lord."],
        ["Where the lord goes, the house goes", "A lord carries its house's matters to the house it sits in. A 10th lord "
         "(career) in the 7th house (partners) often links work with partnership or the public. This one idea, linking two "
         "houses through their lord, explains much of a chart."],
        ["Good and difficult lordships", "Lords of trikonas (1, 5, 9) are helpful for any rising sign; lords of dusthanas "
         "(6, 8, 12) bring their tests wherever they go. A planet that rules both a kendra and a trikona is a Yogakaraka, "
         "an especially helpful planet for that rising sign."],
    ]},
    {"id": "dignity", "title": "Strength and dignity", "try": "dignity", "sections": [
        ["Exaltation and debilitation", "Each planet has a sign where it is strongest (exalted) and the opposite sign where "
         "it is weakest (debilitated). The Sun is exalted in Aries, the Moon in Taurus, Mars in Capricorn, Mercury in Virgo, "
         "Jupiter in Cancer, Venus in Pisces and Saturn in Libra."],
        ["Own sign and friends", "A planet in its own sign is comfortable and reliable. In a friend's sign it is at ease; in "
         "an enemy's sign it works harder."],
        ["Retrograde and combust", "A retrograde planet appears to move backwards; its results tend to come through review, "
         "repetition or an inward route. A planet very close to the Sun is combust: its light is hidden, so it can feel "
         "weaker or less visible."],
        ["Cancellation", "A debilitated planet can recover (Neecha Bhanga) when, for example, the lord of its sign sits in a "
         "kendra. Weakness in one place is rarely the whole story."],
    ]},
    {"id": "aspects", "title": "Aspects (Drishti)", "try": "aspects", "sections": [
        ["Planets look at houses", "In Vedic astrology every planet aspects (looks at) the 7th house from itself. Mars "
         "also aspects the 4th and 8th, Jupiter the 5th and 9th, and Saturn the 3rd and 10th."],
        ["Why it matters", "An aspect brings the planet's nature to that house. Jupiter's aspect protects and expands; "
         "Saturn's slows and makes you work for it; Mars's adds energy and heat."],
        ["Rahu and Ketu", "Texts differ on the nodes' aspects. This app counts only their 7th-house aspect; some astrologers "
         "also give them the 5th and 9th."],
    ]},
    {"id": "nakshatras", "title": "Nakshatras: the lunar mansions", "try": "moon", "sections": [
        ["27 star groups", "The zodiac is also divided into 27 nakshatras of 13 degrees 20 minutes each, starting with "
         "Ashwini. Each has a ruling planet, a deity and a character, and is split into four quarters (padas)."],
        ["Your birth star", "The nakshatra of your Moon is your birth star (janma nakshatra). It colours the mind and the "
         "emotional nature, and it is used to match charts for marriage."],
        ["The key to timing", "The ruler of your Moon's nakshatra decides the first period of the Vimshottari dasha you were "
         "born into, and how much of it was left at birth."],
    ]},
    {"id": "yogas", "title": "Yogas: special combinations", "try": "yogas", "sections": [
        ["What a yoga is", "A yoga is a specific combination of planets, signs or house lords that classical texts link "
         "to a particular result."],
        ["Some well-known yogas", "Gajakesari: Jupiter in a kendra from the Moon (respect, good sense). Raja Yoga: lords of "
         "a kendra and a trikona connected (rise in status). Pancha Mahapurusha: Mars, Mercury, Jupiter, Venus or Saturn in "
         "its own or exaltation sign in a kendra from the Lagna (a strong, distinctive personality)."],
        ["A yoga needs strength", "A yoga works fully only when the planets forming it are strong and unafflicted, and it "
         "shows most in their periods. Many charts have several yogas; their presence alone is not a promise."],
    ]},
    {"id": "dashas", "title": "Dashas: the timing of life", "try": "dasha", "sections": [
        ["Planetary periods", "The Vimshottari dasha divides a 120-year cycle among the nine planets: Ketu 7 years, Venus "
         "20, the Sun 6, the Moon 10, Mars 7, Rahu 18, Jupiter 16, Saturn 19 and Mercury 17, always in that order."],
        ["Main and sub-periods", "Each main period (Mahadasha) is divided into sub-periods (Antardashas) of all nine "
         "planets in the same order. The main period sets the background; the sub-period sets the current focus."],
        ["How to read a period", "A period brings out what its planet promises in your chart: the houses it rules, the house "
         "it sits in, its strength and the yogas it joins. A well-placed planet's period tends to go smoothly; a troubled "
         "one's asks for more care."],
    ]},
    {"id": "transits", "title": "Transits (Gochara)", "try": "transits", "sections": [
        ["Planets on the move", "Transits are where the planets are now, compared with your birth chart. In Vedic astrology "
         "they are mainly read from your Moon sign."],
        ["Slow planets matter most", "Saturn spends about two and a half years in a sign, Jupiter about a year, and Rahu and "
         "Ketu about eighteen months, so their transits mark longer phases. The Moon moves through a sign in about two and a "
         "half days."],
        ["Sade Sati", "Sade Sati is the roughly seven and a half years when Saturn passes through the sign before your Moon, "
         "your Moon sign and the sign after. It is a period of responsibility and maturing, not a disaster."],
        ["Dasha first", "Transits trigger what the dashas promise. A good transit in a difficult period helps a little; a "
         "testing transit in a good period is usually mild."],
    ]},
    {"id": "vargas", "title": "Divisional charts (Vargas)", "try": "navamsa", "sections": [
        ["Charts within the chart", "Each sign can be divided into smaller parts to make divisional charts that focus on "
         "one area of life. The birth chart is D1."],
        ["The Navamsa (D9)", "The Navamsa divides each sign into nine parts. It is the most important divisional chart: it "
         "shows the inner strength of each planet and is read for marriage and the second half of life. A planet strong in "
         "both D1 and D9 is reliable."],
        ["Vargottama", "A planet in the same sign in D1 and D9 is vargottama, which classical texts count as a source of "
         "strength."],
        ["Other vargas", "D10 (Dashamsa) is read for career, D2 for wealth, D4 for property and D12 for parents."],
    ]},
    {"id": "method", "title": "How to read a chart, step by step", "try": None, "sections": [
        ["1. Start with the rising sign", "Note the Lagna, its lord, and where that lord sits: this is the core of the "
         "person and the direction of life."],
        ["2. Read the Moon", "Note the Moon's sign, house and nakshatra: this is the mind and emotional life."],
        ["3. Scan the houses", "See which houses hold planets and which lords sit where. Pay most attention to the 1st, "
         "10th, 7th and 4th houses."],
        ["4. Judge strength", "Check each planet's dignity, retrogression, combustion and the aspects it receives. Strong "
         "planets deliver; weak ones need support."],
        ["5. Find the yogas", "Look for combinations, then check whether the planets forming them are strong."],
        ["6. Time it", "Read the running Mahadasha and Antardasha, then the transits of Saturn and Jupiter from the Moon."],
        ["7. Confirm with the Navamsa", "See whether the D9 supports or weakens what the birth chart shows."],
        ["8. Put it together", "Look for themes that repeat in several places. A single factor is a hint; three factors "
         "pointing the same way are a pattern."],
    ]},
    {"id": "wisely", "title": "Using astrology wisely", "try": None, "sections": [
        ["A tool for understanding", "Astrology is best used to understand yourself and to choose good timing, not to "
         "live in fear. Difficult placements describe where you grow through effort."],
        ["What this app does not do", "Some topics are left out on purpose: the app makes no predictions about the length "
         "of life or about pregnancy and births."],
        ["Remedies", "Mantras, charity, fasting and practices are traditional supports, never a substitute for medical, "
         "legal or financial advice."],
    ]},
]

GLOSSARY = [
    ["Lagna", "The rising sign at birth, which becomes the 1st house; also called the Ascendant.", "houses"],
    ["Rashi", "A sign of the zodiac (30 degrees). Also used for the birth chart itself (Rashi chart, D1).", "signs"],
    ["Graha", "A planet. Vedic astrology uses nine: the Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu and Ketu.", "planets"],
    ["Bhava", "A house of the chart: one of the twelve areas of life.", "houses"],
    ["Kundli", "The birth chart: the positions of the planets in the signs and houses at birth.", "what"],
    ["Ayanamsa", "The difference between the sidereal (star-based) and tropical (season-based) zodiacs; about 24 degrees today.", "what"],
    ["Sidereal zodiac", "The zodiac measured against the fixed stars, used in Vedic astrology.", "what"],
    ["Nakshatra", "One of the 27 lunar mansions of 13 degrees 20 minutes each.", "nakshatras"],
    ["Pada", "A quarter of a nakshatra (3 degrees 20 minutes).", "nakshatras"],
    ["Janma nakshatra", "The birth star: the nakshatra the Moon occupied at birth.", "nakshatras"],
    ["Dasha", "A planetary period that times the events of life.", "dashas"],
    ["Mahadasha", "A main planetary period (for example Saturn's 19 years in the Vimshottari system).", "dashas"],
    ["Antardasha", "A sub-period within a Mahadasha.", "dashas"],
    ["Vimshottari", "The 120-year dasha system based on the Moon's nakshatra; the main timing system of Parashari astrology.", "dashas"],
    ["Gochara", "Transits: the current movement of the planets, read mainly from the Moon sign.", "transits"],
    ["Sade Sati", "About seven and a half years when Saturn passes the 12th, 1st and 2nd signs from the natal Moon.", "transits"],
    ["Drishti", "Aspect: a planet's influence on the houses it looks at.", "aspects"],
    ["Kendra", "The angular houses 1, 4, 7 and 10; the pillars of the chart.", "houses"],
    ["Trikona", "The trine houses 1, 5 and 9; the houses of fortune.", "houses"],
    ["Dusthana", "The testing houses 6, 8 and 12.", "houses"],
    ["Upachaya", "The growth houses 3, 6, 10 and 11, where difficult planets improve with time.", "houses"],
    ["Uchcha", "Exaltation: the sign where a planet is strongest.", "dignity"],
    ["Neecha", "Debilitation: the sign where a planet is weakest, opposite its exaltation sign.", "dignity"],
    ["Neecha Bhanga", "Cancellation of debilitation by supporting factors.", "dignity"],
    ["Moolatrikona", "A sign, close to its own sign, where a planet works especially well.", "dignity"],
    ["Swakshetra", "A planet in its own sign.", "dignity"],
    ["Vakri", "Retrograde: a planet that appears to move backwards.", "dignity"],
    ["Asta", "Combust: a planet too close to the Sun, whose light is hidden.", "dignity"],
    ["Yoga", "A combination of planets, signs or lords linked to a particular result.", "yogas"],
    ["Raja Yoga", "A combination of kendra and trikona lords, linked to rise in status.", "yogas"],
    ["Dhana Yoga", "A combination of the lords of wealth houses (2, 5, 9, 11), linked to income.", "yogas"],
    ["Gajakesari Yoga", "Jupiter in a kendra from the Moon; linked to respect and sound judgement.", "yogas"],
    ["Pancha Mahapurusha", "Five yogas formed by Mars, Mercury, Jupiter, Venus or Saturn strong in a kendra.", "yogas"],
    ["Yogakaraka", "A planet that rules both a kendra and a trikona for a given rising sign; especially helpful.", "lords"],
    ["Bhavesh", "The lord of a house.", "lords"],
    ["Varga", "A divisional chart, made by dividing each sign into parts.", "vargas"],
    ["Navamsa", "The ninth-division chart (D9), the most important varga.", "vargas"],
    ["Dashamsa", "The tenth-division chart (D10), read for career.", "vargas"],
    ["Vargottama", "A planet in the same sign in D1 and D9; a mark of strength.", "vargas"],
    ["Rahu", "The Moon's north node; ambition, the unusual and the foreign.", "planets"],
    ["Ketu", "The Moon's south node; detachment, insight and letting go.", "planets"],
    ["Shubha graha", "A natural benefic planet: Jupiter, Venus, a well-placed Mercury and a waxing Moon.", "planets"],
    ["Papa graha", "A natural malefic planet: the Sun, Mars, Saturn, Rahu and Ketu.", "planets"],
    ["Paksha", "The Moon's phase: Shukla (waxing) or Krishna (waning).", "planets"],
    ["Tithi", "A lunar day: each 12 degrees of separation between the Moon and the Sun.", "nakshatras"],
    ["Panchanga", "The five parts of the Hindu calendar: tithi, weekday, nakshatra, yoga and karana.", "nakshatras"],
    ["Ashtakavarga", "A point system (0-8 per sign) showing how supportive each sign is for each planet.", "transits"],
    ["Shadbala", "The six-fold strength of a planet in classical astrology.", "dignity"],
    ["Karaka", "The natural significator of something: Venus for marriage, the Sun for the father, Jupiter for wisdom.", "planets"],
    ["Muhurta", "Choosing an auspicious moment to start something.", "transits"],
    ["Manglik", "Mars in certain houses from the Lagna (Kuja Dosha), checked when matching charts for marriage.", "yogas"],
    ["Parivartana", "Exchange of signs: two planets each in the other's sign, which links their houses strongly.", "lords"],
    ["Varshaphal", "The yearly chart cast for the Sun's return to its birth position (Tajika system).", "what"],
    ["KP", "Krishnamurti Paddhati: a modern system based on star lords and sub lords of the house cusps.", "what"],
    ["Lal Kitab", "A system with fixed houses and practical remedies, separate from Parashari astrology.", "what"],
]

data = {
    "schema_version": "1.0",
    "system": "Learn Astrology - teaching text for the Parashari basics used in this app",
    "sources": ["Brihat Parashara Hora Shastra (signs, planets, houses, lordships, aspects, dignity, Vimshottari)",
                "Phaladeepika (yogas, dignity, transits)", "Original explanatory text written for this app"],
    "policy": "The v1.2 content policy applies, as everywhere in the app.",
    "lessons": LESSONS,
    "glossary": [{"term": t, "meaning": m, "lesson": l} for t, m, l in GLOSSARY],
}
ids = {l["id"] for l in LESSONS}
assert all(g["lesson"] in ids for g in data["glossary"])
with open(OUT, "w", encoding="utf-8") as fh:
    json.dump(data, fh, indent=2, ensure_ascii=False)
    fh.write("\n")
print("wrote", OUT, len(LESSONS), "lessons,", len(GLOSSARY), "terms")
