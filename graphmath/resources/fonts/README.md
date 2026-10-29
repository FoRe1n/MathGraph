# Inter UI fonts

These unmodified static TrueType files come from the official Inter 4.1 release:

https://github.com/rsms/inter/releases/download/v4.1/Inter-4.1.zip

Copyright (c) 2016 The Inter Project Authors (https://github.com/rsms/inter).
Licensed under SIL Open Font License 1.1; the complete upstream license and
copyright notice are in `../licenses/Inter-OFL.txt`.

The original archive's SHA256 is
`9883fdd4a49d4fb66bd8177ba6625ef9a64aa45899767dde3d36aa425756b11e`.
Only `extras/ttf/Inter-Regular.ttf`, `extras/ttf/Inter-Medium.ttf` and
`extras/ttf/Inter-SemiBold.ttf` were copied. No subsetting, renaming or conversion
was performed.

| File | SHA256 |
| --- | --- |
| Inter-Regular.ttf | `40d692fce188e4471e2b3cba937be967878f631ad3ebbbdcd587687c7ebe0c82` |
| Inter-Medium.ttf | `97ad806f526e41546d46365bb3a393145f75b7b1568913db74549ad8b8dba872` |
| Inter-SemiBold.ttf | `78a843fade9d4612a5567302fb595b56976eb5fcebf4fea5a5912d638bafcde3` |

The static faces avoid depending on variable-font axis support for UI weights.
Qt handles device scaling directly. Mathematical previews continue to use the
existing Matplotlib DejaVu math font. The existing DejaVu faces remain available
as a verified UI fallback.
