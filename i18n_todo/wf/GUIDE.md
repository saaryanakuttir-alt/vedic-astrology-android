# Bengali translation guide (Vedic astrology app, offline, Android)

You translate English text of a Vedic (Jyotish) astrology app into natural, everyday Bengali (চলিত ভাষা, polite "আপনি").
The English is already written in plain words for ordinary readers - keep it that way. A Bengali reader will proofread.

## Your files (all under `i18n_todo/wf/`, project root = the `android_app` folder)
* Input  : `in_NNN.txt`   - one text per line: `id<TAB>English`. Lines starting with `#` are context only (which knowledge-base entry follows).
* Output : `out_NNN.txt`  - you WRITE this: exactly the same ids, one per line: `id<TAB>Bengali`. No `#` lines, no extra text, UTF-8.
* Check  : run `python tools/validate_wf.py NNN` from the project root and fix every problem it prints. Do not finish until it prints `OK`.
* Style samples already approved by the owner: `i18n_todo/bn_04.txt` (lines 297-360) and `i18n_todo/bn_08.txt` - read a few lines first.

## Rules
1. **One line in, one line out.** Same id, same order. Never merge, split, drop or add lines. Every id must appear exactly once.
2. **Newlines** appear as the two characters `\n` in the file. Keep exactly the same number of `\n` in each translation.
3. **Placeholders** such as `{0}`, `{1}`, `{2:.0f}`, `{0:%d %b %Y}`, `%s` must be kept exactly and all of them must appear (word order may change).
   The note after `##` in the input says what is slotted in (a planet, a sign, an ordinal like "5th", a whole sentence...). It is only a hint, do not copy it.
   Slotted words are translated separately, so put grammar around them that works for any planet/sign/number ("{0}-এর", "{0} ভাবে").
4. **Leading and trailing spaces do not matter** (they are restored automatically), but keep the sentence a fragment if the English is a fragment
   (ends with ":" or starts with lower case or "," - it is glued to other text by the program). Do not turn fragments into full sentences.
5. **Meaning first, natural Bengali second.** Do not translate word by word. Keep the same softness: "may/tends to/can" -> "হতে পারে / ঝোঁক থাকে". Never make a
   prediction stronger than the English. Keep warnings and disclaimers ("not a diagnosis", "not a guarantee") fully.
6. Full stop `.` at the end of a statement becomes `।`. Keep `?`, `!`, `:`, `;`, quotes '...' and the dash `—` / `-` as in the English.
7. "you/your" -> আপনি/আপনার. "the native / native's" -> জাতক / জাতকের. "person" -> ব্যক্তি.
8. **Numbers**: keep ordinary digits 0-9 as they are (36, 2026, 12deg -> 12 ডিগ্রি). Ordinals become Bengali-digit ordinals:
   1st ১ম, 2nd ২য়, 3rd ৩য়, 4th ৪র্থ, 5th ৫ম, 6th ৬ষ্ঠ, 7th ৭ম, 8th ৮ম, 9th ৯ম, 10th ১০ম, 11th ১১তম, 12th ১২তম. "house 7" -> "৭ নম্বর ভাব".
9. No English words may be left, except chart codes and abbreviations: D1 D9 D10..., KP, Rx, MC, PDF, and text inside placeholders. Write Sanskrit terms in Bengali script.
10. Consistency matters: the same English phrase must always get the same Bengali phrase (many lines are near-copies with a different planet or sign).
    Templated sentences ("Own sign — colors career ... through Taurus's stability.") must read as one family. Translate the recurring parts identically.

