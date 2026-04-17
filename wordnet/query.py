from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import (
    Sense,
    Synset,
    Word,
    WordNetData,
)

_STOPWORDS = frozenset(
    w
    for w in """
    a about above after again against all am an and any are aren't as at be
    because been before being below between both but by can't cannot could
    couldn't did didn't do does doesn't doing don't down during each few for
    from further get got had hadn't has hasn't have haven't having he he'd
    he'll he's her here here's hers herself him himself his how how's i i'd
    i'll i'm i've if in into is isn't it it's its itself let's me more most
    mustn't my myself no nor not of off on once only or other ought our ours
    ourselves out over own same shan't she she'd she'll she's should shouldn't
    so some such than that that's the their theirs them themselves then there
    there's these they they'd they'll they're they've this those through to too
    very was wasn't we we'd we'll we're we've were weren't what what's when
    when's where where's which while who who's whom why why's will with won't
    would wouldn't you you'd you'll you're you've your yours yourself yourselves
    also just like even still already really much many well way need use used
    using make makes made know known knows think thinks thought go goes going
    went come comes coming take takes took see sees seen want wants say says
    said one two new first last long great little old big high small
    """.split()
    if w.strip()
)

_POS_MAP = {"n": "noun", "v": "verb", "a": "adj", "r": "adv"}


@dataclass
class ChildWord:
    lemma: str
    pos: str
    gloss: str
    score: float = 0.0


@dataclass
class ParentWord:
    lemma: str
    pos: str
    gloss: str
    score: float = 0.0


