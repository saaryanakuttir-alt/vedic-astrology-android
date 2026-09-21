"""life_profile.py - "Your nature": character, mind, career, education and leisure written in plain second-person
language from the rising sign, Moon sign and nakshatra, the 10th house, Mercury and Venus. Original wording; every
line is a tendency ("tends to", "may"), never a fixed fact. Nothing here touches lifespan or children.
"""
from astrology_tables import SIGN_LORD
from extras import _HOUSE_AREA, _TONE_PHRASE, ordinal, planet_considerations
from panchanga import SIGNS

RISING = {
    "Aries": "bold, direct and quick to act. You like to lead from the front, hate waiting around, and recover fast after a setback. Patience is the skill to grow",
    "Taurus": "steady, patient and practical. You value comfort, loyalty and things that last, and you work at your own reliable pace. Once you decide, you can be very stubborn",
    "Gemini": "curious, talkative and quick-witted. You pick things up fast, enjoy variety and people, and adapt easily. A restless mind is your challenge, so finishing what you start matters",
    "Cancer": "caring, protective and sensitive. Home, family and memories matter deeply to you, and you read moods well. You may hold on to hurts, so learning to let go helps",
    "Leo": "warm, proud and generous. You have natural presence, like to be appreciated and are loyal to your people. Guard against needing constant applause",
    "Virgo": "careful, modest and analytical. You notice details others miss and like being useful. Worry and self-criticism are the things to keep in check",
    "Libra": "charming, fair-minded and peace-loving. You value harmony, beauty and partnership, and see both sides of a question. Indecision is the thing to work on",
    "Scorpio": "intense, private and determined. You feel deeply, sense what is beneath the surface and do not give up easily. Learning to trust and forgive brings ease",
    "Sagittarius": "optimistic, honest and freedom-loving. You enjoy learning, travel and big ideas, and you say what you think. Tact and follow-through are the lessons",
    "Capricorn": "disciplined, ambitious and responsible. You build slowly and carefully, take duties seriously and get better with age. Remember to rest and enjoy the journey",
    "Aquarius": "independent, original and friendly in a detached way. You like ideas, groups and causes, and think differently from the crowd. Close emotional warmth may need conscious effort",
    "Pisces": "gentle, imaginative and compassionate. You are intuitive, absorb the moods around you and are drawn to art or spirituality. Boundaries and practical planning protect you",
}
MOON = {
    "Aries": "Your mind is quick and fiery: you react fast, feel strongly and calm down soon after. Action clears your head.",
    "Taurus": "Your mind is calm and steady and needs comfort and routine to feel secure. Change unsettles you at first but you adapt slowly.",
    "Gemini": "Your mind is busy and curious, always taking in something new. You process feelings by talking or writing them out.",
    "Cancer": "Your mind is deeply emotional and caring, tied to home and loved ones. Your mood follows the atmosphere around you.",
    "Leo": "Your mind is warm, proud and generous. You need to feel valued, and encouragement lifts you more than anything.",
    "Virgo": "Your mind is practical and detail-minded and likes to fix things. Worry can creep in, so calming routines help.",
    "Libra": "Your mind seeks balance and company. You feel best when relationships are peaceful and unsettled when they are not.",
    "Scorpio": "Your mind is intense and private, with strong feelings you keep well hidden. You remember deeply and heal by facing things honestly.",
    "Sagittarius": "Your mind is hopeful and restless for meaning. Freedom, learning and trust in the future keep your spirits up.",
    "Capricorn": "Your mind is serious and self-controlled. You hide vulnerability behind duty, and you feel better once you have a plan.",
    "Aquarius": "Your mind is independent and inventive and likes space. You handle feelings by stepping back and thinking them through.",
    "Pisces": "Your mind is dreamy, sensitive and very intuitive. You need quiet time to recharge, and kind surroundings matter a lot.",
}
CAREER = {
    "Aries": "work that involves initiative, leadership or competition - management, sport, engineering, defence, or starting your own venture",
    "Taurus": "steady work with something tangible - finance, farming, food, art, design, luxury goods or property",
    "Gemini": "communication and variety - writing, media, teaching, sales, technology, trade or anything involving information",
    "Cancer": "caring or public-facing work - healthcare, hospitality, education, real estate, food or working with families",
    "Leo": "roles with visibility and leadership - administration, government, performing arts, management or education",
    "Virgo": "detail and service - health, accounts, analysis, editing, research, quality control or technical work",
    "Libra": "partnership and design - law, diplomacy, fashion, art, counselling, public relations or business with partners",
    "Scorpio": "depth and investigation - research, medicine, psychology, finance, insurance, engineering or work in crisis and change",
    "Sagittarius": "teaching and horizons - education, law, publishing, travel, advice, philosophy or international work",
    "Capricorn": "structure and authority - administration, industry, construction, government or building a business step by step",
    "Aquarius": "ideas and networks - technology, science, social causes, innovation, aviation or group-based work",
    "Pisces": "creative or compassionate work - arts, healing, music, film, spiritual guidance, chemistry or work behind the scenes",
}
LEISURE = {
    "Aries": "sport, adventure, competitions and anything active and hands-on",
    "Taurus": "good food, gardening, music, art and comfortable home pleasures",
    "Gemini": "reading, conversation, puzzles, games, writing and short trips",
    "Cancer": "cooking, home projects, family time, nature and nostalgic hobbies",
    "Leo": "performing, creative projects, entertaining friends and celebrations",
    "Virgo": "crafts, gardening, health routines, reading and improving or organising things",
    "Libra": "art, music, fashion, socialising, movies and design",
    "Scorpio": "mysteries, research, deep films and books, swimming or intense sports",
    "Sagittarius": "travel, outdoor life, learning, spiritual reading and team sport",
    "Capricorn": "hiking, building or restoring things, history and long-term projects",
    "Aquarius": "technology, gadgets, community causes, science and unusual hobbies",
    "Pisces": "music, painting, poetry, dance, meditation and time near water",
}
LEARNING = {
    "Aries": "You learn best by doing, and you race ahead when a subject challenges you.",
    "Taurus": "You learn steadily and remember well, and you do best with practical, step-by-step material.",
    "Gemini": "You learn quickly through reading, talking and variety, though you may skim before you go deep.",
    "Cancer": "You learn best where you feel safe and supported, and you remember what touches you emotionally.",
    "Leo": "You learn best when you are encouraged and can present or lead what you know.",
    "Virgo": "You learn through careful analysis and notes, and you are usually thorough and accurate.",
    "Libra": "You learn well through discussion and in company, and you enjoy the arts and law-like reasoning.",
    "Scorpio": "You learn by digging deep and focusing intensely, and you enjoy research and hidden patterns.",
    "Sagittarius": "You enjoy big-picture subjects such as philosophy, law, languages and higher study.",
    "Capricorn": "You learn with discipline and long-term focus, and you do well in structured programmes.",
    "Aquarius": "You enjoy science, technology and original ideas, and you learn best your own way.",
    "Pisces": "You learn through imagination, stories and intuition, and you shine in creative or caring subjects.",
}
NAKSHATRA = [
    ("Ashwini", "quick, energetic and pioneering, with a healing touch"), ("Bharani", "intense, responsible and able to carry heavy loads"),
    ("Krittika", "sharp, honest and purifying, with a cutting wit"), ("Rohini", "charming, creative and fond of beauty and comfort"),
    ("Mrigashira", "curious, gentle and always searching"), ("Ardra", "stormy and emotional, with a deep urge to renew things"),
    ("Punarvasu", "hopeful, kind and good at starting over"), ("Pushya", "nurturing, wise and dependable"),
    ("Ashlesha", "perceptive, secretive and strategic"), ("Magha", "dignified, proud and drawn to tradition and status"),
    ("Purva Phalguni", "warm, playful and pleasure-loving"), ("Uttara Phalguni", "helpful, steady and good with commitments"),
    ("Hasta", "skilful with the hands, witty and resourceful"), ("Chitra", "artistic, stylish and eye-catching"),
    ("Swati", "independent, flexible and diplomatic"), ("Vishakha", "determined, goal-driven and persuasive"),
    ("Anuradha", "loyal, friendly and devoted"), ("Jyeshtha", "protective, capable and status-aware"),
    ("Mula", "probing and drawn to get to the root of things"), ("Purva Ashadha", "confident, enthusiastic and persuasive"),
    ("Uttara Ashadha", "principled, patient and a steady winner"), ("Shravana", "a good listener who learns by hearing"),
    ("Dhanishta", "rhythmic, ambitious and good with groups"), ("Shatabhisha", "private, independent and healing-minded"),
    ("Purva Bhadrapada", "intense, idealistic and unconventional"), ("Uttara Bhadrapada", "calm, deep and compassionate"),
    ("Revati", "gentle, caring and protective of the vulnerable"),
]
_SIGN_ADJ = {s: s for s in SIGNS}