## Glossary (use these exactly)
Planets: Sun সূর্য, Moon চন্দ্র, Mars মঙ্গল, Mercury বুধ, Jupiter বৃহস্পতি, Venus শুক্র, Saturn শনি, Rahu রাহু, Ketu কেতু. Planet = গ্রহ.
Signs: Aries মেষ, Taurus বৃষ, Gemini মিথুন, Cancer কর্কট, Leo সিংহ, Virgo কন্যা, Libra তুলা, Scorpio বৃশ্চিক, Sagittarius ধনু, Capricorn মকর, Aquarius কুম্ভ, Pisces মীন. Sign = রাশি.
Chart কুণ্ডলী; birth chart জন্মকুণ্ডলী; divisional chart বিভাগীয় কুণ্ডলী; Ascendant / Lagna লগ্ন; house ভাব; degree ডিগ্রি; Rasi chart রাশি কুণ্ডলী; Navamsa নবাংশ.
Lord / ruler অধিপতি; exalted উচ্চস্থ; exaltation উচ্চরাশি; debilitated নীচস্থ; own sign স্বরাশি; moolatrikona মূলত্রিকোণ; friend's sign মিত্র রাশি; enemy's sign শত্রু রাশি;
neutral সম; great friend অধিমিত্র; great enemy অধিশত্রু; dignity মর্যাদা; strength বল.
Conjunct / conjunction যুক্ত / যুতি; aspect (a planet looking at a house) দৃষ্টি; opposition বিপরীত অবস্থান; trine ত্রিকোণ; square চতুষ্কোণ; sextile ষষ্ঠাংশ.
Benefic শুভগ্রহ; malefic পাপগ্রহ; kendra (angular house) কেন্দ্র; trikona ত্রিকোণ; dusthana (difficult house) দুঃস্থান; upachaya উপচয়; maraka মারক.
Dasha দশা; Mahadasha মহাদশা; Antardasha অন্তর্দশা; Pratyantardasha প্রত্যন্তর্দশা; Vimshottari বিংশোত্তরী; period কাল; sub-period উপকাল.
Yoga যোগ; dosha দোষ; Raja Yoga রাজযোগ; Dhana Yoga ধনযোগ; Kuja / Mangal Dosha মঙ্গল দোষ (মাঙ্গলিক); Kalsarpa কালসর্প; Pitra Dosha পিতৃ দোষ; Guru Chandal গুরু চণ্ডাল; Gaja Kesari গজকেশরী; Sade Sati সাড়েসাতি; Dhaiya ঢাইয়া.
Nakshatra নক্ষত্র; pada পাদ; Janma Nakshatra জন্মনক্ষত্র; Vargottama বর্গোত্তম; retrograde বক্রী; combust অস্ত; Muntha মুন্থা.
Atmakaraka আত্মকারক; Amatyakaraka অমাত্যকারক; Darakaraka দারকারক; Putrakaraka পুত্রকারক; Karakamsa কারকাংশ; karaka / significator কারক; Jaimini জৈমিনি.
Dharma ধর্ম; Karma কর্ম; Moksha মোক্ষ; Artha অর্থ; Kama কাম; past-life merit পূর্বপুণ্য; past life পূর্বজন্ম; soul আত্মা.
Verdict words: Good ভালো; Mostly good মোটামুটি ভালো; Mixed মিশ্র; Needs some care সামান্য যত্ন প্রয়োজন; Challenging কঠিন.
Nakshatras: অশ্বিনী ভরণী কৃত্তিকা রোহিণী মৃগশিরা আর্দ্রা পুনর্বসু পুষ্যা অশ্লেষা মঘা পূর্ব ফাল্গুনী উত্তর ফাল্গুনী হস্তা চিত্রা স্বাতী বিশাখা অনুরাধা জ্যেষ্ঠা মূলা পূর্বাষাঢ়া উত্তরাষাঢ়া শ্রবণা ধনিষ্ঠা শতভিষা পূর্বভাদ্রপদ উত্তরভাদ্রপদ রেবতী.
Weekdays সোমবার মঙ্গলবার বুধবার বৃহস্পতিবার শুক্রবার শনিবার রবিবার. Koota terms: Varna বর্ণ, Vashya বশ্য, Tara তারা, Yoni যোনি, Graha Maitri গ্রহ মৈত্রী, Gana গণ, Bhakoot ভকূট, Nadi নাড়ী, Ashtakoot Guna Milan অষ্টকূট গুণ মিলন.
Body / health: Ayurveda আয়ুর্বেদ; Prakriti প্রকৃতি; Vata বাত; Pitta পিত্ত; Kapha কফ; Kalapurusha কালপুরুষ.

## Good examples (English -> Bengali)
* `Your mind is calm and steady and needs comfort and routine to feel secure.` -> `আপনার মন শান্ত ও স্থির এবং নিরাপদ বোধ করতে আরাম ও রুটিন দরকার।`
* `You may feel {0} at times.   ## {0}=an emotion` -> `আপনি মাঝে মাঝে {0} বোধ করতে পারেন।`
* `Own sign — colors career and professional standing through Taurus's stability.` -> `স্বরাশি — বৃষের স্থিরতার মাধ্যমে কর্মজীবন ও পেশাগত মর্যাদায় রং যোগ করে।`

When you are finished, reply with ONE short line: the batch number, how many ids you wrote, and `OK` (from the validator).
