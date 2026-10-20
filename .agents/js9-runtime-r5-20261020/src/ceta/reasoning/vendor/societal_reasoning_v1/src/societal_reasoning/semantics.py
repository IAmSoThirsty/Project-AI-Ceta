"""Offline, source-linked lexical sense contract.

Dictionary citations are references; explanatory glosses are ORIGINAL project text,
NOT Merriam-Webster quotations or a redistribution of dictionary entries.
Unresolved material terms block a provisional interpretation; this module makes
no claim to parse arbitrary prose or infer the speaker's private intentions.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files
from typing import Any
from urllib.parse import urlsplit


@dataclass(frozen=True, slots=True)
class Sense:
    id: str
    gloss: str
    mw_reference: str

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> Sense:
        if set(row) != {"id", "gloss", "mw_reference"}:
            raise ValueError("Sense requires id, gloss, and mw_reference only")
        if not all(isinstance(row[k], str) and row[k].strip() for k in row):
            raise ValueError("Sense fields must be nonempty strings")
        return cls(**row)

    def to_dict(self) -> dict[str, str]:
        return {"id": self.id, "gloss": self.gloss, "mw_reference": self.mw_reference}


@dataclass(frozen=True, slots=True)
class Term:
    term: str
    url: str
    senses: tuple[Sense, ...]

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> Term:
        if set(row) != {"term", "url", "senses"}:
            raise ValueError("Term requires term, url, and senses only")
        term, url = row["term"], row["url"]
        if not isinstance(term, str) or not term.strip() or term != term.strip().lower():
            raise ValueError("Term must be a lowercase canonical word")
        parsed = urlsplit(url) if isinstance(url, str) else None
        if not parsed or parsed.scheme != "https" or parsed.netloc != "www.merriam-webster.com" or not parsed.path.startswith("/dictionary/"):
            raise ValueError("Canonical Merriam-Webster HTTPS dictionary URL required")
        if not isinstance(row["senses"], list) or not row["senses"]:
            raise ValueError("A term must contain at least one cited sense")
        senses = tuple(Sense.from_dict(entry) for entry in row["senses"])
        if len({s.id for s in senses}) != len(senses):
            raise ValueError("Duplicate dictionary sense id")
        return cls(term, url, senses)

    def to_dict(self) -> dict[str, Any]:
        return {"term": self.term, "url": self.url, "dictionary": "Merriam-Webster",
                "gloss_status": "original_project_paraphrase_not_dictionary_quote",
                "senses": [s.to_dict() for s in self.senses]}


class LexicalRegistry:
    def __init__(self, terms: list[Term]):
        self.terms: dict[str, Term] = {}
        for entry in terms:
            if entry.term in self.terms:
                raise ValueError(f"Duplicate term: {entry.term}")
            self.terms[entry.term] = entry

    @classmethod
    def starter(cls) -> LexicalRegistry:
        with files("societal_reasoning").joinpath("resources", "mw_lexicon.v1.json").open(encoding="utf-8") as file:
            raw = json.load(file)
        if set(raw) != {"version", "dictionary", "license_note", "terms"} or raw["version"] != "1.0" or raw["dictionary"] != "Merriam-Webster":
            raise ValueError("Invalid lexical registry header")
        if not isinstance(raw["license_note"], str) or not raw["license_note"].strip():
            raise ValueError("Missing licensing explanation")
        if not isinstance(raw["terms"], list):
            raise ValueError("Invalid lexical registry terms")
        return cls([Term.from_dict(row) for row in raw["terms"]])

    def lookup(self, word: str) -> dict[str, Any] | None:
        if not isinstance(word, str) or not word.strip():
            raise ValueError("Nonempty term required")
        entry = self.terms.get(word.strip().casefold())
        return entry.to_dict() if entry else None

    def assess(self, uses: tuple[Any, ...]) -> dict[str, Any]:
        """Require explicit sense only for caller-declared MATERIAL ambiguous terms.

        Does not scan prose for terms or upgrade dictionary records into fact evidence.
        """
        resolutions: list[dict[str, Any]] = []
        unresolved: list[dict[str, Any]] = []
        for use in uses:
            term = use.term.strip().casefold()
            entry = self.terms.get(term)
            if entry is None:
                unresolved.append({"term": term, "issue": "term_not_in_reviewed_registry",
                                   "supplied_sense": use.sense_id,
                                   "question": f"Which Merriam-Webster dictionary entry and sense applies to '{term}'?"})
                continue
            candidates = {sense.id: sense for sense in entry.senses}
            if use.sense_id is not None:
                if use.sense_id not in candidates:
                    unresolved.append({"term": term, "issue": "unknown_sense_id",
                                       "supplied_sense": use.sense_id,
                                       "available_senses": sorted(candidates),
                                       "dictionary_url": entry.url,
                                       "question": f"Which listed Merriam-Webster sense of '{term}' did you mean?"})
                    continue
                chosen = candidates[use.sense_id]
            elif len(candidates) == 1:
                chosen = next(iter(candidates.values()))
            else:
                unresolved.append({"term": term, "issue": "material_dictionary_ambiguity",
                                   "available_senses": sorted(candidates), "dictionary_url": entry.url,
                                   "question": f"Which Merriam-Webster sense of '{term}' applies here?"})
                continue
            resolutions.append({"term": term, "sense_id": chosen.id,
                                "operational_gloss": chosen.gloss,
                                "dictionary_url": entry.url,
                                "dictionary_sense_reference": chosen.mw_reference,
                                "resolution_basis": "caller_explicit_sense" if use.sense_id else "only_reviewed_sense"})
        return {"status": "requires_clarification" if unresolved else "resolved",
                "resolved": resolutions, "unresolved": unresolved,
                "source_boundary": "Dictionary sense references are external; glosses are project paraphrases.",
                "not_established": "No automatic determination of context, private intent, or word sense from free text."}

    def discover_in_text(self, text: str, *, material_words: tuple[str, ...] = (),
                         selected_senses: dict[str, str] | None = None) -> dict[str, Any]:
        """Find registered terms; only *declared material* unresolved senses can block.

        Conservative direct-word matching, not an NLP claim about sense. Unknown words
        are outside registry coverage. Dictionary links are not live lookup receipts.
        """
        import re

        if not isinstance(text, str):
            raise ValueError("Text must be a string")
        if not isinstance(material_words, tuple) or not all(isinstance(x, str) and x.strip() for x in material_words):
            raise ValueError("material_words must be a tuple of nonempty strings")
        if selected_senses is not None and (
            not isinstance(selected_senses, dict) or
            not all(isinstance(k, str) and isinstance(v, str) and k.strip() and v.strip()
                    for k, v in selected_senses.items())
        ):
            raise ValueError("selected_senses must map words to their registry sense IDs")
        selected_senses = {k.casefold(): v for k, v in (selected_senses or {}).items()}
        material = {x.strip().casefold() for x in material_words}
        uses = []
        for key, entry in sorted(self.terms.items()):
            for hit in re.finditer(r"(?<!\w)" + re.escape(key) + r"(?!\w)", text, re.IGNORECASE):
                uses.append({
                    "term": key, "start": hit.start(), "end": hit.end(), "exact_span": hit.group(),
                    "source_url": entry.url, "available_sense_ids": [s.id for s in entry.senses],
                    "materiality": "declared_material" if key in material else "not_established",
                    "status": "candidate_not_a_word_sense_decision",
                })
        # Explicitly declared terms absent from the text cannot be assumed to apply.
        absent = sorted(material - {x["term"] for x in uses})
        if absent:
            raise ValueError(f"Material term not found in source text: {absent}")
        # Only narrow, explicitly documented adjacent-phrase patterns can decide
        # an otherwise material sense. Never extend that to arbitrary intention.
        if set(selected_senses) - material:
            raise ValueError("A sense selection requires the corresponding material term")
        auto_basis = {}
        if "context" in material and "context" not in selected_senses:
            # Require the grammatical 'context of ...' construction; reject
            # mixed text/event indicators rather than choose arbitrarily.
            local_texts = [text[c["end"]:min(len(text), c["end"] + 65)].casefold()
                           for c in uses if c["term"] == "context"]
            discourse = any(re.match(r"\s+of\s+(?:this |the |a |an )?(?:paragraph|sentence|text|quote|article|word|passage)\b", fragment)
                            for fragment in local_texts)
            situational = any(re.match(r"\s+of\s+(?:this |the |a |an )?(?:event|incident|situation|meeting|occurrence|setting)\b", fragment)
                              for fragment in local_texts)
            if discourse != situational:
                selected_senses["context"] = "discourse" if discourse else "setting"
                auto_basis["context"] = "transparent_narrow_phrase_pattern_not_general_understanding"
        from .models import MaterialTerm
        lexical = self.assess(tuple(MaterialTerm(term, selected_senses.get(term)) for term in sorted(material)))
        for record in lexical["resolved"]:
            if record["term"] in auto_basis:
                record["resolution_basis"] = auto_basis[record["term"]]
        # The registry contains no review timestamp and does not contain cached
        # copyright-controlled dictionary entries; do not invent one.
        return {
            "status": "requires_clarification" if lexical["unresolved"] else "no_material_ambiguity_identified",
            "candidates": sorted(uses, key=lambda x: (x["start"], x["term"])),
            "declared_material_assessment": lexical,
            "coverage": "ten_reviewed_linked_registry_terms_only_lexical_matching",
            "dictionary_consultation": "offline_registry_links_no_live_dictionary_access",
            "review_date": None,
        }
