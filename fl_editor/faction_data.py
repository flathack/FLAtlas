"""Faction data model and INI parser/writer for Freelancer faction files.

Handles:
    - DATA/initialworld.ini   → [Group] sections (faction definitions + reputations)
    - DATA/MISSIONS/empathy.ini → [RepChangeEffects] sections (empathy rates)
    - DATA/MISSIONS/faction_prop.ini → [FactionProps] sections (faction properties)
"""
from __future__ import annotations

import copy
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .parser import FLParser
from .path_utils import ci_resolve

_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
#  Data classes
# ---------------------------------------------------------------------------

@dataclass
class FactionRep:
    """Single reputation entry toward another faction."""
    target: str          # nickname of the other faction
    value: float         # -1.0 .. 1.0

@dataclass
class EmpathyEvent:
    """One event entry inside a [RepChangeEffects] block."""
    event_type: str      # e.g. "object_destruction"
    value: float

@dataclass
class EmpathyRate:
    """One empathy_rate entry inside a [RepChangeEffects] block."""
    target: str          # nickname of the other faction
    rate: float

@dataclass
class FactionPropData:
    """Parsed [FactionProps] block."""
    affiliation: str = ""
    legality: str = ""
    nickname_plurality: str = ""
    msg_id_prefix: str = ""
    jump_preference: str = ""
    npc_ships: list[str] = field(default_factory=list)
    voices: list[str] = field(default_factory=list)
    mc_costume: str = ""
    space_costumes: list[str] = field(default_factory=list)
    firstname_male: str = ""
    firstname_female: str = ""
    lastname: str = ""
    rank_desig: str = ""
    formation_desig: str = ""
    large_ship_desig: str = ""
    large_ship_names: str = ""
    scan_for_cargo: list[str] = field(default_factory=list)
    scan_announce: str = ""
    scan_chance: str = ""
    formations: list[str] = field(default_factory=list)
    _raw_entries: list[tuple[str, str]] = field(default_factory=list)

@dataclass
class Faction:
    """Complete faction record assembled from all three INI files."""
    nickname: str
    ids_name: str = ""
    ids_info: str = ""
    ids_short_name: str = ""
    reputations: list[FactionRep] = field(default_factory=list)
    empathy_events: list[EmpathyEvent] = field(default_factory=list)
    empathy_rates: list[EmpathyRate] = field(default_factory=list)
    props: FactionPropData | None = None
    # Source tracking
    in_initialworld: bool = False
    in_empathy: bool = False
    in_faction_prop: bool = False
    # Raw sections for faithful re-serialization
    _iw_entries: list[tuple[str, str]] = field(default_factory=list)
    _emp_entries: list[tuple[str, str]] = field(default_factory=list)

# ---------------------------------------------------------------------------
#  World model
# ---------------------------------------------------------------------------

