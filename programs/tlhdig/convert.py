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
import unicodedata
from pathlib import Path

import lxml.etree as LE
from xml.parsers import expat

from . import brackets as B
from .tags import DESTINATION as TAG_DESTINATION
from . import cuneiform, lineref, morph, repair, signs, source
from . import SOURCE_VERSION, TF_VERSION
from .featuremeta import DESCRIPTIONS
from .paths import ENCRYPTED, PROGRAMS, rel as rel_key

SLOT_TYPE = "sign"

# U+2592 MEDIUM SHADE: the cuneiform writes one per unreadable sign.
PLACEHOLDER = "\u2592"


class Ledger:
    """Accounting for every source file (plan §8.3).

    The conversion loop used to swallow patch and parse failures with a bare
    `continue`, so 52 documents vanished while the build reported success.  Every
    file must now end in exactly one outcome, and `balances()` says whether it did.
    """

    # A stale patch hash means the manifest and the corpus disagree. That is a build
    # error, never an acceptable exclusion.
    FATAL = frozenset({"patch_failed"})

    # Markers fed to the bracket tracker vs endpoints actually emitted, per family.
    # Discovering a shortfall from an external gate cost a 30-minute build per round;
    # this makes the same question answerable during the walk.
    marker_fed: dict = None
    marker_out: dict = None
    marker_lost: list = None
    marker_src: dict = None

    def __init__(self, allow=None):
        self.total = 0
        self.converted = 0
        self.excluded_reasons: dict[str, int] = {}
        self.excluded_files: list[tuple[str, str]] = []
        self.marker_fed = {}
        self.marker_out = {}
        self.marker_lost = []
        self.marker_src = {}
        # The exclusion set of an immutable release is known, so the build checks
        # membership rather than arithmetic: balancing alone would wave through a
        # regression that broke another 500 documents.  The *reason* is compared too --
        # a file that was `unparseable` and starts failing as `no_text_element` is a
        # change in behaviour, not a known exclusion.
        if isinstance(allow, dict):
            self.allow = dict(allow)
        else:
            self.allow = {rel: None for rel in (allow or ())}

    def exclude(self, rel: str, reason: str) -> None:
        self.excluded_reasons[reason] = self.excluded_reasons.get(reason, 0) + 1
        self.excluded_files.append((rel, reason))

    def balances(self) -> bool:
        return self.total == self.converted + sum(self.excluded_reasons.values())

    def unexpected(self) -> list[str]:
        """Excluded files that are not on the allowlist, or excluded fatally."""
        bad = []
        for rel, reason in self.excluded_files:
            if reason in self.FATAL or rel not in self.allow:
                bad.append(rel)
                continue
            expect = self.allow[rel]
            if expect is not None and expect != reason:
                bad.append(rel)
        return sorted(bad)

    def allowed(self) -> bool:
        return self.balances() and not self.unexpected()

    def note_markers(self, rel: str, src: dict, fed: dict, out: dict) -> None:
        """Record one document's marker counts in pipeline order: XML, fed, emitted.

        The parameters are ordered the way the data flows.  An earlier signature put
        the source count last and optional, which reads as an afterthought when it is
        the only count that says whether the XML survived at all.
        """
        for k, v in src.items():
            self.marker_src[k] = self.marker_src.get(k, 0) + v
        for k, v in fed.items():
            self.marker_fed[k] = self.marker_fed.get(k, 0) + v
        for k, v in out.items():
            self.marker_out[k] = self.marker_out.get(k, 0) + v
        if (src != fed or fed != out) and len(self.marker_lost) < 200:
            self.marker_lost.append((rel, dict(src), dict(fed), dict(out)))

    def marker_report(self) -> str:
        """source -> fed -> emitted, the three counts the build gate compares.

        The table used to show only fed and emitted, so the column carrying the claim
        -- that nothing is lost between the XML and the graph -- was the one column a
        reader could not see.
        """
        keys = sorted(set(self.marker_src) | set(self.marker_fed) | set(self.marker_out))
        lines = ["damage markers, source -> fed -> emitted:"]
        for k in keys:
            s = self.marker_src.get(k, 0)
            a = self.marker_fed.get(k, 0)
            b = self.marker_out.get(k, 0)
            flag = "" if s == a == b else f"   LOST {s - b}"
            lines.append(f"  {k:<12} src {s:>8,}  fed {a:>8,}  emitted {b:>8,}{flag}")
        if self.marker_lost:
            lines.append(f"  first divergent documents ({len(self.marker_lost)} shown):")
            for rel, src, fed, out in self.marker_lost[:6]:
                lines.append(f"    {rel}\n       src {src}\n       fed {fed}\n       out {out}")
        return "\n".join(lines)

    def report(self) -> str:
        lines = [f"source files : {self.total:,}", f"  converted  : {self.converted:,}"]
        for r, n in sorted(self.excluded_reasons.items(), key=lambda x: -x[1]):
            lines.append(f"  {r:<11}: {n:,}")
        lines.append("  BALANCES" if self.balances() else "  *** DOES NOT BALANCE ***")
        bad = self.unexpected()
        if bad:
            lines.append(f"  *** {len(bad)} EXCLUSION(S) NOT ON THE ALLOWLIST ***")
            lines.extend(f"      {r}" for r in bad[:10])
        return "\n".join(lines)

