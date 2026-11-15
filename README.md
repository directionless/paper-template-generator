# paper-templator

Makes printable handwriting practice paper as a PDF. It can draw slant guides for cursive.

It is one Python file and needs nothing beyond Python 3.

## Quick start

```bash
python3 handwriting.py
```

This writes `handwriting.pdf`: US Letter, 8 mm x-height, and slant guides at 55°.

```bash
python3 handwriting.py --help
```

## What the lines are

Each row has, from top to bottom:

| Line      | Default look         | Meaning                                        |
|-----------|----------------------|------------------------------------------------|
| ascender  | thin solid black     | top of tall letters (l, h, k, capitals)        |
| midline   | dashed light blue    | top of small letters (a, c, o); the x-height   |
| baseline  | thick solid black    | where letters sit                              |
| descender | dotted pale blue     | bottom of tails (g, y, p)                      |
| slant     | thin solid light blue| angle guides for cursive                       |

## Common options

Sizes take `mm`, `cm`, `in`, or `pt`. A plain number means mm.

| Option              | Default         | What it does                                          |
|---------------------|-----------------|-------------------------------------------------------|
| `-o FILE`           | handwriting.pdf | output file                                           |
| `--paper`           | letter          | `letter`, `legal`, `a4`, `a5`                         |
| `--landscape`       | off             | turn the page sideways                                |
| `--pages N`         | 1               | number of pages                                       |
| `--x-height`        | 8mm             | baseline to midline                                   |
| `--ascender`        | 2 × x-height    | baseline to top line                                  |
| `--descender`       | 1 × x-height    | baseline to bottom line                               |
| `--row-gap`         | 5mm             | empty space between rows                              |
| `--rows N`          | as many as fit  | force a row count                                     |
| `--slant-angle`     | 55              | degrees from horizontal (90 = upright)                |
| `--slant-spacing`   | x-height        | distance between slant lines                          |
| `--slant-span`      | row             | `row` = only inside rows, `page` = all the way down   |
| `--no-slant`        | off             | no slant lines                                        |
| `--margin`          | 15mm            | all margins (`--margin-left` etc. for one side)       |
| `--margin-line`     | off             | vertical line at the left margin, e.g. `'0.8 pink'`   |
| `--xheight-fill`    | off             | shade the x-height band, e.g. `'#fff4cc'`             |
| `--color`           | —               | one color for all horizontal lines                    |
| `--no-footer`       | off             | hide the small footer (see below)                     |

Each page has a small gray footer in the bottom margin. It shows the sizes used, the command (without `-o`), and the project URL, so you can make the same page again.

Common cursive slants: about 52–55° for traditional styles, 60–65° for a gentler slant.

## Line styles

Every line has a `--<name>-style` option: `--ascender-style`, `--midline-style`, `--baseline-style`, `--descender-style`, `--slant-style`.

A style is up to three words, in any order:

- **width**: a number in points, such as `0.8` (or `0.3mm`)
- **dash**: `solid`, `dashed`, `dotted`, or a custom pattern like `dash=6/2` (on/off lengths in points)
- **color**: `#rrggbb`, `#rgb`, or a name: black, gray, lightgray, red, pink, blue, lightblue, green, lightgreen, orange, purple

You only need the parts you want to change. The rest keep their defaults. Use `none` to hide a line.

## Examples

Bigger lines for a beginner, with a shaded middle band:

```bash
python3 handwriting.py --x-height 12mm --xheight-fill '#fff4cc' -o big.pdf
```

Smaller lines with slants down the whole page, 5 pages, A4:

```bash
python3 handwriting.py --paper a4 --x-height 6mm --slant-span page --pages 5 -o practice.pdf
```

Red dotted midline, darker slants, no descender line:

```bash
python3 handwriting.py --midline-style 'dotted red' --slant-style '0.5 gray' --descender-style none
```

Print-style paper with no slants:

```bash
python3 handwriting.py --no-slant
```

## Printing

Print at **100% / Actual size**. If you use "Fit to page", the sizes will be wrong.
