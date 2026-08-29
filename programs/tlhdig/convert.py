"""The Text-Fabric director (plan §7.7).

Walks each AOxml document and issues `cv` actions.  The node ontology follows plan §3.2:
`sign` is the slot type, with `word`, `line`, `column`, `surface` and `document` as the
containment spine, and `analysis`, `cluster`, `note` and `edit` as overlays.

Two policies are parameters rather than assumptions:

* `keep_empty` -- whether contentless tokens become slots.  Milestone 0 decides this
  from a benchmark, not from taste (plan §8.0).
* `patches` -- the repair manifest, applied in memory; source files are never rewritten.
"""

from __future__ import annotations

import re
from pathlib import Path

import lxml.etree as LE

from . import brackets as B
from . import lineref, morph, repair, signs, source
from . import SOURCE_VERSION, TF_VERSION
from .featuremeta import DESCRIPTIONS
from .paths import ENCRYPTED

SLOT_TYPE = "sign"

OTEXT = {
    "sectionTypes": "document,column,line",
    "sectionFeatures": "docid,collabel,lnno",
    # TF requires a default format named text-orig-full; the names also match BHSA
    # and the Nino-cunei corpora, so existing tooling recognises them.
    "fmt:text-orig-full": "{srcxml}{after}",     # source-faithful, markers in place
    "fmt:text-orig-plain": "{sym}{after}",       # clean transliteration
    "fmt:line#text-cuneiform": "{cu} ",
}

GENERIC = {
    "name": "TLHdig",
    "title": "Thesaurus Linguarum Hethaeorum digitalis",
    "sourceVersion": SOURCE_VERSION,
    "version": TF_VERSION,
    "sourceDoi": "10.5281/zenodo.20328284",
    "sourceLicense": "CC-BY-4.0",
    "language": "hit",
}

INT_FEATURES = {
    "ln", "index", "sgr", "agr", "det", "num", "space_count", "nanalyses",
    "cu_pua", "cu_broken", "start_offset", "end_offset", "order", "nrecords",
    "parse_ok", "materlect_anomalous", "srcln", "anchor",
}

_CTH_DIR = re.compile(r"^CTH ([^_]+)_XML_(.+)$")
_AO = "{http://hethiter.net/ns/AO/1.0}"

# <meta> children that are editorial events rather than structure.
_EDIT_KINDS = {
    "kor", "kor2", "kor1kf", "annot", "uebern", "format", "author", "kolon",
    "val", "trlst", "join", "merge", "aufheb", "aufloes", "korof", "koltaf",
    "kolfot", "kolfot2", "cth", "creation-date", "AOxml-creation",
}
_EDIT_ATTRS = ("editor", "date", "part", "src", "frgm", "docs", "comment",
               "author", "alt", "neu")


def _text(el) -> str:
    return "".join(el.itertext())


def director(cv, files, corpus_root: Path, keep_empty: bool, patches):
    for path in files:
        rel = path.relative_to(corpus_root).as_posix()
        if rel == ENCRYPTED:
            continue
        data = path.read_bytes()
        entry = patches.get(rel)
        if entry:
            try:
                data = repair.apply(data, entry[1], expect_sha=entry[0])
            except repair.PatchError:
                continue
        try:
            spans = source.scan(data)
            root = LE.fromstring(data)
        except Exception:
            continue

        _document(cv, root, spans, data, rel, keep_empty)

    # Declare metadata only for features that actually occur: TF rejects an intFeatures
    # entry for a feature the walk never produced, which would make the converter fail
    # on any subset of the corpus.
    for feat in cv.features():
        meta = {
            "description": DESCRIPTIONS.get(feat, "(undocumented)"),
            "valueType": "int" if feat in INT_FEATURES else "str",
        }
        cv.meta(feat, **meta)


_STRIP_TAGS = re.compile(rb"<[^>]*>")


def _has_readable_sign(data: bytes, w_spans) -> bool:
    """Cheap pre-scan: will this document yield any non-empty token?

    Stripping tags from each <w> and looking for a character that is not a separator
    is far cheaper than tokenising twice, and it only has to be right about whether
    the count is zero.
    """
    for sp in w_spans:
        inner = source.inner_bytes(data, sp)
        if _STRIP_TAGS.sub(b"", inner).translate(None, b"-. \t\r\n").strip():
            return True
    return False