OTEXT = {
    "sectionTypes": "document,column,line",
    "sectionFeatures": "docid,collabel,lnno",
    # TF requires a default format named text-orig-full; the names also match BHSA
    # and the Nino-cunei corpora, so existing tooling recognises them.
    # `text-orig-full` is TF's required default format, so it must reference only
    # features the main dataset carries.  It used to be `{srcxml}{after}` -- the
    # source-faithful form with editorial brackets in place -- but `srcxml` now lives in
    # the provenance module, and a format naming an absent feature is not a warning:
    # `loadAll` dies with `KeyError: 'srcxml'` (tf/core/fabric.py:416).  The main dataset
    # has to load on its own.
    #
    # The bracketed rendering is not lost. Load the provenance module and the format
    # below works, or rebuild it from `cluster` boundaries -- which is where the plan
    # says rich rendering belongs anyway (§3.5), rather than in a cached string.
    "fmt:text-orig-full": "{sym}{after}",        # clean transliteration, the default
    "fmt:text-orig-plain": "{sym}{after}",
    # The node-type prefix belongs on the TEMPLATE, not the format name: TF's
    # Text.splitFormat splits the template on "#" (tf/core/text.py:1225).  Declared the
    # other way round -- `fmt:line#text-cuneiform={cu}` -- the name keeps the prefix, the
    # descend type stays `sign`, and TF evaluates {cu} on signs, which have none: every
    # line rendered as a run of spaces.  Measured, not assumed.
    "fmt:text-cuneiform": "line#{cu} ",
    # `text-trans-full` pairs with `text-orig-full` under the `-orig-`/`-trans-` naming
    # that Context-Fabric's describe_text_formats looks for; without a pair it reports
    # "no orig/trans pairs defined" and an agent told to call get_text_formats() before
    # a lexical search learns nothing (measured against cfabric 0.1.7).
    #
    # It is NOT cuneiform-vs-romanisation: this corpus is transliteration throughout, and
    # `cu` exists only on `line`, while the sampler walks slots.  The pair is the source's
    # own notation with editorial brackets and damage marks (`[ya`) against the clean
    # reading (`ya`) -- which is the encoding distinction a query author actually needs.
    # No `-trans-` counterpart is declared any more.  Context-Fabric pairs `-orig-X`
    # with `-trans-X` to show an agent how text is encoded, and with `srcxml` gone the
    # only slot-level string left is `sym`: a pair would show the same value twice,
    # which is worse than no pair. Loading the provenance module restores a real one.
}

# `license` is the licence of *this dataset*, not of the source.  A Text-Fabric build
# of TLHdig is an adaptation of a CC-BY-4.0 work, so it inherits CC-BY-4.0 and cannot be
# redistributed under the repository's MIT code licence.  Stating it in every .tf file
# keeps the dataset self-describing once it is detached from the repo -- which is how
# Agora and cfabric consume it.
GENERIC = {
    "name": "TLHdig",
    "title": "Thesaurus Linguarum Hethaeorum digitalis",
    "sourceVersion": SOURCE_VERSION,
    "version": TF_VERSION,
    "sourceDoi": "10.5281/zenodo.20328284",
    "sourceLicense": "CC-BY-4.0",
    "license": "CC-BY-4.0",
    "attribution": (
        "Derived from TLHdig 0.3 (Hethitologie-Portal Mainz), CC-BY-4.0. "
        "Cite the source dataset, doi:10.5281/zenodo.20328284, not this conversion."
    ),
    "language": "hit",
}

