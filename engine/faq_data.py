"""
faq_data.py — offline "Help & FAQ" content shown in every version of this
app (desktop, web, Android). There's no AI and no internet access here, so
this can't be a chatbot that answers open-ended questions - instead it's a
curated, searchable list of the questions people actually ask the first
time they open a Vedic chart report, grouped by topic and written in plain
language. Every surface (webapp/server.py's /api/faq, gui_app.py's Help &
FAQ tab, android_app's tabs_help.py) reads from FAQ_CATEGORIES below, so
the content only has to be written once.

Structure: FAQ_CATEGORIES is a list of categories, in display order. Each
category is a dict with a short id, an icon (a single emoji - renders
fine on desktop/web/Android with zero image assets), a title, and its own
list of (question, answer) pairs. A category with an empty "items" list
is simply skipped by every renderer, so it's safe to leave one half-filled.
"""

FAQ_CATEGORIES = [
    {
        "id": "basics",
        "icon": "✨",  # ✨
        "title": "Getting Started",
        "items": [
            ("What do I actually need to enter for an accurate chart?",
             "Your birth date, birth TIME (as exact as possible - even 15 "
             "minutes off can shift the Ascendant and house placements), "
             "and birth place. Time is the single biggest source of error - "
             "check a birth certificate or hospital record if you have one."),
            ("Why does the app ask for a country hint along with the city?",
             "Many city names repeat around the world (there are Londons in "
             "the UK, Canada, and the US). The country hint tells the "
             "offline place lookup which one you mean - especially useful "
             "for expat families searching for a city outside India."),
            ("I don't know the exact birth time. What should I do?",
             "Use the closest estimate you have (a birth certificate, "
             "hospital paperwork, or a family member's memory). The chart "
             "still computes, but treat Ascendant-dependent results (house "
             "placements, some yogas) as approximate rather than exact."),
            ("What does 'sidereal' / Lahiri ayanamsa mean?",
             "Vedic astrology measures planets against the fixed stars "
             "(the sidereal zodiac), not the seasons (the tropical zodiac "
             "used in Western astrology). Lahiri is the most widely used "
             "sidereal reference point in Indian astrology, and it's what "
             "this app uses throughout."),
        ],
    },
    {
        "id": "chart",
        "icon": "\U0001F4D0",  # 📐
        "title": "Reading Your Chart",
        "items": [
            ("What's the difference between North Indian and South Indian chart styles?",
             "Same information, two traditional drawing conventions. North "
             "Indian charts keep the Ascendant fixed in a diamond shape and "
             "the signs rotate around it; South Indian charts keep the "
             "signs fixed in a grid and the planets move between boxes. "
             "Pick whichever you're used to reading - the maths behind "
             "both is identical."),
            ("What is a Varga / divisional chart (D9, D10...)?",
             "Traditional Vedic astrology doesn't stop at the main birth "
             "chart (D1) - it re-divides each sign into smaller slices for "
             "specific life areas: D9 (Navamsa) for marriage and inner "
             "strength, D10 (Dashamsha) for career, and so on. They refine "
             "the D1 picture rather than replace it."),
            ("What is a Yoga?",
             "A Yoga is a specific, named combination of planets and "
             "houses that classical texts treat as significant - some "
             "favourable, some challenging. Think of it as a recognisable "
             "'pattern' astrologers look for, similar to a doctor looking "
             "for a specific cluster of symptoms."),
            ("What is Dasha / Antardasha?",
             "The Vimshottari Dasha is a traditional timeline that assigns "
             "different life periods to different planets (a Mahadasha, "
             "further divided into Antardasha sub-periods). It's the "
             "system's main tool for timing WHEN a theme is more active, "
             "not just whether it exists in the chart at all."),
        ],
    },
    {
        "id": "predictions",
        "icon": "\U0001F52E",  # 🔮
        "title": "Predictions & Karmic Section",
        "items": [
            ("How literally should I take the Karmic & Past Life section?",
             "As a symbolic, reflective lens - Rahu/Ketu placements are a "
             "traditional way to talk about old patterns (Ketu) versus the "
             "direction you're being pulled to grow (Rahu), not a literal "
             "historical record. Many people still find it useful for "
             "self-reflection."),
            ("The Longevity section gives an age/year - is that a guarantee?",
             "No. Ayurdaya (longevity estimation) is one of the oldest and "
             "most debated branches of traditional astrology. Treat the "
             "age/year and 'vulnerable period' output as a traditional "
             "estimate to be aware of, never as a prediction to act on - "
             "and always prioritise real medical advice over this."),
            ("What's the difference between 'Concise' and 'Detailed' report mode?",
             "Concise keeps the short 'in simple terms' summary for each "
             "section; Detailed adds the full traditional reasoning "
             "underneath it. Same underlying analysis either way - Concise "
             "is just the same conclusions with less reading."),
            ("What do the Weekly & Monthly predictions use, if not AI?",
             "Classical Gochara (transit) astrology: where the real planets "
             "are positioned RIGHT NOW relative to your birth Moon, plus "
             "your currently running Dasha period. It's fully offline and "
             "recalculated instantly using the same ephemeris as your "
             "birth chart - just applied to today's date instead of your "
             "birth date."),
        ],
    },
    {
        "id": "family",
        "icon": "\U0001F46A",  # 👪
        "title": "Family & Compatibility",
        "items": [
            ("What is Ashtakoot Guna Milan?",
             "A traditional 36-point compatibility scoring system compared "
             "between two birth charts (classically for marriage matching), "
             "covering 8 separate factors: Varna, Vashya, Tara, Yoni, Graha "
             "Maitri, Gana, Bhakoot, and Nadi."),
            ("Can I generate charts for my children too?",
             "Yes - use the Profile switcher to add a Life Partner and up "
             "to four Child profiles, each with its own independent birth "
             "details and full reading. The 'Example family' quick-fill "
             "button can populate and generate sample charts for everyone "
             "at once, so you can see how it all looks before entering "
             "real data."),
            ("Is my birth data ever sent anywhere?",
             "No. Place lookup, chart maths, and every reading run "
             "entirely offline on your own device. Nothing is uploaded, "
             "and there's no internet connection involved at any point."),
        ],
    },
    # A spot for the questions YOUR OWN family/friends actually ask you
    # when you show them this app - you know these better than anyone
    # writing generic FAQ content ever could.
    {
        "id": "personal",
        "icon": "\U0001F4AC",  # 💬
        "title": "Questions I Get Asked",
        "items": [
            # TODO(human): add 2-5 of your own (question, answer) tuples here,
            # in the same shape as the categories above, e.g.:
            # ("Why did my Ascendant change when I fixed the birth time?",
            #  "..."),
        ],
    },
]


def search_faq(query):
    """Case-insensitive substring search across every question AND answer.
    Returns a flat list of (category, question, answer) tuples, category
    first so a matching UI can still group/label results by topic."""
    query = (query or "").strip().lower()
    if not query:
        return []
    results = []
    for cat in FAQ_CATEGORIES:
        for question, answer in cat["items"]:
            if query in question.lower() or query in answer.lower():
                results.append((cat, question, answer))
    return results