class WordNetIndex:
    def __init__(self, data: WordNetData) -> None:
        self.words_by_lemma: dict[str, list[Word]] = {}
        self.word_by_id: dict[int, Word] = {}
        self.senses_by_word_id: dict[int, list[Sense]] = {}
        self.senses_by_synset: dict[tuple[int, str], list[Sense]] = {}
        self.synset_by_key: dict[tuple[int, str], Synset] = {}
        self.children_by_synset: dict[tuple[int, str], list[tuple[int, str]]] = {}
        self.parents_by_synset: dict[tuple[int, str], list[tuple[int, str]]] = {}
        self.morph_map: dict[str, list[str]] = {}

        for w in data.words:
            self.words_by_lemma.setdefault(w.lemma.lower(), []).append(w)
            self.word_by_id[w.id] = w

        for s in data.senses:
            self.senses_by_word_id.setdefault(s.word_id, []).append(s)
            self.senses_by_synset.setdefault(
                (s.synset_offset, s.synset_pos), []
            ).append(s)

        for s in data.synsets:
            self.synset_by_key[(s.offset, s.pos)] = s

        for r in data.semantic_relations:
            if r.relation_type == "~":
                key = (r.from_synset_offset, r.from_synset_pos)
                self.children_by_synset.setdefault(key, []).append(
                    (r.to_synset_offset, r.to_synset_pos)
                )
            if r.relation_type == "@":
                child_key = (r.from_synset_offset, r.from_synset_pos)
                parent_key = (r.to_synset_offset, r.to_synset_pos)
                self.parents_by_synset.setdefault(child_key, []).append(parent_key)

        for m in data.morph_exceptions:
            self.morph_map.setdefault(m.inflected_form.lower(), []).append(
                m.base_form.lower()
            )

    def _resolve_lemma(self, token: str) -> str | None:
        low = token.lower()
        if low in self.words_by_lemma:
            return low
        bases = self.morph_map.get(low)
        if bases:
            return bases[0]
        for candidate in self._suffix_stems(low):
            if candidate in self.words_by_lemma:
                return candidate
        return None

    @staticmethod
    def _suffix_stems(word: str) -> list[str]:
        stems: list[str] = []
        if word.endswith("ing"):
            if len(word) > 5:
                stems.append(word[:-3])
                stems.append(word[:-3] + "e")
            if len(word) > 6 and word[-4] == word[-5]:
                stems.append(word[:-4])
        if word.endswith("ed"):
            if len(word) > 4:
                stems.append(word[:-2])
                stems.append(word[:-1])
            if len(word) > 5 and word[-3] == word[-4]:
                stems.append(word[:-3])
        if word.endswith("ies") and len(word) > 4:
            stems.append(word[:-3] + "y")
        if word.endswith("es") and len(word) > 4:
            stems.append(word[:-2])
            stems.append(word[:-1])
        if word.endswith("s") and not word.endswith("ss") and len(word) > 3:
            stems.append(word[:-1])
        return stems

    def _tokenize(self, text: str) -> list[str]:
        return [t.lower() for t in re.split(r"[^a-zA-Z]+", text) if t.strip()]

    def extract_keywords(self, text: str) -> list[str]:
        tokens = self._tokenize(text)
        seen: set[str] = set()
        keywords: list[str] = []
        for t in tokens:
            if t in _STOPWORDS:
                continue
            lemma = self._resolve_lemma(t)
            if lemma and lemma not in seen:
                seen.add(lemma)
                if self._has_relations(lemma):
                    keywords.append(lemma)
        return keywords

    def _has_relations(self, lemma: str) -> bool:
        words = self.words_by_lemma.get(lemma.lower(), [])
        for w in words:
            for sense in self.senses_by_word_id.get(w.id, []):
                sk = (sense.synset_offset, sense.synset_pos)
                if sk in self.children_by_synset or sk in self.parents_by_synset:
                    return True
        return False

    def _hyponym_words(self, lemma: str) -> list[ChildWord]:
        words = self.words_by_lemma.get(lemma.lower(), [])
        results: list[ChildWord] = []
        seen_lemmas: set[str] = set()

        for w in words:
            for sense in self.senses_by_word_id.get(w.id, []):
                synset_key = (sense.synset_offset, sense.synset_pos)
                for child_key in self.children_by_synset.get(synset_key, []):
                    child_synset = self.synset_by_key.get(child_key)
                    if not child_synset:
                        continue
                    for child_sense in self.senses_by_synset.get(child_key, []):
                        child_word = self.word_by_id.get(child_sense.word_id)
                        if not child_word:
                            continue
                        lk = f"{child_word.lemma}:{child_word.pos}"
                        if lk in seen_lemmas:
                            continue
                        seen_lemmas.add(lk)
                        results.append(
                            ChildWord(
                                lemma=child_word.lemma,
                                pos=_POS_MAP.get(child_word.pos, child_word.pos),
                                gloss=child_synset.gloss,
                            )
                        )
        return results

    def _hypernym_words(self, lemma: str) -> list[ParentWord]:
        words = self.words_by_lemma.get(lemma.lower(), [])
        results: list[ParentWord] = []
        seen_lemmas: set[str] = set()

        for w in words:
            for sense in self.senses_by_word_id.get(w.id, []):
                synset_key = (sense.synset_offset, sense.synset_pos)
                for parent_key in self.parents_by_synset.get(synset_key, []):
                    parent_synset = self.synset_by_key.get(parent_key)
                    if not parent_synset:
                        continue
                    for parent_sense in self.senses_by_synset.get(parent_key, []):
                        parent_word = self.word_by_id.get(parent_sense.word_id)
                        if not parent_word:
                            continue
                        lk = f"{parent_word.lemma}:{parent_word.pos}"
                        if lk in seen_lemmas:
                            continue
                        seen_lemmas.add(lk)
                        results.append(
                            ParentWord(
                                lemma=parent_word.lemma,
                                pos=_POS_MAP.get(parent_word.pos, parent_word.pos),
                                gloss=parent_synset.gloss,
                            )
                        )
        return results

    def _context_tokens(self, text: str) -> set[str]:
        return set(self._tokenize(text)) - _STOPWORDS

    def _keyword_pos_counts(self, keywords: list[str]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for kw in keywords:
            for w in self.words_by_lemma.get(kw.lower(), []):
                counts[w.pos] = counts.get(w.pos, 0) + 1
        return counts

    def _score_child(
        self, child: ChildWord, context_tokens: set[str], pos_counts: dict[str, int]
    ) -> float:
        raw_pos = next((k for k, v in _POS_MAP.items() if v == child.pos), "n")
        score = 0.0

        gloss_tokens = set(self._tokenize(child.gloss))
        overlap = len(context_tokens & gloss_tokens)
        score += float(overlap) * 2.0

        if child.lemma.lower() in context_tokens:
            score += 4.0

        dominant_pos = max(pos_counts, key=pos_counts.get) if pos_counts else "n"
        if raw_pos == dominant_pos:
            score += 3.0

        return score

    def _score_parent(
        self, parent: ParentWord, context_tokens: set[str], pos_counts: dict[str, int]
    ) -> float:
        raw_pos = next((k for k, v in _POS_MAP.items() if v == parent.pos), "n")
        score = 0.0

        gloss_tokens = set(self._tokenize(parent.gloss))
        overlap = len(context_tokens & gloss_tokens)
        score += float(overlap) * 2.0

        if parent.lemma.lower() in context_tokens:
            score += 4.0

        dominant_pos = max(pos_counts, key=pos_counts.get) if pos_counts else "n"
        if raw_pos == dominant_pos:
            score += 3.0

        return score

    def top_children(self, messages: list[dict], top_n: int = 3) -> list[ChildWord]:
        full_context = " ".join(m["content"] for m in messages)
        context_tokens = self._context_tokens(full_context)
        keywords = self.extract_keywords(full_context)
        pos_counts = self._keyword_pos_counts(keywords)

        all_children: list[ChildWord] = []
        seen: set[str] = set()

        for kw in keywords:
            for child in self._hyponym_words(kw):
                key = f"{child.lemma}:{child.pos}"
                if key in seen:
                    continue
                seen.add(key)
                child.score = self._score_child(child, context_tokens, pos_counts)
                if child.score > 0:
                    all_children.append(child)

        all_children.sort(key=lambda c: c.score, reverse=True)
        return all_children[:top_n]

    def top_parents(self, messages: list[dict], top_n: int = 3) -> list[ParentWord]:
        full_context = " ".join(m["content"] for m in messages)
        context_tokens = self._context_tokens(full_context)
        keywords = self.extract_keywords(full_context)
        pos_counts = self._keyword_pos_counts(keywords)

        all_parents: list[ParentWord] = []
        seen: set[str] = set()

        for kw in keywords:
            for parent in self._hypernym_words(kw):
                key = f"{parent.lemma}:{parent.pos}"
                if key in seen:
                    continue
                seen.add(key)
                parent.score = self._score_parent(parent, context_tokens, pos_counts)
                if parent.score > 0:
                    all_parents.append(parent)

        all_parents.sort(key=lambda p: p.score, reverse=True)
        return all_parents[:top_n]

    def top_related(
        self, messages: list[dict], top_n: int = 3
    ) -> tuple[list[ChildWord], list[ParentWord]]:
        return self.top_children(messages, top_n), self.top_parents(messages, top_n)