INT_FEATURES = {
    "ln", "index", "sgr", "agr", "det", "num", "space_count", "nanalyses",
    "cu_pua", "cu_broken", "start_offset", "end_offset", "order", "nrecords", "nselected",
    "cu_aligned", "cu_nsigns",
    "noccs",
    "crossesline", "nested", "width", "from_open_marker", "from_close_marker",
    # induced damage flags on signs
    "missing", "laes", "ras", "add", "quot",
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


def director(cv, files, corpus_root: Path, keep_empty: bool, patches, ledger):
    # docid is *manuscript* identity, not record identity: a Sammeltafel such as
    # KUB 26.71 is edited under CTH 1, 18 and 39.6, so 141 docids cover more than one
    # document node.  A docgroup expresses "these claim the same tablet" without
    # asserting the editions are equivalent -- and keeps the record itself primary.
    groups: dict[str, list] = {}
    # (lemma, gloss) -> [analysis nodes].  A lexeme spans documents, so this has to be
    # accumulated across the whole walk, like docgroup.
    lexemes: dict[tuple[str, str], list] = {}
    for path in files:
        # paths.rel() and nothing else: it normalises to NFC, and the manifests are
        # keyed that way.  An inline relative_to() here produced NFD on macOS, so a
        # repaired file's patch was never found and it silently became unparseable.
        rel = rel_key(path, corpus_root)
        ledger.total += 1
        if rel == ENCRYPTED:
            ledger.exclude(rel, "encrypted")
            continue
        data = path.read_bytes()
        entry = patches.get(rel)
        omap = None
        if entry:
            try:
                omap = repair.OffsetMap(data, entry[1])
                data = repair.apply(data, entry[1], expect_sha=entry[0])
            except repair.PatchError as e:
                ledger.exclude(rel, "patch_failed")
                continue
        try:
            spans = source.scan(data)
            root = LE.fromstring(data)
        except (expat.ExpatError, LE.XMLSyntaxError, ValueError) as e:
            # Narrow on purpose.  A bare `except Exception` here turned any regression in
            # source.scan() -- an IndexError, a TypeError -- into the *expected*
            # exclusion reason for a file already on the allowlist, so the ledger
            # accepted it and the build stayed green.  ValueError is included because
            # source.scan raises it for an unterminated tag, which is malformed input.
            ledger.exclude(rel, "unparseable")
            del e
            continue

        made = _document(cv, root, spans, data, rel, keep_empty, omap, groups, ledger,
                         lexemes)
        if made:
            ledger.converted += 1
        else:
            ledger.exclude(rel, "no_text_element")

    for docid, records in sorted(groups.items()):
        slots = set()
        for _node, first in records:
            if first is not None:
                slots.add(first)
        if not slots:
            continue
        g = cv.node("docgroup", slots=slots)
        cv.feature(g, docid=docid, nrecords=len(records))
        cv.terminate(g)
        for node, _first in records:
            cv.edge(node, g, edition=None)

    # The lexical layer.  A `lex` node is one (lemma, gloss) pair -- one sense of one
    # lemma -- and `analysis --lexeme--> lex` ties every occurrence to it.  2,670 lemmas
    # are genuinely polysemous (LUGAL: Koenig / Koenig werden / Koenigtum / koeniglicher
    # Status), so the gloss is part of the key rather than a label on it.
    #
    # `oslots` here is an ANCHOR, not an extent: a lex node covers one slot of its first
    # occurrence, and the attestations are reached through the `lexeme` edge. Giving it
    # the union of its occurrences would be the BHSA semantics, but a lexeme's slots are
    # scattered across the corpus rather than contiguous, so oslots could not range-encode
    # them and would grow by millions of entries. The `fragment` extent is a union
    # because its lines *are* contiguous; this one is not. Do not read containment off it.
    for (lemma_v, gloss_v), analysis_nodes in sorted(lexemes.items()):
        first = None
        for an in analysis_nodes:
            slots = cv.linked(an)
            if slots:
                first = min(slots)
                break
        if first is None:
            continue
        lx = cv.node("lex", slots={first})
        cv.feature(lx, lemma=lemma_v, noccs=len(analysis_nodes))
        if gloss_v:
            cv.feature(lx, gloss=gloss_v)
        cv.terminate(lx)
        for an in analysis_nodes:
            cv.edge(an, lx, lexeme=None)

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


def _manuscripts(cv, text_el, doc, state) -> None:
    """Record the witness apparatus: sigla, inventory numbers and joins.

    <AO:Manuscripts> lists each constituent manuscript of a composite text with the
    `€n` siglum that lb/@lnr then references, so this is what makes a line's witness
    recoverable.  It was not processed at all before.
    """
    block = text_el.find(f"{_AO}Manuscripts")
    if block is None:
        return
    direct, indirect, invnr = [], [], []
    for child in block:
        tag = child.tag
        if not isinstance(tag, str):
            continue
        name = tag.replace(_AO, "")
        txt = _text(child).strip()
        if name == "TxtPubl":
            siglum = (child.get("nr") or "").strip()
            state.fragments[siglum or txt] = (siglum, txt)
        elif name == "InvNr":
            invnr.append(txt)
        elif name == "DirectJoin":
            direct.append(txt)
        elif name == "InDirectJoin":
            indirect.append(txt)
    if direct:
        cv.feature(doc, directjoin=" | ".join(direct))
    if indirect:
        cv.feature(doc, indirectjoin=" | ".join(indirect))
    if invnr:
        cv.feature(doc, invnr=" | ".join(invnr))


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


def _document(cv, root, spans, data, rel, keep_empty, omap=None, groups=None,
              ledger=None, lexemes=None):
    parts = rel.split("/")
    m = _CTH_DIR.match(parts[0])
    cth, subcorpus = (m.group(1), m.group(2)) if m else ("", "")

    docid = (root.findtext("AOHeader/docID") or Path(rel).stem).strip()
    text_el = root.find("body/div1/text")
    if text_el is None:
        return False

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
    # `meta//*` not `meta/*`: <annotation> wraps the annot events and <neu> wraps
    # others, so iterating only direct children missed a third of all events
    # (36,850 vs 24,494 over a 6,000-file sample).
    for order, ev in enumerate(root.iterfind("AOHeader/meta//*")):
        tag = LE.QName(ev).localname if not isinstance(ev.tag, str) else ev.tag
        if tag not in _EDIT_KINDS:
            continue
        edits.append((tag, order, {a: ev.get(a) for a in _EDIT_ATTRS if ev.get(a)}))

    # Pair each <w> element with its byte span.  Both sides must describe the *same*
    # sequence, which needs two filters that ordinal counting alone got wrong:
    #
    #  * 427 <w> spans in 30 files sit outside <text>, under <div1>.  Counting all
    #    spans in the file shifted every pairing after the first stray one, so words
    #    were tokenised from a different word's bytes.
    #  * 235 <w> sit inside another <w>.  The outer word's bytes already contain them,
    #    so feeding both double-counted 108 open and 107 close markers.
    text_span = next(
        (sp for sp in spans if sp.tag == "text" and sp.inner_start is not None), None
    )
    w_all = [sp for sp in spans if sp.tag == "w"]
    if text_span is not None:
        w_all = [
            sp
            for sp in w_all
            if text_span.inner_start <= sp.outer_start < text_span.inner_end
        ]
    w_spans = []
    for sp in w_all:
        if any(
            o is not sp and o.outer_start <= sp.outer_start and sp.outer_end <= o.outer_end
            for o in w_all
        ):
            continue                      # nested inside another <w>
        w_spans.append(sp)
    w_seen = 0

    # Per-line lookahead for the bracket tracker: a range survives the line boundary
    # only when the *next* line opens with a matching close (plan §6).
    per_line: list[list[str]] = []
    cur_line: list[str] | None = None
    for node in text_el.iter():
        t = node.tag
        if not isinstance(t, str):
            continue
        if t == "lb":
            cur_line = []
            per_line.append(cur_line)
        elif cur_line is not None and (t in B.OPEN or t in B.CLOSE):
            cur_line.append(t)
    leading_close = [
        frozenset({B.CLOSE[ln[0]]}) if ln and ln[0] in B.CLOSE else frozenset()
        for ln in per_line
    ]

    state = _State(cv, keep_empty, omap, lexemes)
    _manuscripts(cv, text_el, doc, state)

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
            hint = (
                leading_close[state.line_no]
                if state.line_no < len(leading_close)
                else frozenset()
            )
            state.start_line(node, hint)
        elif tag == "w":
            if any(a.tag == "w" for a in node.iterancestors()):
                continue                  # covered by the enclosing word's bytes
            sp = w_spans[w_seen] if w_seen < len(w_spans) else None
            w_seen += 1
            state.word(node, data, sp)
        elif (tag in B.OPEN or tag in B.CLOSE) and not any(
            a.tag == "w" for a in node.iterancestors()
        ):
            # A marker directly under <text>, not inside any word: 647+ of these were
            # dropped because only tokenised words fed the tracker.
            state.stray_marker(tag)
        elif tag in ("parsep", "parsep_dbl"):
            state.close_paragraph(double=tag.endswith("dbl"))
        elif tag == "clb":
            state.start_colon(node)
        elif tag == "note" and not any(a.tag == "w" for a in node.iterancestors()):
            # 419 notes sit outside any <w>: 398 directly under <text>, the rest under
            # AO:Manuscripts or a stray formatting wrapper.  Only tokenised words fed
            # the note collector, so these were never seen at all.
            state.stray_note(node.attrib)
    state.finish()

    # Damage ranges become nodes.  The tracker has been accumulating them all along;
    # until now they were simply never emitted, so the dataset had no cluster type.
    # Source markers present in this document, counted from the same tree the walk
    # uses. Comparing against `fed` in-process names the divergent file immediately,
    # instead of an external gate reporting a corpus-wide shortfall 30 minutes later.
    src_count: dict[str, int] = {}
    for node in text_el.iter():
        tg = node.tag
        if not isinstance(tg, str):
            continue
        if tg in B.OPEN:
            k = f"{B.OPEN[tg]}/open"
            src_count[k] = src_count.get(k, 0) + 1
        elif tg in B.CLOSE:
            k = f"{B.CLOSE[tg]}/close"
            src_count[k] = src_count.get(k, 0) + 1

    fed_count: dict[str, int] = {}
    for cl in state.brackets.clusters:
        if cl.from_open_marker:
            fed_count[f"{cl.type}/open"] = fed_count.get(f"{cl.type}/open", 0) + 1
        if cl.from_close_marker:
            fed_count[f"{cl.type}/close"] = fed_count.get(f"{cl.type}/close", 0) + 1
    out_count: dict[str, int] = {}

    flags: dict[int, set[str]] = {}
    slot_set = set(state.slots)
    first_slot = state.slots[0] if state.slots else None
    last_slot = state.slots[-1] if state.slots else None
    for cl in state.brackets.clusters:
        # A marker can precede every readable sign in its document -- a line opening
        # with a break. Its coordinate is None, and collapsing that to the other end
        # (or dropping the cluster) lost 9,060 markers. An unknown start means the
        # range was already open at the document's first sign; an unknown end means it
        # was still open at the last.
        lo = cl.start_sign if cl.start_sign is not None else first_slot
        hi = cl.end_sign if cl.end_sign is not None else last_slot
        if lo is None or hi is None:
            continue
        lo, hi = min(lo, hi), max(lo, hi)
        slots = {n for n in state.slots if lo <= n <= hi}
        # A boundary sign belongs to the range only if the range covers a non-zero
        # part of it: an opening marker at len(sym) sits after the sign, a closing
        # marker at 0 sits before it.
        if lo != hi or cl.start_sign != cl.end_sign:
            if cl.start_sign is not None and cl.start_offset >= state.slot_len.get(
                cl.start_sign, 0
            ):
                slots.discard(cl.start_sign)
            if cl.end_sign is not None and cl.end_offset <= 0:
                slots.discard(cl.end_sign)
        else:
            if cl.start_offset >= cl.end_offset:
                slots.discard(lo)
        # A range may enclose no sign at all -- `<del_in/><del_fin/>` between two
        # signs, or a marker pair inside one sign with zero extent.  That is still an
        # editorial statement (a break of unknown extent sits here), so it is kept as
        # a point anchored to its boundary sign, with width=0.  Discarding these lost
        # 30% of all ranges.  Only positive-width ranges induce sign flags.
        width = len(slots)
        if not slots:
            anchor = cl.start_sign if cl.start_sign is not None else cl.end_sign
            if anchor is None:
                anchor = first_slot
            if anchor is None or anchor not in slot_set:
                continue
            slots = {anchor}
        else:
            fam = {"del": "missing"}.get(cl.type, cl.type)
            for n in slots:
                flags.setdefault(n, set()).add(fam)
        c = cv.node("cluster", slots=slots)
        cv.feature(
            c, type=cl.type, orphan=cl.orphan, width=width,
            start_offset=cl.start_offset, end_offset=cl.end_offset,
            from_open_marker=1 if cl.from_open_marker else 0,
            from_close_marker=1 if cl.from_close_marker else 0,
        )
        # `oslots` says what the range *covers*; these say where its boundaries *are*.
        # The two differ by design -- a marker at len(sym) excludes its own sign from
        # coverage -- so an offset without its sign is meaningless.
        if cl.start_sign is not None and cl.start_sign in state.slot_len:
            cv.edge(c, (SLOT_TYPE, cl.start_sign), startsAt=None)
        if cl.end_sign is not None and cl.end_sign in state.slot_len:
            cv.edge(c, (SLOT_TYPE, cl.end_sign), endsAt=None)
        if cl.crossesline:
            cv.feature(c, crossesline=1)
        if cl.nested:
            cv.feature(c, nested=1)
        if cl.from_open_marker:
            out_count[f"{cl.type}/open"] = out_count.get(f"{cl.type}/open", 0) + 1
        if cl.from_close_marker:
            out_count[f"{cl.type}/close"] = out_count.get(f"{cl.type}/close", 0) + 1
        cv.terminate(c)

    if ledger is not None:
        ledger.note_markers(rel, src_count, fed_count, out_count)

    # Induced sign flags are derived from cluster membership rather than stamped from
    # tracker state during the walk.  Stamping made the two disagree on 482,076 signs:
    # the flag followed the range to the line end while the cluster did not, and a
    # marker at the start of a sign was missed entirely.
    for n, fams in flags.items():
        cv.feature((SLOT_TYPE, n), **{f: 1 for f in fams})

    # Sign-level cuneiform.  `cu` is one string for a whole line and not sign-aligned,
    # so the corpus could not be queried by grapheme.  Where the line has exactly as many
    # cuneiform codepoints as signs, they are laid out one per sign.
    #
    # That the zip is correct rather than merely plausible is established elsewhere and
    # not assumed here: `programs/signmap.tsv` learns reading -> codepoint from these
    # same lines and finds one reading landing on one codepoint 99% of the time over
    # 80,000 observations, and 96.2% of those entries agree with Oracc's sign list. A
    # wrong alignment could not produce either number.
    #
    # Lines whose counts differ get nothing: `cu_aligned` says which is which, so a
    # query can never silently mix aligned and unaligned material.
    # Which lines carry damage at all.  A surplus placeholder may only be absorbed on a
    # line where the source records a lacuna; anywhere else it is unexplained and the
    # line stays unaligned.  Zero-width damage points do not flag their neighbouring
    # sign, so cluster boundaries are collected too, not just induced flags.
    multi_signs = cuneiform.load_multi(PROGRAMS / "signmap-multi.tsv")
    damaged = set()
    for cl in state.brackets.clusters:
        if cl.type != "del":
            continue
        for s_ in (cl.start_sign, cl.end_sign):
            if s_ is None:
                continue
            for ln_, ext_ in state.line_extent.items():
                if ext_[0] <= s_ <= ext_[1]:
                    damaged.add(ln_)
                    break

    for line_node, ext in state.line_extent.items():
        cu_text = state.line_cu.get(line_node)
        if not cu_text:
            continue
        slots = [n for n in range(ext[0], ext[1] + 1) if n not in state.anchor_slots]
        syms = [state.slot_sym.get(n, "") for n in slots]
        got = cuneiform.align(
            cu_text, syms, damaged=line_node in damaged, multi=multi_signs
        )
        if got is None:
            cv.feature(line_node, cu_aligned=0)
            continue
        how, per_sign = got
        cv.feature(line_node, cu_aligned=how)
        for n, ch in zip(slots, per_sign):
            cv.feature((SLOT_TYPE, n), cu_sign=ch)
            if len(ch) > 1:
                cv.feature((SLOT_TYPE, n), cu_nsigns=len(ch))

    # Witness apparatus.  A fragment covers the slots of the lines that cite it, so
    # `€1` in a composite tablet is queryable as an object rather than a string.
    #
    # It used to be given `{state.slots[0]}` -- the document's first sign -- for every
    # fragment, so the comment above was simply false and any slot-based containment
    # query returned nonsense.  The extent is now the union of its witness lines, which
    # costs almost nothing in oslots because those lines are contiguous and oslots
    # stores ranges.
    if state.slots:
        frag_slots: dict[str, set] = {}
        for line_node, siglum in state.line_frag:
            ext = state.line_extent.get(line_node)
            if ext is None:
                continue
            # a composite siglum such as €1+2 names several witnesses
            for part in lineref.LineRef(raw="", frag=siglum).frags or (siglum,):
                frag_slots.setdefault(part, set()).update(range(ext[0], ext[1] + 1))

        for key, (siglum, txtpubl) in state.fragments.items():
            name = siglum or key
            slots = frag_slots.get(name) or {state.slots[0]}
            fn = cv.node("fragment", slots=slots)
            cv.feature(fn, frag=name, txtpubl=txtpubl)
            cv.terminate(fn)
            state.frag_nodes[name] = fn

        # Every line now carries at least an anchor slot, so none is skipped here. The
        # skip existed because a node with no slots *and* an edge crashes TF 13.1.0
        # while it deletes unlinked nodes (walker.py:1425; see
        # handoff/TF-WALKER-BUG-HANDOFF.md) -- it silently dropped witness edges too.
        for line_node, siglum in state.line_frag:
            if line_node not in state.lines_with_slots:
                continue
            for part in lineref.LineRef(raw="", frag=siglum).frags or (siglum,):
                fn = state.frag_nodes.get(part)
                if fn is not None:
                    cv.edge(line_node, fn, witness=None)

        for attrs, slot in state.notes:
            nn = cv.node("note", slots={slot})
            for k, v in attrs.items():
                if v:
                    cv.feature(nn, **{k: v})
            cv.terminate(nn)
            cv.edge(nn, (SLOT_TYPE, slot), noteref=None)

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

    if groups is not None:
        groups.setdefault(docid, []).append(
            (doc, state.slots[0] if state.slots else None)
        )
    cv.terminate(doc)
    return True


class _State:
    """Tracks the open line / column / surface / paragraph / colon while walking."""

    def __init__(self, cv, keep_empty: bool, omap=None, lexemes=None):
        self.cv = cv
        self.keep_empty = keep_empty
        # Corpus-wide, shared across documents: a lexeme spans the whole corpus.
        self.lexemes = lexemes
        # Repairs are applied in memory but src_file names the file on disk, so every
        # recorded span has to be translated back to original coordinates.
        self.omap = omap
        self.surface = self.column = self.line = None
        self.paragraph = self.colon = None
        self.collabel = None
        self.surface_label = None
        self.brackets = B.Tracker()
        self.line_no = 0
        self.sign_idx = 0
        self.words_in_para = 0
        self.slots: list[int] = []
        self.slot_len: dict[int, int] = {}     # slot -> len(sym), for offset maths
        self.line_first: int | None = None     # first slot of the current line
        self.pending_layouts: list[dict] = []
        self.needs_anchor = False
        self.fragments: dict[str, tuple[str, str]] = {}   # key -> (siglum, txtpubl)
        self.frag_nodes: dict[str, object] = {}
        self.notes: list[tuple[dict, int]] = []           # (attrs, anchor slot)
        # Notes seen before any slot exists to hang them on, flushed at the next slot.
        self.pending_notes: list[dict] = []
        self.line_frag: list[tuple[object, str]] = []     # (line node, siglum)
        self.lines_with_slots: set = set()
        self.line_extent: dict = {}      # line node -> [first slot, last slot]
        self.line_cu: dict = {}          # line node -> its cu string
        self.slot_sym: dict = {}         # slot -> its clean reading, for the sign table
        self.anchor_slots: set = set()
        # len(self.slots) when a structural node was opened.  A node whose count has not
        # moved by the time it closes received no slots, and TF deletes unlinked nodes --
        # which silently cost 15,434 `line`, 6,802 `colon` and 3,848 `note` nodes.
        self.opened_at: dict = {}

    def _anchor_slot(self):
        """An empty slot that exists only to keep a contentless structure alive.

        `anchor=1` and `type="empty"` mark it so it can be excluded from linguistic
        counts and from rendering; it is a real slot for every other purpose, including
        damage-range boundaries, which is why it is registered in `slot_len`.
        """
        a = self.cv.slot()
        self.cv.feature(a, srcxml="", sym="", after="", type="empty", anchor=1)
        self.slots.append(a[1])
        self.slot_len[a[1]] = 1
        self.anchor_slots.add(a[1])
        self._flush_notes(a[1])
        if self.line is not None:
            # An anchored line is a line with slots for every purpose that matters:
            # witness edges used to skip slotless lines to dodge a TF crash, so the
            # anchor restores those edges too.
            self.lines_with_slots.add(self.line)
            self._extend_line(a[1])
        return a[1]

    def _extend_line(self, slot: int) -> None:
        ext = self.line_extent.get(self.line)
        if ext is None:
            self.line_extent[self.line] = [slot, slot]
        else:
            ext[1] = slot

    def _carry_notes(self, t, here) -> None:
        """Keep a contentless token's notes, deferring when no slot exists yet."""
        for na in t.note_attrs or ():
            if here is None:
                self.pending_notes.append(na)
            else:
                self.notes.append((na, here))

    def _flush_notes(self, slot) -> None:
        for na in self.pending_notes:
            self.notes.append((na, slot))
        self.pending_notes.clear()

    # ---------------------------------------------------------------- structure
    def start_line(self, node, continues=frozenset()):
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
        self.opened_at[self.line] = len(self.slots)
        cv.feature(
            self.line,
            lnr=ref.raw, lnno=ref.lnno or ref.raw.strip(), prime=ref.prime,
            linetail=ref.tail, txtid=node.get("txtid", ""), srcln=self.line_no,
        )
        if ref.ln is not None:
            cv.feature(self.line, ln=ref.ln)
        if node.get("cu"):
            self.line_cu[self.line] = node.get("cu")
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
        self.line_first = None
        if self.needs_anchor and not self.slots:
            # Registered in slot_len like any other slot: leaving it out made
            # `start_offset >= slot_len.get(sign, 0)` true for every cluster touching it,
            # so the boundary rule discarded them and the fallback then rejected the
            # anchor as "not a real sign" -- losing all damage in such documents.
            anchor_slot = self._anchor_slot()
            for feats in self.pending_layouts:
                self._emit_layout(feats, anchor_slot)
            self.pending_layouts.clear()

        last = self.slots[-1] if self.slots else None
        if ref.frag:
            self.line_frag.append((self.line, ref.frag))
        self.brackets.start_line(
            self.line_no, continues, last, self.slot_len.get(last, 0)
        )

    def stray_note(self, attrs) -> None:
        """A <note> that is not inside a word.  Anchor it where the reader is."""
        na = {"n": attrs.get("n", ""), "c": attrs.get("c", "")}
        here = self.slots[-1] if self.slots else None
        if here is None:
            self.pending_notes.append(na)
        else:
            self.notes.append((na, here))

    def stray_marker(self, tag: str) -> None:
        """A bracket marker that sits between words rather than inside one."""
        here = self.slots[-1] if self.slots else None
        B.feed(self.brackets, tag, here, self.slot_len.get(here, 0), self.line_first)

    def close_paragraph(self, double: bool = False):
        cv = self.cv
        if self.paragraph is not None:
            cv.feature(self.paragraph, ruling="double" if double else "single")
            cv.terminate(self.paragraph)
            self.paragraph = None

    def start_colon(self, node):
        cv = self.cv
        # _close(), not cv.terminate(): the anchor that keeps a contentless structure
        # alive lives there, and terminating directly here bypassed it, so a <clb> with
        # no readable sign was still deleted as unlinked -- 3,345 of them.
        self._close(("colon",))
        self.colon = cv.node("colon")
        self.opened_at[self.colon] = len(self.slots)
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
            # A marker-only <w> sits *between* signs.  Anchoring it inside the
            # previous sign at offset 0 would make that sign look damaged, so an
            # opening boundary is placed at the end of the previous sign and a
            # closing boundary likewise -- either way covering no part of it.
            here = self.slots[-1] if self.slots else None
            edge = self.slot_len.get(here, 0)
            for t in toks:
                for tagname, off in t.markers:
                    B.feed(self.brackets, tagname, here, edge, self.line_first)
                self._carry_notes(t, here)
            # `<w></w>` -- 297 of them -- tokenises to nothing at all. Returning here
            # gave it neither a `word` nor a `layout` node, so the element vanished
            # without appearing in any count. An empty word is still a source
            # construct with a span; it gets a layout node like any other
            # contentless <w>.
            if not toks and sp is not None:
                feats = {"src_span": self._span(sp)}
                if self.slots:
                    self._emit_layout(feats, self.slots[-1])
                else:
                    self.pending_layouts.append(feats)
            if toks:
                feats = {}
                total_space = sum(t.space_count for t in toks)
                if total_space:
                    feats["space_count"] = total_space
                marks = [tag for t in toks for tag, _ in t.markers]
                if marks:
                    feats["markers"] = " ".join(marks)
                if sp is not None:
                    feats["src_span"] = self._span(sp)
                if self.slots:
                    self._emit_layout(feats, self.slots[-1])
                else:
                    # nothing to anchor to yet; a line commonly opens with an indent
                    self.pending_layouts.append(feats)
            return

        if self.line is None:
            # A word can precede the first <lb>. It gets no word node -- there is no
            # line to hang it on -- but its markers are still real damage annotation
            # and must reach the tracker, or they vanish silently.
            for t in toks:
                for tagname, off in t.markers:
                    B.feed(
                        self.brackets, tagname,
                        self.slots[-1] if self.slots else None,
                        self.slot_len.get(self.slots[-1], 0) if self.slots else 0,
                        self.line_first,
                    )
                self._carry_notes(t, self.slots[-1] if self.slots else None)
            return
        w = cv.node("word")
        trans = node.get("trans")
        if trans is not None:
            cv.feature(w, trans=trans)
        if sp is not None:
            cv.feature(w, src_span=self._span(sp))

        word_slots = []
        # Walk *all* tokens, not just the ones that become slots. An empty token can
        # still carry markers -- a marker-only <w> nested inside a word with readable
        # signs -- and feeding only `keep` dropped them. That was the last source of
        # marker loss, concentrated in heavily nested documents.
        for t in toks:
            if t.type == "empty" and not self.keep_empty:
                here = self.slots[-1] if self.slots else None
                for tagname, off in t.markers:
                    B.feed(
                        self.brackets, tagname, here,
                        self.slot_len.get(here, 0) if here else 0,
                        self.line_first,
                    )
                # A <note> on a contentless token is a real editorial note.  Feeding
                # only markers here dropped 3,848 of them -- 31.7% of the corpus's
                # notes -- the same defect as the marker loss, one field over.
                self._carry_notes(t, here)
                continue
            self.sign_idx += 1
            s = cv.slot()
            # cv.slot() returns a node *reference* (nType, seq); cv.node(slots=...)
            # wants the raw slot numbers, so keep the sequence part.
            word_slots.append(s[1])
            self.slots.append(s[1])
            self.slot_len[s[1]] = len(t.sym)
            self.slot_sym[s[1]] = t.sym
            self._flush_notes(s[1])
            if self.line is not None:
                self.lines_with_slots.add(self.line)
                self._extend_line(s[1])
            if self.line_first is None:
                self.line_first = s[1]
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
            for f in ("corr", "subscr", "materlect", "surplus", "symmark"):
                v = getattr(t, f)
                if v:
                    cv.feature(s, **{f: v})
            if t.materlect and set(t.materlect) <= set("!?"):
                cv.feature(s, materlect_anomalous=1)
            # Any inline element with no dedicated feature is named here, so that
            # `srcxml` is not the sole record of it. 149 signs carry one: ras_X (an
            # erasure of unread signs), AkkGLOS/HitGLOS, PARSER_ERROR, the mistyped
            # del_iin, and ODF styling the authoring tool leaked in. Their text is in
            # `sym` already; this is the tag identity, which the tokeniser would
            # otherwise drop. Without it the provenance module could not be separated
            # without losing something.
            other = [
                tag for tag, _off in t.markers
                if TAG_DESTINATION.get(tag.split(":")[-1]) in (None, "raw", "malformed")
            ]
            if other:
                cv.feature(s, othertags=" ".join(dict.fromkeys(other)))
            # Stamp the state *as it stands when the sign begins*, then feed this
            # sign's own markers with their true intra-sign offsets.  Feeding first
            # made a mid-sign del_in mark the whole sign, and a mid-sign del_fin
            # leave it unmarked.
            # Feed the *global* slot number: cluster slot sets are looked up among
            # state.slots, which are global.  A per-document counter coincides with
            # them only in the first document.
            for tagname, off in t.markers:
                B.feed(self.brackets, tagname, s[1], off, self.line_first)
            if t.note_attrs:
                for na in t.note_attrs:
                    self.notes.append((na, s[1]))

        got = morph.analyses(node.attrib)
        sel = morph.parse_selection(node.get("mrp0sel"))
        # index -> the mrp0sel token(s) that selected it, verbatim and in source order.
        #
        # The value is the token, not just the alternative letters, because it must never
        # be empty: TF writes a valued edge file as `from<TAB>to<TAB>value`, and a None
        # among real values comes out as a two-field line that the reader then drops --
        # silently, taking the *other* words' edges with it.  Mixing valued and unvalued
        # edges in one feature produces a malformed file, so every selected edge carries
        # a real token: "1", "2a", "1bR 1bS".
        chosen: dict[int, str] = {}
        for one in sel.selectors:
            prev = chosen.get(one.index)
            chosen[one.index] = f"{prev} {one.raw}" if prev else one.raw
        cv.feature(
            w, nanalyses=len(got), mrpsel=sel.raw.strip(), mrpsel_kind=sel.kind,
            nselected=len(chosen),
        )
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
            if self.lexemes is not None and a.base.lemma:
                self.lexemes.setdefault((a.base.lemma, a.base.gloss), []).append(an)
            if not a.ok or a.normalised:
                # `raw` is kept wherever the parsed fields do not reconstruct the source
                # string: an incomplete parse, or a value whose fields carried padding
                # that normalisation removed (12.8% of analyses).  Storing all 1.6M
                # strings would cost 175 MB for no extra information, but these must be
                # kept or the padding is unrecoverable -- and it has to be recoverable
                # *here*, because src_span is provenance and may not be loaded.
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
            # One edge per *selected analysis*, not one per word.  `mrp0sel="1 2a"`
            # selects two analyses and `"1bR 1bS"` two alternatives of one; emitting
            # only the first discarded the editor's other choices on 20,907 words.
            # TF stores one value per (from, to) pair, so alternatives that share an
            # analysis are joined -- distinct analyses are distinct pairs and keep
            # their own values.
            if sel.kind == "analysis" and a.index in chosen:
                cv.edge(w, an, selected=chosen[a.index])

        cv.terminate(w)
        self.words_in_para += 1

    def _span(self, sp) -> str:
        a, b = sp.outer_start, sp.outer_end
        if self.omap is not None:
            a, b = self.omap.span_to_original(a, b)
        return f"{a}-{b}"

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
                # `line` is closed before `colon`, so a line anchor also rescues the
                # colon around it and no second slot is created.
                if k in ("line", "colon") and self.opened_at.get(n) == len(self.slots):
                    self._anchor_slot()
                self.cv.terminate(n)
                self.opened_at.pop(n, None)
                setattr(self, k, None)
        if "column" in kinds:
            self.collabel = None

    def finish(self):
        if self.needs_anchor and not self.slots:
            self._anchor_slot()   # a document with no <lb> at all
        last = self.slots[-1] if self.slots else None
        self.brackets.finish(last, self.slot_len.get(last, 0))
        self.close_paragraph()
        self._close(("line", "colon", "paragraph", "column", "surface"))


def build(corpus_root: Path, out_dir: Path, keep_empty: bool = False,
          files=None, patches=None, silent: str = "deep", ledger=None,
          load: bool = True):
    """Run the conversion.  Returns a loaded TF api, or None on failure.

    `load=False` returns True instead and skips the post-walk load.  On the full
    corpus that load compiles all 106 features into TF's binary cache -- about 35
    minutes -- and build.py then compacts, rewriting every feature file and
    invalidating the whole cache.  The work was discarded on every run.
    """
    from tf.convert.walker import CV
    from tf.fabric import Fabric

    corpus_root = Path(corpus_root)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if files is None:
        files = sorted(corpus_root.rglob("*.xml"), key=lambda p: str(p).lower())
    patches = patches or {}
    ledger = ledger if ledger is not None else Ledger()

    TF = Fabric(locations=str(out_dir), silent=silent)
    cv = CV(TF, silent=silent)
    good = cv.walk(
        lambda c: director(c, files, corpus_root, keep_empty, patches, ledger),
        SLOT_TYPE,
        otext=OTEXT,
        generic=GENERIC,
        intFeatures=set(),      # set dynamically in the director, see above
        featureMeta={},
        warn=False,
    )
    if not good:
        return None
    if not load:
        return True
    TF2 = Fabric(locations=str(out_dir), silent=silent)
    api = TF2.loadAll(silent=silent)
    # loadAll returns the api on success, but a bare bool in some configurations;
    # fall back to the Fabric's own api handle so callers always get one object.
    if api is True or api is False:
        api = getattr(TF2, "api", None) if api else None
    return api
