# TLHdig-TF provenance module

`srcxml` (the verbatim source fragment of each sign, editorial markers in
place) and `src_span` (its byte range in the file `src_file` names).

Not needed to read or query the corpus: every tag inside `srcxml` is modelled
in the main dataset -- wrappers as `sgr`/`agr`/`det`/`num`, damage as `cluster`
nodes with offsets, `corr` and `note` as their own features. What these two add
is the byte-exact round trip, which is what Contract A verifies.

Load it alongside the dataset:

    Fabric(locations=['tf/0.1.0', 'tf-provenance/0.1.0'])

or as a Text-Fabric module: `alexsosn/TLHdig-TF/tf-provenance`.

With it loaded you can define the source-faithful text format that the main
dataset can no longer declare on its own:

    A.dm('{srcxml}{after}')
