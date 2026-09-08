# Sign-language conservation

TF version: `0.4.0`

## Frozen population

- source documents: **23,884**
- source / non-anchor signs: **3,365,129**
- signs with effective source language: **3,364,981**
- genuinely absent: **148**
- synthetic anchors: **21,215** (language-free required)

## Winning source level

| level | signs |
| --- | ---: |
| word | 40,187 |
| colon | 64,686 |
| line | 3,259,913 |
| text | 195 |
| absent | 148 |

## Most frequent winning raw values

| level | raw value | signs |
| --- | --- | ---: |
| line | `Hit` | 2,929,540 |
| line | `Akk` | 143,961 |
| line | `Hur` | 106,512 |
| colon | `Hit` | 46,750 |
| line | `Hat` | 39,618 |
| line | `Luw` | 27,362 |
| word | `Hur` | 21,876 |
| colon | `Hur` | 11,730 |
| word | `Luw` | 9,455 |
| line | `Sum` | 6,566 |
| line | `Pal` | 5,653 |
| colon | `Hat` | 4,626 |
| word | `Akk` | 3,028 |
| word | `Hit` | 2,052 |
| word | `Hat` | 1,616 |
| colon | `Akk` | 1,532 |
| word | `Sum` | 1,510 |
| line | `ign` | 625 |
| word | `Lin` | 594 |
| text | `Hit` | 195 |
| line | `Hit> <w><note n='15' c=` | 53 |
| word | `Pal` | 53 |
| colon | `Luw` | 48 |
| line | `Hit> <w><del_in/> … <del_fin/></w` | 21 |
| word | `w` | 2 |
| line | `5f_` | 2 |
| word | `𒉽` | 1 |

## Result

**PASS** — every converted document's ordered non-anchor sign sequence matches the independently reconstructed source language values exactly.
