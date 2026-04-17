from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import sqlite3


@dataclass
class LexicalDomain:
    id: int
    name: str


@dataclass
class Synset:
    offset: int
    pos: str
    lex_filenum: int
    gloss: str
    is_satellite: bool = False


@dataclass
class Word:
    id: int
    lemma: str
    pos: str


@dataclass
class Sense:
    id: int
    synset_offset: int
    synset_pos: str
    word_id: int
    lex_id: int = 0
    sense_key: str | None = None
    sense_number: int = 0
    tag_count: int = 0


@dataclass
class SemanticRelation:
    from_synset_offset: int
    from_synset_pos: str
    to_synset_offset: int
    to_synset_pos: str
    relation_type: str
    is_lexical: bool = False
    source_sense_id: int | None = None
    target_sense_id: int | None = None


@dataclass
class MorphException:
    id: int
    pos: str
    inflected_form: str
    base_form: str


@dataclass
class VerbFrame:
    id: int
    template: str


@dataclass
class VerbFrameSense:
    sense_id: int
    frame_id: int


@dataclass
class WordNetData:
    lexical_domains: list[LexicalDomain] = field(default_factory=list)
    synsets: list[Synset] = field(default_factory=list)
    words: list[Word] = field(default_factory=list)
    senses: list[Sense] = field(default_factory=list)
    semantic_relations: list[SemanticRelation] = field(default_factory=list)
    morph_exceptions: list[MorphException] = field(default_factory=list)
    verb_frames: list[VerbFrame] = field(default_factory=list)
    verb_frame_senses: list[VerbFrameSense] = field(default_factory=list)


def load_wordnet_db(db_path: str | Path) -> WordNetData:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    data = WordNetData()

    cur.execute("SELECT id, name FROM lexical_domain ORDER BY id")
    data.lexical_domains = [LexicalDomain(r["id"], r["name"]) for r in cur.fetchall()]

    cur.execute("SELECT id, template FROM verb_frame ORDER BY id")
    data.verb_frames = [VerbFrame(r["id"], r["template"]) for r in cur.fetchall()]

    cur.execute("SELECT id, lemma, pos FROM word ORDER BY id")
    data.words = [Word(r["id"], r["lemma"], r["pos"]) for r in cur.fetchall()]

    cur.execute(
        "SELECT offset, pos, lex_filenum, gloss, is_satellite FROM synset ORDER BY offset, pos"
    )
    data.synsets = [
        Synset(
            r["offset"], r["pos"], r["lex_filenum"], r["gloss"], bool(r["is_satellite"])
        )
        for r in cur.fetchall()
    ]

    cur.execute(
        "SELECT id, synset_offset, synset_pos, word_id, lex_id, sense_key, sense_number, tag_count FROM sense ORDER BY id"
    )
    data.senses = [
        Sense(
            r["id"],
            r["synset_offset"],
            r["synset_pos"],
            r["word_id"],
            r["lex_id"],
            r["sense_key"],
            r["sense_number"],
            r["tag_count"],
        )
        for r in cur.fetchall()
    ]

    cur.execute(
        "SELECT from_synset_offset, from_synset_pos, to_synset_offset, to_synset_pos, relation_type, is_lexical, source_sense_id, target_sense_id FROM semantic_relation"
    )
    data.semantic_relations = [
        SemanticRelation(
            r["from_synset_offset"],
            r["from_synset_pos"],
            r["to_synset_offset"],
            r["to_synset_pos"],
            r["relation_type"],
            bool(r["is_lexical"]),
            r["source_sense_id"],
            r["target_sense_id"],
        )
        for r in cur.fetchall()
    ]

    cur.execute(
        "SELECT id, pos, inflected_form, base_form FROM morph_exception ORDER BY id"
    )
    data.morph_exceptions = [
        MorphException(r["id"], r["pos"], r["inflected_form"], r["base_form"])
        for r in cur.fetchall()
    ]

    cur.execute("SELECT sense_id, frame_id FROM verb_frame_sense")
    data.verb_frame_senses = [
        VerbFrameSense(r["sense_id"], r["frame_id"]) for r in cur.fetchall()
    ]

    conn.close()
    return data
