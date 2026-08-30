"""The app-config gate.

TF only validates `app/config.yaml` when `use()` loads the corpus -- 12 minutes and 5 GB
for this dataset -- and a `features:` entry naming a feature that does not apply to the
node type fails *silently*: the field renders as nothing and the app looks correct.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import appcheck

HEAD = "@node\n@valueType=str\n\n"


def make(tmp_path: Path, files: dict[str, str]) -> Path:
    d = tmp_path / "tf"
    d.mkdir()
    for name, body in files.items():
        head = ("@edge\n\n" if name == "oslots"
                else "@config\n@fmt:text-orig-plain={sym}\n\n" if name == "otext"
                else HEAD)
        (d / f"{name}.tf").write_text(head + body, encoding="utf8")
    return d


@pytest.fixture
def dataset(tmp_path):
    # slots 1-10 are signs, 11-12 words, 13 a line
    return make(tmp_path, {
        "otype": "1-10\tsign\n11-12\tword\n13\tline\n",
        "sym": "1-10\ta\n",
        "trans": "11-12\tanda\n",
        "lnno": "13\t1'\n",
        "otext": "",   # the @fmt line lives in the header, as in a real otext.tf
    })


def test_config_matching_the_dataset_passes(dataset):
    cfg = {
        "typeDisplay": {
            "sign": {"template": "{sym}"},
            "word": {"features": "trans"},
            "line": {"label": "{lnno}"},
        },
        "dataDisplay": {"textFormat": "text-orig-plain"},
    }
    assert appcheck.check(dataset, cfg) == []


def test_unknown_node_type_is_reported(dataset):
    cfg = {"typeDisplay": {"lex": {"label": "{sym}"}}}
    (problem,) = appcheck.check(dataset, cfg)
    assert "lex" in problem and "no such node type" in problem


def test_missing_feature_is_reported(dataset):
    cfg = {"typeDisplay": {"word": {"features": "lemma"}}}
    (problem,) = appcheck.check(dataset, cfg)
    assert "'lemma' does not exist" in problem


def test_feature_on_the_wrong_node_type_is_reported(dataset):
    """The silent failure: `lnno` is real, but no word node carries it."""
    cfg = {"typeDisplay": {"word": {"features": "lnno"}}}
    (problem,) = appcheck.check(dataset, cfg)
    assert "no value on any word node" in problem


def test_template_and_label_fields_are_both_read(dataset):
    cfg = {"typeDisplay": {
        "sign": {"template": "{nope}"},
        "line": {"label": "{alsonope}"},
    }}
    assert len(appcheck.check(dataset, cfg)) == 2


def test_colon_syntax_in_featuresBare_is_split(dataset):
    cfg = {"typeDisplay": {"word": {"featuresBare": "trans:lnno"}}}
    (problem,) = appcheck.check(dataset, cfg)
    assert "lnno" in problem


def test_excluded_and_textformat_are_checked(dataset):
    cfg = {"dataDisplay": {"excludedFeatures": ["ghost"], "textFormat": "text-orig-fancy"}}
    problems = appcheck.check(dataset, cfg)
    assert any("ghost" in p for p in problems)
    assert any("text-orig-fancy" in p for p in problems)


def test_node_ranges_merge_split_specs(tmp_path):
    d = make(tmp_path, {"otype": "1-3\tsign\n7-9\tsign\n4-6\tword\n"})
    assert appcheck.node_ranges(d)["sign"] == (1, 9)


def test_shipped_config_is_compatible_with_the_installed_tf():
    """A TF upgrade that bumps API_VERSION silently makes `use()` refuse the app."""
    import yaml
    from tf.parameters import API_VERSION

    root = Path(__file__).resolve().parents[2]
    config = yaml.safe_load((root / "app" / "config.yaml").read_text(encoding="utf8"))
    assert config["apiVersion"] == API_VERSION


def test_shipped_config_names_only_real_node_types():
    """Guards the config against a node type being renamed or dropped by the converter."""
    import yaml

    root = Path(__file__).resolve().parents[2]
    tf_dir = root / "tf" / "0.1.0"
    if not (tf_dir / "otype.tf").is_file():
        pytest.skip("no built dataset")
    config = yaml.safe_load((root / "app" / "config.yaml").read_text(encoding="utf8"))
    assert set(config["typeDisplay"]) <= set(appcheck.node_ranges(tf_dir))


def test_stylesheet_does_not_target_classes_tf_never_emits():
    """The first display.css styled `.sign`, `.word`, `.missing`, `.laes` and `.det`.

    Text-Fabric emits none of them: a container is `contnr c<level>` and a label
    `lbl c<level>`, where the level is a number shared by every type at that depth
    (tf/advanced/settings.py:1868). The stylesheet was inlined into every page and did
    nothing, which is invisible -- CSS has no equivalent of an undefined-name error.
    """
    import re

    root = Path(__file__).resolve().parents[2]
    css = (root / "app" / "static" / "display.css").read_text(encoding="utf8")
    # strip comments: they discuss the phantom classes on purpose
    body = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    phantom = {
        "sign", "word", "line", "cluster", "analysis", "document", "fragment",
        "missing", "laes", "ras", "add", "quot", "sgr", "agr", "det", "corr",
    }
    used = set(re.findall(r"\.([A-Za-z][\w-]*)", body))
    bad = sorted(used & phantom)
    assert not bad, f"display.css targets classes TF does not emit: {bad}"


def test_stylesheet_uses_the_classes_tf_does_emit():
    """Guard the other way: the file must still hook the real render classes."""
    root = Path(__file__).resolve().parents[2]
    css = (root / "app" / "static" / "display.css").read_text(encoding="utf8")
    for real in (".contnr", ".lbl", "a.nd", ".txtu", ".txtn", ".tfsechead"):
        assert real in css, f"display.css no longer targets {real}"
