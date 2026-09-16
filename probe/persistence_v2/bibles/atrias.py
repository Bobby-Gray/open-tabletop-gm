"""Atrias — sci-fi orbital-station bible + 20-turn script.

A beanstalk skyport above a dead colony world. Player is a forensic
accountant turned fixer who may have killed someone on her last job;
recall tests probe whether the model carries that thread.
"""
from __future__ import annotations

from .valdremor import Turn, Fact  # reuse same dataclasses


BIBLE = """## Campaign: The Atrias Loop

**Setting:** Atrias Station — a beanstalk skyport orbiting a dead colony world. The station is the last legal port for the Outer Loop; smugglers and corp courier ships dock side by side. Climate-controlled habitat rings rotate slowly; gravity is 0.3g on the docks, 1g in the core. The station's water plant is failing and the corp that owns it is gouging on rations.

**Player character:** Vex, a former corporate forensic accountant who quit when she discovered the water price-rigging scheme. She freelances as a fixer now — small jobs, no questions. Dry, methodical, distrustful of authority.

**Recent events:** Two cycles ago, Vex accepted a job from Yulen (Loop-side data broker) to extract a corp executive's personal logs. She got the logs, but in the process she destabilized a maintenance drone that may have killed a junior engineer named Rell. She doesn't know yet if Rell survived. She left fast.

**Factions:**
- **Helion Holdings** — the corp that owns the water plant. Tregaard's faction.
- **Loop Hands** — the Outer Loop smugglers' loose coalition. Yulen's faction.

**Current scene:** Vex is at a noodle stand on Habitat Ring 3 — open-air vendor strip with hissing protein presses, fluorescent panel light, the constant low whine of the station's ventilation.
"""

NPCS = """### Yulen
**Role:** Loop-side data broker, gave Vex the corp logs job
**Demeanor:** Tall, thin, prosthetic right arm with a sticking elbow servo. Cautious about debts.
**Speech quirk:** Rounds every price up to a number ending in 7.

### Rell
**Role:** Junior engineer Vex's job may have killed
**Demeanor:** Young, eager, off-station hair (still long, not station-shaved). Owes Vex nothing — Vex owes Rell everything.
**Speech quirk:** Stammers when contradicted.

### Tregaard
**Role:** Helion Holdings water-plant director, target of Vex's prior extraction
**Demeanor:** Heavy, calm, salt-and-pepper close-crop, lab-coat clean.
**Speech quirk:** Never raises his voice.

### Mei (noodle vendor)
**Role:** Ring 3 vendor who knows everyone passing through
**Demeanor:** Older, missing two fingers on her left hand from a press accident. Eyes for trouble.
**Speech quirk:** Calls strangers "kid."

### Anso
**Role:** Helion station security captain
**Demeanor:** Heavyset, magnetic boots scuffed, dislikes Loop-side traders.
**Speech quirk:** Quotes the Station Compact word-for-word.
"""

FACTS = (
    Fact("mei_fingers", "Mei is missing two fingers on her left hand (press accident)"),
    Fact("mei_kid", "Mei calls strangers 'kid'"),
    Fact("rell_eager", "Rell is young, eager, with long off-station hair; Vex owes Rell after a past job"),
    Fact("tregaard_quiet", "Tregaard never raises his voice; he is heavy, calm, lab-coat clean"),
    Fact("tregaard_target", "Tregaard was the target of Vex's prior extraction job"),
    Fact("yulen_arm", "Yulen has a prosthetic right arm with a sticking elbow servo"),
    Fact("yulen_seven", "Yulen rounds every price up to a number ending in 7"),
    Fact("rell_jeopardy", "Vex's prior job may have killed Rell (open thread, unresolved)"),
)

TURNS = (
    Turn(1,  "I scan Ring 3 for tails before approaching any vendor.", "neutral"),
    Turn(2,  "I drift toward Mei's noodle stand. I order a bowl and tip enough that she'll talk.", "seed",
         seeds=("mei_fingers", "mei_kid")),
    Turn(3,  "I ask her if she's heard about anyone Helion is looking for this week.", "neutral"),
    Turn(4,  "I read her response. If she's hedging, I push back gently. If she's clean, I move on.", "neutral"),
    Turn(5,  "I leave Ring 3 and head to the Lower Cargo Spine. Gravity drops to 0.3g as I go.", "neutral"),
    Turn(6,  "I should find out if Rell is alive. I head to the junior crew berths and wait near them, off-camera.", "seed",
         seeds=("rell_jeopardy",)),
    Turn(7,  "I wait until shift change. I follow one of the engineers heading off-shift at a distance.", "neutral"),
    Turn(8,  "I catch up to her in a maintenance corridor and step out. 'Looking for Rell.' How does she react?", "recall",
         targets=("rell_eager", "rell_jeopardy")),
    Turn(9,  "I ask if Rell came back from the incident two cycles ago. I make it clear I'm not Helion.", "neutral"),
    Turn(10, "I press: was Tregaard behind the cleanup?", "recall",
         targets=("tregaard_target",)),
    Turn(11, "I thank her, slip her a credit chit, and head back to Ring 3.", "neutral"),
    Turn(12, "I want to find Mei again. Same stand. Same time slot.", "recall",
         targets=("mei_fingers",)),
    Turn(13, "I tell her I want to find someone discreet. I make it clear I'm willing to trade information.", "neutral"),
    Turn(14, "She mentions a rumor: Helion has a list of station staff who've been flagged 'compromised.' I ask if the junior engineer Rell is on it.", "recall",
         targets=("rell_jeopardy",)),
    Turn(15, "If Rell IS on the list, who else is? I push.", "neutral"),
    Turn(16, "I need to talk to Yulen. Where would they be at this cycle?", "seed", seeds=()),
    Turn(17, "I find Yulen. What's the first thing about them I notice as they move?", "recall",
         targets=("yulen_arm",)),
    Turn(18, "Yulen wants to know why I'm asking about Tregaard. I tell them about the cleanup I think happened — Tregaard should know I have logs.", "recall",
         targets=("tregaard_target", "tregaard_quiet")),
    Turn(19, "They name a price. I haggle, expecting their habit.", "neutral"),
    Turn(20, "Yulen accepts. As they confirm the number, what's the last digit?", "recall",
         targets=("yulen_seven",)),
)
