"""Valdremor — medieval-fantasy bible + 20-turn script.

A ruined-empire city beneath a still-active volcano. Player is a half-elf
rogue who let a witness go on her last heist; recall tests probe whether
the model remembers that choice's consequence across 14+ turns.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


TurnKind = Literal["seed", "neutral", "recall"]


@dataclass(frozen=True)
class Turn:
    idx: int
    action: str
    kind: TurnKind
    seeds: tuple[str, ...] = ()
    targets: tuple[str, ...] = ()


@dataclass(frozen=True)
class Fact:
    id: str
    description: str


BIBLE = """## Campaign: The Ashen Crown

**Setting:** Valdremor — a city built on the ruins of a destroyed empire. Ash falls from the Cinderpeak volcano to the north. The ruling Merchant Council controls all trade; the Thornwarden thieves' guild controls everything else.

**Player character:** Sable, a half-elf rogue, former Council courier who went rogue after witnessing a Council assassination. Cautious, dry humor, loyal to very few people.

**Recent events:** Three sessions ago, Sable accepted a job from Mira (Thornwarden fixer) to steal a ledger from a Council warehouse. Sable got the ledger but also let a bound warehouse guard go free — a choice that broke the job's clean exit and left a witness.

**Factions:**
- **Merchant Council** — runs Valdremor. Ruthless, well-funded. Vael's faction.
- **Thornwarden** — thieves' guild. Mira's faction. In tension with the Council.

**Current scene:** Sable is moving through the Ashmarket — a covered bazaar in Valdremor's lower district, smoky and loud, vendors selling everything from spiced eel to forged travel papers.
"""

NPCS = """### Mira
**Role:** Thornwarden fixer
**Demeanor:** Wiry, 40s, missing the tip of her left index finger. Always negotiating.
**Speech quirk:** Drops half-finished idioms. Smells of cloves.

### Aldric
**Role:** Warehouse guard Sable freed
**Demeanor:** Young, nervous, owes Sable a life debt he doesn't know how to repay.
**Speech quirk:** Stammers when contradicted.

### Councillor Vael
**Role:** Merchant Council member who ordered the assassination Sable witnessed
**Demeanor:** Cold, meticulous, believes the city's survival requires ugly choices.
**Speech quirk:** Never raises his voice.

### Tessen (spice vendor)
**Role:** Ashmarket vendor (older woman, broken nose)
**Demeanor:** Sells clove-bundle wraps from a brass tray. Sharp eyes for trouble.
**Speech quirk:** Calls everyone "love."

### Brennick
**Role:** Council guard captain
**Demeanor:** Heavyset, scarred jaw, hates the Thornwardens.
**Speech quirk:** Quotes the city charter.
"""

FACTS = (
    Fact("mira_clove", "Mira smells of cloves (the bible anchor scent)"),
    Fact("mira_finger", "Mira is missing the tip of her left index finger"),
    Fact("aldric_nervous", "Aldric is young and nervous; he owes Sable a life debt"),
    Fact("vael_quiet", "Vael never raises his voice; he is cold and meticulous"),
    Fact("vael_assassin", "Vael ordered the assassination Sable witnessed"),
    Fact("tessen_nose", "Tessen (the spice vendor introduced turn 2) has a broken nose, older, sells clove wraps on a brass tray"),
    Fact("brennick_charter", "Brennick (Council guard captain) quotes the city charter and has a scarred jaw"),
    Fact("aldric_freed", "Sable previously freed Aldric during the warehouse job — a choice with consequence"),
)

TURNS = (
    Turn(1,  "I move deeper into the Ashmarket, hood up, scanning for tails.", "neutral"),
    Turn(2,  "I find Tessen's stall and approach casually, keeping my hands visible.", "seed",
         seeds=("tessen_nose",)),
    Turn(3,  "I ask her if she knew a ledger came through the warehouse on Eel Street last month.", "neutral"),
    Turn(4,  "I read her response carefully. If she's hiding something, I lean in and offer coin for the truth.", "neutral"),
    Turn(5,  "I leave the Ashmarket and head to the Salt Stairs. The fog is thick tonight.", "neutral"),
    Turn(6,  "Aldric should be on warehouse rotation this week. I find a vantage where I can watch the Council warehouses without being seen.", "seed",
         seeds=("aldric_freed",)),
    Turn(7,  "I wait until I see Aldric come off shift. I follow him at a distance.", "neutral"),
    Turn(8,  "When he's alone in a side alley I step out from behind a stack of crates. 'It's me.' How does he react?", "recall",
         targets=("aldric_nervous", "aldric_freed")),
    Turn(9,  "I ask him what the Council is moving through the warehouses now. I tell him I'm not here to hurt him; I just need to know who's directing the operations.", "neutral"),
    Turn(10, "I press: is Councillor Vael behind it?", "recall",
         targets=("vael_assassin",)),
    Turn(11, "I leave Aldric with a small purse and tell him to lay low. I head back to the Ashmarket.", "neutral"),
    Turn(12, "I look for the spice vendor I spoke to earlier. Same stall. I want to know if she's still there.", "recall",
         targets=("tessen_nose",)),
    Turn(13, "I want her name now. I tell her I have something to trade if she helps me.", "neutral"),
    Turn(14, "She mentions the Thornwarden talk: word is the Council has a ledger of every guard who's been compromised. I tell her about the guard I let go — does that name appear on it?", "recall",
         targets=("aldric_freed",)),
    Turn(15, "If Aldric IS on the ledger, who else is? I push for more.", "neutral"),
    Turn(16, "I need to talk to Mira. Where would she be at this hour?", "seed", seeds=()),
    Turn(17, "I find her. What does she smell like?", "recall",
         targets=("mira_clove",)),
    Turn(18, "Mira wants to know why I'm asking about Vael. I tell her about the assassination I witnessed — she should know that's not just talk.", "recall",
         targets=("vael_assassin",)),
    Turn(19, "She names a price. I haggle.", "neutral"),
    Turn(20, "I leave with her terms. As I'm walking out, what does she do — a gesture, a word — that tells me whether she'll honor the deal?", "recall",
         targets=("mira_finger",)),
)
