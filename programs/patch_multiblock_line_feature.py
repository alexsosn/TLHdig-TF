from pathlib import Path


def main() -> None:
    path = Path("programs/tlhdig/convert.py")
    text = path.read_text(encoding="utf8")
    old = '''        self.line = cv.node("line")
        self.line_manuscript_block[self.line] = self.manuscript_line_scope.get(id(node))
        self.opened_at[self.line] = len(self.slots)
'''
    new = '''        self.line = cv.node("line")
        manuscript_block = self.manuscript_line_scope.get(id(node))
        self.line_manuscript_block[self.line] = manuscript_block
        if manuscript_block is not None:
            cv.feature(self.line, manuscript_block=manuscript_block)
        self.opened_at[self.line] = len(self.slots)
'''
    if text.count(old) != 1:
        raise SystemExit(f"line scope patch: expected one match, found {text.count(old)}")
    path.write_text(text.replace(old, new, 1), encoding="utf8")


if __name__ == "__main__":
    main()