def _document(cv, root, spans, data, rel, keep_empty):
    parts = rel.split("/")
    m = _CTH_DIR.match(parts[0])
    cth, subcorpus = (m.group(1), m.group(2)) if m else ("", "")

    docid = (root.findtext("AOHeader/docID") or Path(rel).stem).strip()
    text_el = root.find("body/div1/text")
    if text_el is None:
        return

    doc = cv.node("document")
    lang = text_el.get("{http://www.w3.org/XML/1998/namespace}lang", "")
    cv.feature(
        doc,
        docid=docid, docid_raw=docid, cth=cth, subcorpus=subcorpus,
        src_file=rel, lang_raw=lang,
    )
    # XXXlang means unset; TF encodes absence by omitting the value (plan §5.3)
    if lang and lang != "XXXlang":
        cv.feature(doc, lang=lang)

    edits = []
    for order, ev in enumerate(root.iterfind("AOHeader/meta/*")):
        tag = LE.QName(ev).localname if not isinstance(ev.tag, str) else ev.tag
        if tag not in _EDIT_KINDS:
            continue
        edits.append((tag, order, {a: ev.get(a) for a in _EDIT_ATTRS if ev.get(a)}))

    # Pair each <w> element with its byte span.  source.scan and lxml both walk the
    # document in order, so the nth <w> in one is the nth in the other; that is the
    # join between the byte layer (Contract A) and the structural layer.
    w_spans = [sp for sp in spans if sp.tag == "w"]
    w_seen = 0

    state = _State(cv, keep_empty)

    # 249 documents contain no readable sign at all -- wholly broken tablets whose
    # every <w> is contentless.  TF deletes unlinked nodes, so without an anchor the
    # document, its lines and its editorial history all disappear and a document count
    # comes out wrong.  Nino-cunei sets the precedent of an artificial empty slot.
    # It is emitted inside the first line, not before it: a slot outside every line
    # leaves the line nodes unlinked, TF deletes them, and the section computation
    # then fails outright on the missing level.
    state.needs_anchor = not _has_readable_sign(data, w_spans)

    for node in text_el.iter():
        tag = node.tag
        if not isinstance(tag, str):
            continue
        if tag == "lb":
            state.start_line(node)
        elif tag == "w":
            sp = w_spans[w_seen] if w_seen < len(w_spans) else None
            w_seen += 1
            state.word(node, data, sp)
        elif tag in ("parsep", "parsep_dbl"):
            state.close_paragraph(double=tag.endswith("dbl"))
        elif tag == "clb":
            state.start_colon(node)
    state.finish()

    # Editorial events carry no text of their own.  TF deletes unlinked nodes -- and
    # in 13.1.0 crashes while doing so when the node has edges (walker.py:1424 iterates
    # an edge dict without .items()).  So they are anchored to the document's first
    # slot; the `edits` edge carries the real relation.
    anchor = {state.slots[0]} if state.slots else None
    if anchor:
        for tag, order, attrs in edits:
            e = cv.node("edit", slots=anchor)
            cv.feature(e, kind=tag, order=order)
            for a, v in attrs.items():
                cv.feature(e, **{a: v})
            cv.terminate(e)
            cv.edge(e, doc, edits=None)

    cv.terminate(doc)


