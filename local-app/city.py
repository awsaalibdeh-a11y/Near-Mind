"""NearMind City: neighborhoods -> buildings -> apartments -> families (4-8 people each).

Everything is generated from a fixed seed, so the city is the same on every run.
Name rules (checked by tests):
  - every neighborhood and building name is different
  - inside a building no first name is used twice, and every family name is different
  - nobody in the whole city has the same full name as anyone else
The flagship building (Sedra, Osama, ... with portraits and recorded demos) is "The Roof Robot Tower" in Al Noor Gardens;
its ten contact people come from street.py, and here they get their families.
"""
from __future__ import annotations

import random

FLAGSHIP = "noor-tower"

HOODS = [
    ("al-noor", "Al Noor Gardens", "🌳", "#8fd6a8", "Leafy streets around the old park"),
    ("palm-bay", "Palm Bay", "🌴", "#7cc8e8", "Sea breeze and new towers by the corniche"),
    ("old-souq", "Old Souq Quarter", "🏺", "#f2b97c", "Narrow lanes, spice shops and big families"),
    ("crescent", "Crescent Hills", "🌙", "#b9a6f0", "Quiet hills where everyone has a car"),
    ("falcon", "Falcon Heights", "🦅", "#f29b9b", "Students, startups and late nights"),
]

BUILDINGS = {   # four per neighborhood, every name different; the first one in Al Noor Gardens is the flagship
    "al-noor": ["The Roof Robot Tower", "Jasmine Court", "Olive Grove House", "Sidra Residence"],
    "palm-bay": ["Coral View", "Pearl Tower", "Dhow Harbour Flats", "Sunset Terrace"],
    "old-souq": ["Saffron House", "Lantern Building", "Cardamom Court", "Copper Gate"],
    "crescent": ["Moonrise Heights", "Juniper Block", "Desert Rose Residence", "Starlight Tower"],
    "falcon": ["Skyline Lofts", "Atlas Hall", "Nova Apartments", "Horizon House"],
}

MALE = """Abdullah Ahmed Adel Amjad Ammar Anwar Ayman Aziz Badr Basel Bilal Dawood Ehab Emad Fahad Faisal Fares Fawaz Ghassan Hadi
Haitham Hamad Hani Harith Hasan Hatem Hisham Husam Ibrahim Idris Imran Ismail Jaber Jalal Jamal Jamil Kamal Karim Khaled Khalil
Luay Mahdi Mahmoud Majed Malik Mamdouh Mansour Marwan Mazen Mishal Mohammed Mostafa Muath Munir Murad Musa Mustafa Nabil Nader Naif
Nasser Nawaf Nizar Omar Qasim Rakan Rami Rashid Rayan Riyad Saad Saber Saeed Salah Saleh Salem Sami Samir Shadi Shaker Sultan Tamer
Tariq Tawfiq Thamer Turki Waleed Wael Yahya Yasser Yazan Younes Zaid Zakaria Ziad Bandar Fadi Hamdan Ilyas Jawad Kareem Laith Moaz
Nour-Aldeen Osman Qais Raed Safwan Talal Usama Wesam Yaman Zuhair Adham Ayham Baraa Diyaa Fouad Hazem Iyad Juma Kinan Labib Maher
Nashat Obaid Raafat Sadiq Taha Wadah Yamen Zayed Aws Hussein Mohanad Mutaz Rabea Suhail Tayseer Ubai Wasim Yusri Amr Bassam Ghazi""".split()
FEMALE = """Aisha Alaa Amal Amira Asil Aya Basma Bayan Dalal Dana Dima Duha Eman Farah Fatima Ghada Hala Hanan Haya Heba Hind Huda Iman Jana
Joud Jumana Kholoud Lama Lamia Lana Lara Lina Lujain Maha Malak Manal Maram Mariam Mona Nada Najla Nawal Nisreen Nouf Rahaf Rana
Rania Rasha Rawan Reem Ruba Rula Sabah Safa Sahar Salma Samar Sana Sara Shahad Shatha Sumaya Suzan Tala Tasneem Wafa Wejdan Yara
Yasmin Zahra Zainab Ruqaya Abeer Afnan Arwa Batool Bushra Dunya Ghala Hadeel Jawaher Juri Leen Lubna Majd Marwa Mayar Mais Nadia
Nermeen Noura Raghad Raneem Razan Rimas Roaa Sadeem Sajida Sereen Shaden Tahani Taghreed Wiam Yumna Zeina Alya Bushra-Noor Dalia
Elaf Fadwa Ghaida Hessa Ibtisam Jood Kawthar Lulwa Maysa Najat Ohood Rafah Sawsan Tamara Wedad Areej Danah Haneen Lojain Nuha""".split()