class FactionWorld:
    """In-memory model of all factions assembled from the three INI files."""

    def __init__(self) -> None:
        self.factions: dict[str, Faction] = {}  # nickname → Faction
        self._iw_sections: list[tuple[str, list[tuple[str, str]]]] = []
        self._emp_sections: list[tuple[str, list[tuple[str, str]]]] = []
        self._fp_sections: list[tuple[str, list[tuple[str, str]]]] = []
        self._iw_path: str = ""
        self._emp_path: str = ""
        self._fp_path: str = ""
        self._locked_gates: list[tuple[str, str]] = []  # preserve locked_gates section

    # ------------------------------------------------------------------
    #  Load
    # ------------------------------------------------------------------
    def load(self, game_path: str) -> list[str]:
        """Parse all three faction files. Returns list of warning messages."""
        warnings: list[str] = []
        parser = FLParser()
        base = Path(game_path)

        # initialworld.ini
        iw = _resolve_path(base, "DATA/initialworld.ini")
        if iw:
            self._iw_path = str(iw)
            self._iw_sections = parser.parse(str(iw))
            self._parse_initialworld(self._iw_sections)
        else:
            warnings.append("initialworld.ini not found")

        # empathy.ini
        emp = _resolve_path(base, "DATA/MISSIONS/empathy.ini")
        if emp:
            self._emp_path = str(emp)
            self._emp_sections = parser.parse(str(emp))
            self._parse_empathy(self._emp_sections)
        else:
            warnings.append("empathy.ini not found")

        # faction_prop.ini
        fp = _resolve_path(base, "DATA/MISSIONS/faction_prop.ini")
        if fp:
            self._fp_path = str(fp)
            self._fp_sections = parser.parse(str(fp))
            self._parse_faction_prop(self._fp_sections)
        else:
            warnings.append("faction_prop.ini not found")

        return warnings

    # ------------------------------------------------------------------
    #  Parse helpers
    # ------------------------------------------------------------------
    def _parse_initialworld(self, sections: list[tuple[str, list[tuple[str, str]]]]) -> None:
        for sec_name, entries in sections:
            low = sec_name.lower()
            if low == "locked_gates":
                self._locked_gates = list(entries)
                continue
            if low != "group":
                continue
            nickname = ""
            ids_name = ""
            ids_info = ""
            ids_short_name = ""
            reps: list[FactionRep] = []
            for k, v in entries:
                kl = k.lower().strip()
                if kl == "nickname":
                    nickname = v.strip()
                elif kl == "ids_name":
                    ids_name = v.strip()
                elif kl == "ids_info":
                    ids_info = v.strip()
                elif kl == "ids_short_name":
                    ids_short_name = v.strip()
                elif kl == "rep":
                    parts = [p.strip() for p in v.split(",", 1)]
                    if len(parts) == 2:
                        try:
                            reps.append(FactionRep(target=parts[1], value=float(parts[0])))
                        except ValueError:
                            pass
            if not nickname:
                continue
            nick_lower = nickname.lower()
            fac = self.factions.get(nick_lower)
            if fac is None:
                fac = Faction(nickname=nickname)
                self.factions[nick_lower] = fac
            fac.ids_name = ids_name
            fac.ids_info = ids_info
            fac.ids_short_name = ids_short_name
            fac.reputations = reps
            fac.in_initialworld = True
            fac._iw_entries = list(entries)

    def _parse_empathy(self, sections: list[tuple[str, list[tuple[str, str]]]]) -> None:
        for sec_name, entries in sections:
            if sec_name.lower() != "repchangeeffects":
                continue
            group = ""
            events: list[EmpathyEvent] = []
            rates: list[EmpathyRate] = []
            for k, v in entries:
                kl = k.lower().strip()
                if kl == "group":
                    group = v.strip()
                elif kl == "event":
                    parts = [p.strip() for p in v.split(",", 1)]
                    if len(parts) == 2:
                        try:
                            events.append(EmpathyEvent(event_type=parts[0], value=float(parts[1])))
                        except ValueError:
                            pass
                elif kl == "empathy_rate":
                    parts = [p.strip() for p in v.split(",", 1)]
                    if len(parts) == 2:
                        try:
                            rates.append(EmpathyRate(target=parts[0], rate=float(parts[1])))
                        except ValueError:
                            pass
            if not group:
                continue
            nick_lower = group.lower()
            fac = self.factions.get(nick_lower)
            if fac is None:
                fac = Faction(nickname=group)
                self.factions[nick_lower] = fac
            fac.empathy_events = events
            fac.empathy_rates = rates
            fac.in_empathy = True
            fac._emp_entries = list(entries)

    def _parse_faction_prop(self, sections: list[tuple[str, list[tuple[str, str]]]]) -> None:
        for sec_name, entries in sections:
            if sec_name.lower() != "factionprops":
                continue
            affiliation = ""
            props = FactionPropData()
            props._raw_entries = list(entries)
            for k, v in entries:
                kl = k.lower().strip()
                val = v.strip()
                if kl == "affiliation":
                    affiliation = val
                    props.affiliation = val
                elif kl == "legality":
                    props.legality = val
                elif kl == "nickname_plurality":
                    props.nickname_plurality = val
                elif kl == "msg_id_prefix":
                    props.msg_id_prefix = val
                elif kl == "jump_preference":
                    props.jump_preference = val
                elif kl == "npc_ship":
                    props.npc_ships.append(val)
                elif kl == "voice":
                    props.voices.append(val)
                elif kl == "mc_costume":
                    props.mc_costume = val
                elif kl == "space_costume":
                    props.space_costumes.append(val)
                elif kl == "firstname_male":
                    props.firstname_male = val
                elif kl == "firstname_female":
                    props.firstname_female = val
                elif kl == "lastname":
                    props.lastname = val
                elif kl == "rank_desig":
                    props.rank_desig = val
                elif kl == "formation_desig":
                    props.formation_desig = val
                elif kl == "large_ship_desig":
                    props.large_ship_desig = val
                elif kl == "large_ship_names":
                    props.large_ship_names = val
                elif kl == "scan_for_cargo":
                    props.scan_for_cargo.append(val)
                elif kl == "scan_announce":
                    props.scan_announce = val
                elif kl == "scan_chance":
                    props.scan_chance = val
                elif kl == "formation":
                    props.formations.append(val)
            if not affiliation:
                continue
            nick_lower = affiliation.lower()
            fac = self.factions.get(nick_lower)
            if fac is None:
                fac = Faction(nickname=affiliation)
                self.factions[nick_lower] = fac
            fac.props = props
            fac.in_faction_prop = True

    # ------------------------------------------------------------------
    #  Serialize / Write
    # ------------------------------------------------------------------
    def build_initialworld_sections(self) -> list[tuple[str, list[tuple[str, str]]]]:
        """Re-build sections list for initialworld.ini from the current model."""
        sections: list[tuple[str, list[tuple[str, str]]]] = []
        if self._locked_gates:
            sections.append(("locked_gates", list(self._locked_gates)))
        for fac in self.factions.values():
            if not fac.in_initialworld:
                continue
            entries: list[tuple[str, str]] = []
            entries.append(("nickname", fac.nickname))
            if fac.ids_name:
                entries.append(("ids_name", fac.ids_name))
            if fac.ids_info:
                entries.append(("ids_info", fac.ids_info))
            if fac.ids_short_name:
                entries.append(("ids_short_name", fac.ids_short_name))
            for rep in fac.reputations:
                entries.append(("rep", f"{rep.value}, {rep.target}"))
            sections.append(("Group", entries))
        return sections

    def build_empathy_sections(self) -> list[tuple[str, list[tuple[str, str]]]]:
        """Re-build sections list for empathy.ini from the current model."""
        sections: list[tuple[str, list[tuple[str, str]]]] = []
        for fac in self.factions.values():
            if not fac.in_empathy:
                continue
            entries: list[tuple[str, str]] = []
            entries.append(("group", fac.nickname))
            for ev in fac.empathy_events:
                entries.append(("event", f"{ev.event_type}, {ev.value}"))
            for er in fac.empathy_rates:
                entries.append(("empathy_rate", f"{er.target}, {er.rate}"))
            sections.append(("RepChangeEffects", entries))
        return sections

    def build_faction_prop_sections(self) -> list[tuple[str, list[tuple[str, str]]]]:
        """Re-build sections list for faction_prop.ini from the current model."""
        sections: list[tuple[str, list[tuple[str, str]]]] = []
        for fac in self.factions.values():
            if not fac.in_faction_prop or fac.props is None:
                continue
            entries: list[tuple[str, str]] = []
            entries.append(("affiliation", fac.nickname))
            p = fac.props
            if p.legality:
                entries.append(("legality", p.legality))
            if p.nickname_plurality:
                entries.append(("nickname_plurality", p.nickname_plurality))
            if p.msg_id_prefix:
                entries.append(("msg_id_prefix", p.msg_id_prefix))
            if p.jump_preference:
                entries.append(("jump_preference", p.jump_preference))
            for ns in p.npc_ships:
                entries.append(("npc_ship", ns))
            for voice in p.voices:
                entries.append(("voice", voice))
            if p.mc_costume:
                entries.append(("mc_costume", p.mc_costume))
            for sc in p.space_costumes:
                entries.append(("space_costume", sc))
            if p.firstname_male:
                entries.append(("firstname_male", p.firstname_male))
            if p.firstname_female:
                entries.append(("firstname_female", p.firstname_female))
            if p.lastname:
                entries.append(("lastname", p.lastname))
            if p.rank_desig:
                entries.append(("rank_desig", p.rank_desig))
            if p.formation_desig:
                entries.append(("formation_desig", p.formation_desig))
            if p.large_ship_desig:
                entries.append(("large_ship_desig", p.large_ship_desig))
            if p.large_ship_names:
                entries.append(("large_ship_names", p.large_ship_names))
            for sc in p.scan_for_cargo:
                entries.append(("scan_for_cargo", sc))
            if p.scan_announce:
                entries.append(("scan_announce", p.scan_announce))
            if p.scan_chance:
                entries.append(("scan_chance", p.scan_chance))
            for fm in p.formations:
                entries.append(("formation", fm))
            sections.append(("FactionProps", entries))
        return sections

    # ------------------------------------------------------------------
    #  Mutation helpers
    # ------------------------------------------------------------------
    def add_faction(self, nickname: str) -> Faction:
        """Create a new empty faction in all three files."""
        nick_lower = nickname.lower()
        if nick_lower in self.factions:
            return self.factions[nick_lower]
        fac = Faction(
            nickname=nickname,
            in_initialworld=True,
            in_empathy=True,
            in_faction_prop=True,
        )
        # Default empathy events (Freelancer standard values)
        fac.empathy_events = [
            EmpathyEvent("object_destruction", -0.02),
            EmpathyEvent("random_mission_success", 0.04),
            EmpathyEvent("random_mission_failure", -0.02),
            EmpathyEvent("random_mission_abortion", -0.02),
        ]
        # Default empathy rates: 0 toward all existing factions
        for existing_nick in self.factions:
            fac.empathy_rates.append(EmpathyRate(target=self.factions[existing_nick].nickname, rate=0.0))
        # Default neutral reputations toward all existing factions
        for existing_nick in self.factions:
            fac.reputations.append(FactionRep(target=self.factions[existing_nick].nickname, value=0.0))
        # Default faction props
        fac.props = FactionPropData(
            affiliation=nickname,
            legality="unlawful",
            nickname_plurality="singular",
            msg_id_prefix="ignore",
            jump_preference="jumpgate",
        )
        self.factions[nick_lower] = fac
        # Add reciprocal entries in existing factions
        for existing_nick, existing_fac in self.factions.items():
            if existing_nick == nick_lower:
                continue
            if existing_fac.in_initialworld:
                existing_fac.reputations.append(FactionRep(target=nickname, value=0.0))
            if existing_fac.in_empathy:
                existing_fac.empathy_rates.append(EmpathyRate(target=nickname, rate=0.0))
        return fac

    def set_reputation(self, from_nick: str, to_nick: str, value: float) -> None:
        """Set the reputation from one faction toward another."""
        fac = self.factions.get(from_nick.lower())
        if fac is None:
            return
        value = max(-1.0, min(1.0, value))
        for rep in fac.reputations:
            if rep.target.lower() == to_nick.lower():
                rep.value = value
                return
        fac.reputations.append(FactionRep(target=to_nick, value=value))

    def set_empathy_rate(self, from_nick: str, to_nick: str, rate: float) -> None:
        """Set the empathy rate from one faction toward another."""
        fac = self.factions.get(from_nick.lower())
        if fac is None:
            return
        for er in fac.empathy_rates:
            if er.target.lower() == to_nick.lower():
                er.rate = rate
                return
        fac.empathy_rates.append(EmpathyRate(target=to_nick, rate=rate))

    def get_reputation(self, from_nick: str, to_nick: str) -> float | None:
        """Get the reputation from one faction toward another."""
        fac = self.factions.get(from_nick.lower())
        if fac is None:
            return None
        for rep in fac.reputations:
            if rep.target.lower() == to_nick.lower():
                return rep.value
        return None

    def sorted_nicknames(self) -> list[str]:
        """Return all faction nicknames sorted alphabetically."""
        return sorted(self.factions.keys())

    # ------------------------------------------------------------------
    #  Validation
    # ------------------------------------------------------------------
    def validate(self) -> list[dict[str, str]]:
        """Run validation checks. Returns list of {severity, faction, message}."""
        issues: list[dict[str, str]] = []
        all_nicks = set(self.factions.keys())

        for nick, fac in self.factions.items():
            # Check presence in all three files
            if not fac.in_initialworld:
                issues.append({"severity": "warning", "faction": nick,
                               "message": "Missing from initialworld.ini"})
            if not fac.in_empathy:
                issues.append({"severity": "warning", "faction": nick,
                               "message": "Missing from empathy.ini"})
            if not fac.in_faction_prop:
                issues.append({"severity": "warning", "faction": nick,
                               "message": "Missing from faction_prop.ini"})

            # Check reputation completeness
            rep_targets = {r.target.lower() for r in fac.reputations}
            for other_nick in all_nicks:
                if other_nick == nick:
                    continue
                if other_nick not in rep_targets:
                    issues.append({"severity": "info", "faction": nick,
                                   "message": f"No rep entry toward '{other_nick}'"})

            # Check empathy rate completeness
            emp_targets = {r.target.lower() for r in fac.empathy_rates}
            for other_nick in all_nicks:
                if other_nick == nick:
                    continue
                if other_nick not in emp_targets:
                    issues.append({"severity": "info", "faction": nick,
                                   "message": f"No empathy_rate toward '{other_nick}'"})

            # Check empathy events (should have exactly 4)
            if fac.in_empathy and len(fac.empathy_events) != 4:
                issues.append({"severity": "warning", "faction": nick,
                               "message": f"Expected 4 empathy events, found {len(fac.empathy_events)}"})

            # Check faction_prop affiliation mismatch
            if fac.props is not None and fac.props.affiliation.lower() != nick:
                issues.append({"severity": "critical", "faction": nick,
                               "message": f"FactionProps affiliation mismatch: '{fac.props.affiliation}'"})

        # Check for duplicate nicknames (case collision)
        seen: dict[str, str] = {}
        for nick, fac in self.factions.items():
            original = fac.nickname
            low = nick.lower()
            if low in seen and seen[low] != original:
                issues.append({"severity": "critical", "faction": nick,
                               "message": f"Duplicate nickname (case variant): '{seen[low]}' vs '{original}'"})
            seen[low] = original

        return issues

    # ------------------------------------------------------------------
    #  Deep copy for diff preview
    # ------------------------------------------------------------------
    def snapshot(self) -> FactionWorld:
        """Return a deep copy of this world for diff comparison."""
        return copy.deepcopy(self)


# ---------------------------------------------------------------------------
#  Path resolution helper
# ---------------------------------------------------------------------------
def _resolve_path(base: Path, rel: str) -> Path | None:
    """Case-insensitive path resolution for Freelancer game files."""
    result = ci_resolve(base, rel)
    if result and result.is_file():
        return result
    # Try direct (case-sensitive) as fallback
    direct = base / rel
    if direct.is_file():
        return direct
    return None
