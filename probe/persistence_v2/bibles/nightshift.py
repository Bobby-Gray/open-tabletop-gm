"""Nightshift — modern-horror bible + 20-turn script.

Late October, 2am, in a rust-belt Ohio town. Player is a crime reporter
chasing missing-persons leads; recall tests probe whether the model
carries character voice and consequences in a contemporary idiom.
"""
from __future__ import annotations

from .valdremor import Turn, Fact  # reuse dataclasses


BIBLE = """## Campaign: Nightshift in Cresford

**Setting:** Cresford, Ohio — a rust-belt town of 14,000 with a downtown that lost its main employer in 2009. Late October, 2am. The 24-hour gas station, the all-night diner, and the river bridge are the only places open. Something has been pulling people out of cars on the river road; the police investigation has gone quiet.

**Player character:** Marin Cole, a 31-year-old crime reporter for the Cresford Sentinel. Her brother went missing in 2018 and she's been chasing missing-persons leads ever since. Sharp, exhausted, mistrustful of cops. Carries a Sony tape recorder she still uses out of habit.

**Recent events:** Last week, Marin interviewed Halloran (a retired detective). He named a place — the old Wilkes farmhouse off County Route 12 — and told her not to go alone. She went anyway. She got out alive but left her phone in the kitchen. She doesn't know yet what found her phone.

**Factions:**
- **Cresford PD** — the town police force. Sheriff Doyle runs them. Hostile to Marin.
- **The Riverline group** — informal network of locals who've lost someone. Halloran runs them, quietly.

**Current scene:** Marin is in the booth at Lou's Diner — fluorescent light, coffee cooling in the cup, jukebox not playing, two truckers at the counter not talking to each other.
"""

NPCS = """### Halloran
**Role:** Retired detective, runs the informal Riverline group
**Demeanor:** Sixties, slow, used to be tall and isn't anymore. Hand tremor in his right hand.
**Speech quirk:** Pauses before saying any name.

### Sheriff Doyle
**Role:** Cresford PD sheriff, hostile to Marin
**Demeanor:** Heavyset, cropped grey hair, lab-coat clean department uniform. Smells of cigarettes he claims to have quit.
**Speech quirk:** Never raises his voice.

### Eli (diner cook)
**Role:** Lou's Diner night-shift cook, hears everything from the booths
**Demeanor:** Older Black man, broken nose from a long-ago bar fight, calls every regular by their first name.
**Speech quirk:** Hums old Motown under his breath while cooking.

### Cathy Wilkes
**Role:** Daughter of the family who owned the farmhouse on County Route 12
**Demeanor:** Late forties, gaunt, hasn't slept right in weeks; her left eye twitches when she's lying.
**Speech quirk:** Says "I don't know" before answering, then answers.

### Garner
**Role:** Cresford PD deputy, Doyle's enforcer
**Demeanor:** Heavyset, pale, fingers stained yellow from rolling his own cigarettes.
**Speech quirk:** Quotes department procedure word-for-word.
"""

FACTS = (
    Fact("eli_nose", "Eli the diner cook has a broken nose (old bar fight)"),
    Fact("eli_motown", "Eli hums old Motown under his breath while cooking"),
    Fact("cathy_twitch", "Cathy Wilkes's left eye twitches when she's lying"),
    Fact("doyle_quiet", "Sheriff Doyle never raises his voice; he smells of cigarettes he claims to have quit"),
    Fact("doyle_hostile", "Sheriff Doyle is hostile to Marin"),
    Fact("halloran_tremor", "Halloran (the retired detective) has a hand tremor in his right hand"),
    Fact("halloran_pause", "Halloran pauses before saying any name"),
    Fact("phone_left", "Marin left her phone in the Wilkes farmhouse kitchen last week (open thread, unresolved)"),
)

TURNS = (
    Turn(1,  "I scan the diner. Two truckers. Who's behind the counter tonight.", "neutral"),
    Turn(2,  "I sit at the counter where the cook works. I order coffee and a slice of pie I don't want.", "seed",
         seeds=("eli_nose", "eli_motown")),
    Turn(3,  "I ask the cook if anyone's been talking about County Route 12 this week.", "neutral"),
    Turn(4,  "I read his answer. If he's hedging, I let it sit. If he's clean, I move on.", "neutral"),
    Turn(5,  "I pay and head out to my car. The wind off the river smells wet and cold.", "neutral"),
    Turn(6,  "I drive to Halloran's place. He told me to come if I learned anything new.", "seed",
         seeds=("phone_left",)),
    Turn(7,  "I park a block away and walk. I knock at his side door instead of the front.", "neutral"),
    Turn(8,  "Halloran answers. I tell him I went to the farmhouse and left my phone behind. How does he react?", "recall",
         targets=("halloran_tremor", "phone_left")),
    Turn(9,  "I ask him what he thinks happens to people who go to the farmhouse alone. I keep my voice low.", "neutral"),
    Turn(10, "I ask him about Sheriff Doyle. Is Doyle hiding something?", "recall",
         targets=("doyle_hostile", "doyle_quiet")),
    Turn(11, "I leave Halloran. I drive back through downtown toward the diner.", "neutral"),
    Turn(12, "I want to talk to Eli again. Same diner. Same shift.", "recall",
         targets=("eli_nose",)),
    Turn(13, "I tell him I might have something I need help moving. I'm not specific.", "neutral"),
    Turn(14, "He says there's a list — names the PD has been quietly tracking. I ask if my brother's name is on it.", "recall",
         targets=("phone_left",)),
    Turn(15, "If my brother's name IS on it, who else is? I push.", "neutral"),
    Turn(16, "I need to find Cathy Wilkes. Where would she be at 4am?", "seed", seeds=()),
    Turn(17, "I find her. She asks if I went to the farmhouse. I tell her I did. What does her face do when she lies?", "recall",
         targets=("cathy_twitch",)),
    Turn(18, "Cathy wants to know why I'm asking about Sheriff Doyle. I tell her what Halloran told me — she should know it's not just talk.", "recall",
         targets=("doyle_hostile",)),
    Turn(19, "I press her on the farmhouse. I tell her I left my phone in the kitchen. How does she respond?", "neutral"),
    Turn(20, "I leave with her account. As she walks back into her house, what's the last thing she does — a hesitation, a gesture — that tells me whether she was lying?", "recall",
         targets=("cathy_twitch",)),
)