FAMILIES = """Al-Harbi Al-Qahtani Al-Otaibi Al-Shehri Al-Ghamdi Al-Zahrani Al-Dosari Al-Mutairi Al-Anazi Al-Shammari Al-Juhani Al-Balawi
Al-Rashidi Al-Subaie Al-Tamimi Al-Malki Al-Omari Al-Hazmi Al-Faifi Al-Asiri Al-Amri Al-Shahrani Al-Yami Al-Dawsari Al-Qurashi
Al-Hashimi Al-Saadi Al-Khatib Al-Najjar Al-Haddad Al-Sabbagh Al-Attar Al-Hakim Al-Masri Al-Shami Al-Halabi Al-Baghdadi Al-Yamani
Al-Jaziri Al-Maghribi Al-Tunisi Al-Sudani Al-Kuwaiti Al-Bahraini Al-Omani Al-Qatari Al-Hijazi Al-Najdi Al-Tihami Al-Jawfi
Al-Khayyat Al-Farra Al-Sayegh Al-Ghazali Al-Kindi Al-Farabi Al-Razi Al-Idrisi Al-Biruni Al-Khwarizmi Al-Jazari Al-Battani Al-Zahrawi
Al-Mawsili Al-Dimashqi Al-Ansari Al-Khazraji Al-Awsi Al-Hilali Al-Kilabi Al-Bakri Al-Taghlibi Al-Azdi Al-Hamdani Al-Himyari
Al-Kalbi Al-Tai Al-Sulami Al-Hudhali Al-Thaqafi Al-Makki Al-Madani Al-Taifi Al-Abhawi Al-Jizani Al-Najrani Al-Qassimi Al-Hasawi
Al-Qatifi Al-Khobari Al-Dammami Al-Jubaili Al-Yanbui Al-Tabuki Al-Hailli Al-Baha Al-Arishi Al-Kharji Al-Majmaai Al-Zulfi
Al-Shaqrawi Al-Duwadmi Al-Afifi Al-Ruwaili Al-Sharari Al-Qurayyat Al-Turaifi Al-Badrani Al-Saedi Al-Fahmi Al-Kathiri Al-Mahri
Al-Hadrami Al-Saqqaf Al-Attas Al-Habshi Al-Junaid Al-Bar Al-Muhdar Al-Shatri Al-Aidarous Al-Jifri Al-Haddar Al-Kaf Al-Bin-Shihab
Al-Musawi Al-Husaini Al-Hasani Al-Alawi Al-Abbasi Al-Jaafari Al-Sadiq Al-Kadhimi Al-Ridha Al-Askari Al-Mahdi Al-Rifai Al-Jilani
Al-Shadhili Al-Qadiri Al-Naqshbandi Al-Tijani Al-Sanusi Al-Mirghani Al-Ahmadi Al-Idrisi-Hasani Al-Fassi Al-Marrakshi Al-Tanji
Al-Rabati Al-Wahrani Al-Qasantini Al-Annabi Al-Safaqsi Al-Qayrawani Al-Susi Al-Tarabulsi Al-Benghazi Al-Misrati Al-Zawi Al-Gharyani
Al-Fezzani Al-Iskandarani Al-Saeedi Al-Aswani Al-Minyawi Al-Tantawi Al-Mansouri Al-Dumyati Al-Suwaisi Al-Ismaili Al-Arishi-Sina
Al-Khalili Al-Nabulsi Al-Ramli Al-Lyddawi Al-Yafawi Al-Haifawi Al-Akkawi Al-Safadi Al-Tabarani Al-Baysani Al-Jenini Al-Tulkarmi
Al-Qalqili Al-Ramallawi Al-Bethlehemi Al-Hebroni Al-Gazzawi Al-Rafahi Al-Irbidi Al-Zarqawi Al-Ammani Al-Salti Al-Karaki Al-Tafili
Al-Maani Al-Aqabawi Al-Mafraqi Al-Ajlouni Al-Jarashi Al-Ramthawi Al-Homsi Al-Hamawi Al-Idlibi Al-Latakawi Al-Tartusi Al-Raqqawi
Al-Dayri Al-Hasakawi Al-Daraawi Al-Suwaydawi Al-Qunaitri Al-Beiruti Al-Saidawi Al-Suri Al-Tripolitani Al-Zahlawi Al-Baalbaki
Al-Jbeili Al-Batrouni""".split()