class _State:
    """Tracks the open line / column / surface / paragraph / colon while walking."""

    def __init__(self, cv, keep_empty: bool):
        self.cv = cv
        self.keep_empty = keep_empty
        self.surface = self.column = self.line = None
        self.paragraph = self.colon = None
        self.collabel = None
        self.surface_label = None
        self.brackets = B.Tracker()
        self.line_no = 0
        self.sign_idx = 0
        self.words_in_para = 0
        self.slots: list[int] = []
        self.pending_layouts: list[dict] = []
        self.needs_anchor = False

    # ---------------------------------------------------------------- structure
    def start_line(self, node):
        ref = lineref.parse(node.get("lnr"))
        cv = self.cv
        if ref.collabel != self.collabel:
            self._close(("line", "colon", "paragraph", "column"))
            surface_label = ref.surface or ""
            if surface_label != self.surface_label:
                self._close(("surface",))
                self.surface = cv.node("surface")
                cv.feature(self.surface, surface=surface_label)
                self.surface_label = surface_label
            self.column = cv.node("column")
            cv.feature(
                self.column,
                column=ref.column, collabel=ref.collabel or ref.surface or "-",
                frag=ref.frag,
            )
            self.collabel = ref.collabel
        else:
            self._close(("line",))

        if self.paragraph is None:
            self.paragraph = cv.node("paragraph")

        self.line_no += 1
        self.line = cv.node("line")
        cv.feature(
            self.line,
            lnr=ref.raw, lnno=ref.lnno or ref.raw.strip(), prime=ref.prime,
            linetail=ref.tail, txtid=node.get("txtid", ""), srcln=self.line_no,
        )
        if ref.ln is not None:
            cv.feature(self.line, ln=ref.ln)
        for a, f in (("lg", "lang"), ("cu", "cu"), ("cuDirty", "cudirty")):
            v = node.get(a)
            if v:
                cv.feature(self.line, **{f: v})
        cu = node.get("cu") or ""
        if cu:
            cv.feature(
                self.line,
                cu_broken=cu.count("▒"),
                cu_pua=sum(1 for c in cu if 0xF0000 <= ord(c) <= 0x10FFFD),
            )
        if self.needs_anchor and not self.slots:
            a = cv.slot()
            cv.feature(a, srcxml="", sym="", after="", type="empty", anchor=1)
            self.slots.append(a[1])
            for feats in self.pending_layouts:
                self._emit_layout(feats, a[1])
            self.pending_layouts.clear()

        self.brackets.start_line(self.line_no)

    def close_paragraph(self, double: bool = False):
        cv = self.cv
        if self.paragraph is not None:
            cv.feature(self.paragraph, ruling="double" if double else "single")
            cv.terminate(self.paragraph)
            self.paragraph = None

    def start_colon(self, node):
        cv = self.cv
        if self.colon is not None:
            cv.terminate(self.colon)
        self.colon = cv.node("colon")
        for a in ("id", "nr", "lg"):
            v = node.get(a)
            if v:
                cv.feature(self.colon, **{"lang" if a == "lg" else a: v})

    # -------------------------------------------------------------------- words
    def word(self, node, data, sp):
        cv = self.cv
        inner = source.inner_bytes(data, sp) if sp is not None else b""
        toks = signs.tokenise_word(inner)
        keep = [t for t in toks if self.keep_empty or t.type != "empty"]
        if not keep:
            # A <w> holding only layout or markers is not a sign, but it is not
            # nothing either: dropping it would lose 403,169 source elements while
            # claiming Contract B holds.  It becomes a `layout` node anchored to the
            # most recent slot, keeping its space count and its byte span.
            for t in toks:
                for tagname, _off in t.markers:
                    B.feed(self.brackets, tagname, self.sign_idx)
            if toks:
                feats = {}
                total_space = sum(t.space_count for t in toks)
                if total_space:
                    feats["space_count"] = total_space
                marks = [tag for t in toks for tag, _ in t.markers]
                if marks:
                    feats["markers"] = " ".join(marks)
                if sp is not None:
                    feats["src_span"] = f"{sp.outer_start}-{sp.outer_end}"
                if self.slots:
                    self._emit_layout(feats, self.slots[-1])
                else:
                    # nothing to anchor to yet; a line commonly opens with an indent
                    self.pending_layouts.append(feats)
            return

        if self.line is None:
            return
        w = cv.node("word")
        trans = node.get("trans")
        if trans is not None:
            cv.feature(w, trans=trans)
        if sp is not None:
            cv.feature(w, src_span=f"{sp.outer_start}-{sp.outer_end}")

        word_slots = []
        for t in keep:
            self.sign_idx += 1
            s = cv.slot()
            # cv.slot() returns a node *reference* (nType, seq); cv.node(slots=...)
            # wants the raw slot numbers, so keep the sequence part.
            word_slots.append(s[1])
            self.slots.append(s[1])
            if self.pending_layouts:
                for feats in self.pending_layouts:
                    self._emit_layout(feats, s[1])
                self.pending_layouts.clear()
            cv.feature(
                s, srcxml=t.srcxml, sym=t.sym, after=t.after, type=t.type,
                sgr=t.sgr, agr=t.agr, det=t.det, num=t.num,
            )
            if t.space_count:
                cv.feature(s, space_count=t.space_count)
            for f in ("corr", "subscr", "materlect", "surplus"):
                v = getattr(t, f)
                if v:
                    cv.feature(s, **{f: v})
            if t.materlect and set(t.materlect) <= set("!?"):
                cv.feature(s, materlect_anomalous=1)
            for tagname, _off in t.markers:
                B.feed(self.brackets, tagname, self.sign_idx)
            for fam in self.brackets.active():
                cv.feature(s, **{{"del": "missing"}.get(fam, fam): 1})

        got = morph.analyses(node.attrib)
        sel = morph.parse_selection(node.get("mrp0sel"))
        cv.feature(w, nanalyses=len(got), mrpsel=sel.raw.strip(), mrpsel_kind=sel.kind)
        if sel.base_alt:
            cv.feature(w, sel_base=sel.base_alt)
        if sel.clitic_alt:
            cv.feature(w, sel_clitic=sel.clitic_alt)
        if sel.group:
            cv.feature(w, sel_group=sel.group)

        for a in got:
            # An analysis covers the same slots as its word, so it is never unlinked.
            an = cv.node("analysis", slots=set(word_slots))
            cv.feature(
                an, index=a.index, sep=a.sep.strip(),
                parse_ok=1 if a.ok else 0,
                lemma=a.base.lemma, gloss=a.base.gloss, morph=a.base.morph,
                stemclass_raw=a.base.stemclass, field4_kind=a.field4_kind,
                det_hint=a.base.det,
            )
            if not a.ok:
                # The parsed fields reconstruct the source string for 1,476,740 of
                # 1,611,354 analyses but not exactly for the rest (trailing empty
                # fields), so `raw` is kept wherever the parse is incomplete.  For the
                # others the verbatim string stays recoverable through the word's
                # src_span, which is the Contract A guarantee -- storing all 1.6M
                # strings as well cost 175 MB for no extra information.
                cv.feature(an, raw=a.raw)
            if a.field4_kind == "pos":
                cv.feature(an, pos=a.pos)
            elif a.field4_kind == "stemclass":
                cv.feature(an, stemclass=a.base.stemclass.strip())
            if a.clitic is not None:
                cv.feature(
                    an, clitic_lemma=a.clitic.lemma, clitic_morph=a.clitic.morph,
                    clitic_stemclass=a.clitic.stemclass, clitic_det=a.clitic.det,
                )
            cv.terminate(an)
            cv.edge(w, an, analyses=None)
            if sel.kind == "analysis" and sel.index == a.index:
                cv.edge(w, an, selected=sel.base_alt or None)

        cv.terminate(w)
        self.words_in_para += 1

    def _emit_layout(self, feats: dict, slot: int) -> None:
        lay = self.cv.node("layout", slots={slot})
        if feats:
            self.cv.feature(lay, **feats)
        self.cv.terminate(lay)

    # ------------------------------------------------------------------- finish
    def _close(self, kinds):
        for k in kinds:
            n = getattr(self, k, None)
            if n is not None:
                self.cv.terminate(n)
                setattr(self, k, None)
        if "column" in kinds:
            self.collabel = None

    def finish(self):
        if self.needs_anchor and not self.slots:
            # a document with no <lb> at all
            a = self.cv.slot()
            self.cv.feature(a, srcxml="", sym="", after="", type="empty", anchor=1)
            self.slots.append(a[1])
        self.brackets.finish()
        self.close_paragraph()
        self._close(("line", "colon", "paragraph", "column", "surface"))


def build(corpus_root: Path, out_dir: Path, keep_empty: bool = False,
          files=None, patches=None, silent: str = "deep"):
    """Run the conversion.  Returns a loaded TF api, or None on failure."""
    from tf.convert.walker import CV
    from tf.fabric import Fabric

    corpus_root = Path(corpus_root)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if files is None:
        files = sorted(corpus_root.rglob("*.xml"), key=lambda p: str(p).lower())
    patches = patches or {}

    TF = Fabric(locations=str(out_dir), silent=silent)
    cv = CV(TF, silent=silent)
    good = cv.walk(
        lambda c: director(c, files, corpus_root, keep_empty, patches),
        SLOT_TYPE,
        otext=OTEXT,
        generic=GENERIC,
        intFeatures=set(),      # set dynamically in the director, see above
        featureMeta={},
        warn=False,
    )
    if not good:
        return None
    TF2 = Fabric(locations=str(out_dir), silent=silent)
    api = TF2.loadAll(silent=silent)
    # loadAll returns the api on success, but a bare bool in some configurations;
    # fall back to the Fabric's own api handle so callers always get one object.
    if api is True or api is False:
        api = getattr(TF2, "api", None) if api else None
    return api