def profile_sections(chart):
    """[(title, text)] - Character, Mind, Career, Education, Hobbies - built from this chart's own placements."""
    pl = chart["planets"]
    cons = planet_considerations(chart)
    rising = chart["ascendant"]["sign"]
    moon, sun = pl["Moon"], pl["Sun"]
    tenth = chart["houses"][10]
    tenth_lord = SIGN_LORD[tenth]
    tl = pl[tenth_lord]
    merc, venus = pl["Mercury"], pl["Venus"]
    nak = NAKSHATRA[int(moon["longitude"] // (360 / 27))]
    sections = []
    sections.append(("Your character", (
        f"With {rising} rising, you tend to be {RISING[rising]}. Your Sun is in {sun['sign']}, in your {ordinal(sun['house'])} house "
        f"({_HOUSE_AREA[sun['house']]}), so your sense of self is drawn toward {_HOUSE_AREA[sun['house']]}. Your Moon nakshatra, "
        f"{nak[0]}, adds a nature that is {nak[1]}.\n\n[In simple terms: the sign rising at your birth shows how people first see you; "
        f"the Sun shows what you want to stand for; the Moon nakshatra colours your inner temperament. None is fixed - you can grow past any of it.]")))
    sections.append(("Your mind and emotions", (
        f"{MOON[moon['sign']]} With the Moon in your {ordinal(moon['house'])} house, your feelings tend to be tied up with "
        f"{_HOUSE_AREA[moon['house']]}. The Moon {_TONE_PHRASE[cons['Moon']['tone']]} in your chart"
        f"{', so your mood tends to be fairly steady' if cons['Moon']['tone'] in ('Good', 'Mostly good') else ', so your mood may swing more than most at times' if cons['Moon']['tone'] == 'Mixed' else ', so looking after sleep and calm routines matters for you'}.")))
    sections.append(("Your career leanings", (
        f"Your 10th house of career is in {tenth}, which points toward {CAREER[tenth]}. Its ruler {tenth_lord} sits in {tl['sign']} in your "
        f"{ordinal(tl['house'])} house, so your working life tends to connect with {_HOUSE_AREA[tl['house']]}, and {tenth_lord} "
        f"{_TONE_PHRASE[cons[tenth_lord]['tone']]} in your chart - "
        f"{'a helpful sign for steady progress' if cons[tenth_lord]['tone'] in ('Good', 'Mostly good') else 'a mix of easy and effortful stretches' if cons[tenth_lord]['tone'] == 'Mixed' else 'a reminder that patience and steady skills matter more than shortcuts'}. "
        f"[In simple terms: these are the kinds of work that tend to suit your temperament; they are leanings, not rules.]")))
    sections.append(("Education and learning", (
        f"{LEARNING[merc['sign']]} Mercury, the planet of learning, is in {merc['sign']} in your {ordinal(merc['house'])} house and "
        f"{_TONE_PHRASE[cons['Mercury']['tone']]}, so studies tend to connect with {_HOUSE_AREA[merc['house']]}. "
        f"[In simple terms: this describes how you take in and use knowledge.]")))
    sections.append(("Hobbies and free time", (
        f"With Venus in {venus['sign']}, you are likely to enjoy {LEISURE[venus['sign']]}. Your Moon in {moon['sign']} adds a liking for "
        f"{LEISURE[moon['sign']]}. [In simple terms: these are the pastimes most likely to refresh you.]")))
    return sections


def profile_text(chart):
    return "\n\n".join(f"--- {title} ---\n{text}" for title, text in profile_sections(chart))