# What a household is like. The contact person is the one NearMind talks to; the family shapes what the home has.
ARCHETYPES = [
    dict(job="nurse", icon="🩹", style="calm & organised", sleep=(22.0, 6.0), car=False,
         home="a first aid kit, a thermometer, flashlights, spare batteries, a power bank, an umbrella, tea, honey",
         wants="a bookshelf, house plants, a coffee machine", budget=250),
    dict(job="carpenter", icon="🪚", style="short & practical", sleep=(22.0, 5.5), car=True,
         home="a cordless drill, a hammer, a saw, a screwdriver set, a 6ft step ladder, clamps, wood glue, a toolbox, an extension cord",
         wants="old furniture to restore, tool sets, a workbench", budget=250),
    dict(job="chef", icon="🍳", style="warm & generous", sleep=(0.0, 8.0), car=False,
         home="a huge cooking pot, sharp knives, an air fryer, rice, flour, eggs, sugar, spices, olive oil, a rice cooker",
         wants="a stand mixer, a cast-iron pan, a big fridge", budget=300),
    dict(job="taxi driver", icon="🚕", style="chatty & helpful", sleep=(1.0, 9.0), car=True,
         home="car jumper cables, a tyre pump, a phone car charger, USB-C chargers, a big umbrella, a flashlight, a cooler box",
         wants="car accessories, a dashcam, a new phone holder", budget=200),
    dict(job="teacher", icon="📚", style="patient & clear", sleep=(22.5, 6.0), car=True,
         home="lots of books, a printer, school supplies, a scientific calculator, board games, a projector, a laminator",
         wants="a bookshelf, a desk lamp, educational toys", budget=200),
    dict(job="pharmacist", icon="💊", style="careful & kind", sleep=(23.0, 6.5), car=True,
         home="a first aid kit, a blood pressure monitor, a thermometer, plasters, an ice pack, a humidifier, a wheelchair from grandma",
         wants="a treadmill, house plants, a reading chair", budget=300),
    dict(job="university student", icon="🎧", style="short & casual", sleep=(3.0, 11.0), car=False,
         home="a game console, an HDMI cable, phone and laptop chargers, a power bank, a ring light, headphones, instant noodles",
         wants="a gaming chair, a monitor, a bike", budget=150),
    dict(job="electrician", icon="⚡", style="direct & quick", sleep=(22.0, 5.5), car=True,
         home="a voltage tester, extension cords, a multimeter, spare bulbs, electrical tape, a ladder, a cordless drill, a work light",
         wants="power tools, a generator, a pickup tool box", budget=300),
    dict(job="baker", icon="🥐", style="sweet & lively", sleep=(21.0, 3.5), car=False,
         home="a stand mixer, baking trays, cake tins, flour, sugar, butter, eggs, vanilla, piping bags, leftover bread",
         wants="a bigger oven, a cast-iron pan, a cake stand", budget=200),
    dict(job="gardener", icon="🪴", style="gentle & slow", sleep=(21.5, 5.0), car=False,
         home="garden tools, a hose, pots, soil, seeds, a wheelbarrow, pruning shears, a watering can, a step ladder",
         wants="house plants, a greenhouse kit, a garden bench", budget=150),
    dict(job="IT engineer", icon="💻", style="upbeat & techy", sleep=(0.5, 7.5), car=True,
         home="spare laptop chargers, a USB-C hub, HDMI and network cables, a router, a soldering iron, a 3D printer, a portable speaker",
         wants="a standing desk, a drone, camping gear", budget=350),
    dict(job="football coach", icon="⚽", style="sporty & direct", sleep=(22.5, 5.0), car=True,
         home="footballs and a pump, cones, yoga mats, a folding table, car jumper cables, a big first aid bag, a cooler box",
         wants="dumbbells, a bike, a rowing machine", budget=250),
    dict(job="tailor", icon="🧵", style="precise & polite", sleep=(22.0, 6.0), car=False,
         home="a sewing machine, a sewing kit, thread, buttons, an iron and ironing board, a steamer, measuring tape, fabric",
         wants="a new sewing machine, a mannequin, a bright lamp", budget=250),
    dict(job="photographer", icon="📷", style="creative & chatty", sleep=(1.0, 9.0), car=True,
         home="cameras, tripods, a ring light, a drone, memory cards, a laptop charger, a projector and screen, a portable speaker",
         wants="a film camera, a desk lamp, a new lens", budget=400),
    dict(job="mechanic", icon="🔧", style="few words, reliable", sleep=(22.0, 5.0), car=True,
         home="a wrench set, car jumper cables, a car jack, a tyre pump, a toolbox, work gloves, motor oil, a bike repair kit",
         wants="old bikes, car parts, a compressor", budget=200),
    dict(job="retired grandfather", icon="☕", style="slow & wise", sleep=(21.0, 4.5), car=False,
         home="a big dallah coffee pot, folding chairs, a prayer mat collection, a wheelchair, a walking stick, dates, a radio, a chess set",
         wants="books, a rocking chair, a good kettle", budget=150),
]

KIDS_STUFF = {"son": ["a football", "a bike", "a skateboard", "a game controller", "a scientific calculator"],
              "daughter": ["a scooter", "art supplies", "a keyboard piano", "a tablet charger", "craft glue"]}
COLORS = ["#ff7eb6", "#f2b560", "#66b8ff", "#8fe0c4", "#a99bff", "#9aa7b1", "#ff8a65", "#26c6da", "#b5d96b", "#e48ad9",
          "#ffb74d", "#4db6ac", "#7986cb", "#f06292", "#aed581", "#ba68c8", "#4fc3f7", "#e57373", "#81c784", "#ffd54f"]

# Families of the ten flagship neighbors (their own facts and inventories stay in street.py).
FLAGSHIP_FAMILIES = {
    "sedra": ("Al-Rashidi", [("Sedra", 22, "herself"), ("Khalil", 52, "father"), ("Manal", 48, "mother"), ("Ziad", 16, "brother"), ("Joud", 11, "sister")]),
    "osama": ("Al-Khatib", [("Osama", 44, "himself"), ("Rania", 41, "wife"), ("Omar", 14, "son"), ("Hala", 12, "daughter"), ("Yahya", 8, "son"), ("Fatima", 72, "mother")]),
    "sulaiman": ("Al-Haddad", [("Sulaiman", 57, "himself"), ("Nawal", 54, "wife"), ("Tariq", 26, "son"), ("Reem", 23, "daughter")]),
    "asma": ("Al-Shehri", [("Asma", 33, "herself"), ("Faisal", 36, "husband"), ("Lana", 6, "daughter"), ("Karim", 4, "son"), ("Huda", 63, "mother")]),
    "alwalid": ("Al-Ghamdi", [("Alwalid", 35, "himself"), ("Dana", 33, "wife"), ("Rayan", 9, "son"), ("Tala", 7, "daughter"), ("Ilyas", 3, "son"), ("Saad", 66, "father"), ("Aisha", 61, "mother")]),
    "anas": ("Al-Juhani", [("Anas", 19, "himself"), ("Majed", 50, "father"), ("Samar", 46, "mother"), ("Lujain", 15, "sister")]),
    "layla": ("Al-Tamimi", [("Layla", 64, "herself"), ("Adel", 40, "son"), ("Shahad", 37, "daughter-in-law"), ("Yazan", 12, "grandson"), ("Lina", 10, "granddaughter"), ("Malik", 6, "grandson")]),
    "yousef": ("Al-Qahtani", [("Yousef", 28, "himself"), ("Nada", 27, "wife"), ("Basel", 30, "brother"), ("Haya", 55, "mother")]),
    "noor": ("Al-Subaie", [("Noor", 26, "herself"), ("Hisham", 29, "husband"), ("Salma", 2, "daughter"), ("Rawan", 24, "sister"), ("Mona", 58, "mother")]),
    "hamza": ("Al-Dosari", [("Hamza", 34, "himself"), ("Yara", 31, "wife"), ("Rakan", 13, "son"), ("Fares", 10, "son"), ("Sumaya", 7, "daughter"), ("Abdullah", 5, "son"), ("Ghada", 60, "mother"), ("Mansour", 28, "brother")]),
}


def _slug(s):
    return "-".join("".join(c for c in w if c.isalnum()) for w in s.lower().split())


def _ascii_id(name):
    return "".join(c for c in name.lower() if c.isalpha())


def _family(rng, contact, gender, size, used_first, used_full, fam):
    """The contact plus size-1 relatives: partner, kids (sons and daughters), sometimes grandparents or an uncle."""
    def pick(pool):
        for _ in range(400):
            n = rng.choice(pool)
            if n not in used_first and f"{n} {fam}" not in used_full:
                used_first.add(n)
                used_full.add(f"{n} {fam}")
                return n
        raise RuntimeError("ran out of names")
    age = rng.randint(30, 58)
    members = [(contact, age, "herself" if gender == "f" else "himself")]
    left = size - 1
    if left:
        members.append((pick(MALE if gender == "f" else FEMALE), age + rng.randint(-4, 4), "husband" if gender == "f" else "wife"))
        left -= 1
    elders = min(left, rng.choice([0, 0, 1, 2])) if left > 2 else 0
    for _ in range(left - elders):
        g = rng.choice("sd")
        members.append((pick(MALE if g == "s" else FEMALE), rng.randint(1, max(2, age - 20)), "son" if g == "s" else "daughter"))
    for k in range(elders):
        members.append((pick(FEMALE if k == 0 else MALE), age + rng.randint(24, 32), "grandmother" if k == 0 else "grandfather"))
    return members


def build(street_n=None, street_order=None):
    """Returns (hoods, buildings). buildings[bid] = {name, hood, order, N} where N matches street.py's neighbor format."""
    rng = random.Random(2026)
    fams = FAMILIES[:]
    rng.shuffle(fams)
    for f, _ in FLAGSHIP_FAMILIES.values():   # flagship family names are taken first
        fams.remove(f)
    used_full = {f"{n} {f}" for f, ms in FLAGSHIP_FAMILIES.values() for n, _, _ in ms}
    hoods, buildings = [], {}
    for hid, hname, hicon, hcolor, hdesc in HOODS:
        bids = []
        for bi, bname in enumerate(BUILDINGS[hid]):
            bid = FLAGSHIP if (hid == "al-noor" and bi == 0) else _slug(bname)
            bids.append(bid)
            if bid == FLAGSHIP and street_n:
                N = {}
                for nid in street_order:
                    fam, ms = FLAGSHIP_FAMILIES[nid]
                    N[nid] = dict(street_n[nid], family=fam, members=[{"name": a, "age": b, "role": c} for a, b, c in ms])
                buildings[bid] = {"name": bname, "hood": hid, "order": list(street_order), "N": N, "flagship": True}
                continue
            used_first, N, order = set(), {}, []
            for floor in range(1, 6):
                for side in "AB":
                    a = rng.choice(ARCHETYPES)
                    gender = rng.choice("mf")
                    fam = fams.pop()
                    while True:
                        contact = rng.choice(FEMALE if gender == "f" else MALE)
                        if contact not in used_first and f"{contact} {fam}" not in used_full and _ascii_id(contact) not in N:
                            break
                    used_first.add(contact)
                    used_full.add(f"{contact} {fam}")
                    size = rng.randint(4, 8)
                    members = _family(rng, contact, gender, size, used_first, used_full, fam)
                    kids = [m for m in members if m[2] in ("son", "daughter")]
                    extra = sorted({rng.choice(KIDS_STUFF[m[2]]) for m in kids if m[1] >= 6})
                    age = members[0][1]
                    nid = _ascii_id(contact)
                    pron = "her" if gender == "f" else "his"
                    teen = [m for m in kids if 13 <= m[1] <= 19]
                    facts = [f"{age}, {a['job']}", f"Family of {size}: " + ", ".join(f"{m[2]} {m[0]}" for m in members[1:4]) + ("…" if size > 4 else ""),
                             "Has a car" if a["car"] else "No car",
                             f"Asleep about {int(a['sleep'][0]):02d}:{int(a['sleep'][0] % 1 * 60):02d}-{int(a['sleep'][1]):02d}:{int(a['sleep'][1] % 1 * 60):02d}"]
                    if teen:
                        facts.append(f"{pron.capitalize()} {teen[0][2]} {teen[0][0]} ({teen[0][1]}) often helps carry things")
                    fam_line = "; ".join(f"{m[0]} ({m[2]}, {m[1]})" for m in members[1:])
                    home = (f"You are {contact} {fam}, {age}, a {a['job']} in apartment {floor}{side} of {bname}, {hname}. Style: {a['style']}. "
                            f"You live with: {fam_line}. At home: {a['home']}" + (", " + ", ".join(extra) if extra else "") + ". "
                            + ("You have a car and can give short rides. " if a["car"] else "You have no car. ")
                            + f"Your family members can help (e.g. a teenager can carry things down), and you may mention them by name. "
                            f"You'd happily BUY: {a['wants']}. Budget: up to about {a['budget']} SAR.")
                    N[nid] = dict(name=contact, family=fam, apt=f"{floor}{side}", color=rng.choice(COLORS), icon=a["icon"], style=a["style"],
                                  facts=facts, sleep=a["sleep"], home=home,
                                  members=[{"name": m[0], "age": m[1], "role": m[2]} for m in members])
                    order.append(nid)
            buildings[bid] = {"name": bname, "hood": hid, "order": order, "N": N, "flagship": False}
        hoods.append({"id": hid, "name": hname, "icon": hicon, "color": hcolor, "desc": hdesc, "buildings": bids})
    return hoods, buildings
