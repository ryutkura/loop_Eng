"""新しい題材（論文）用のフォルダ一式を、.agent/templates/ から作る。

    python scripts/new_paper.py <名前>

<名前> は Python のパッケージ名になるので、英小文字・数字・アンダースコアだけにする（例: cmaes, de_jade）。
"""

import re
import sys

from _lab import d, load_config, rel


def main() -> int:
    if len(sys.argv) != 2 or not re.fullmatch(r"[a-z][a-z0-9_]*", sys.argv[1]):
        print(__doc__)
        return 2
    name = sys.argv[1]
    config = load_config()
    templates = d(config, "agent") / "templates"
    src = d(config, "src") / name
    if (d(config, "sources") / name).exists() or src.exists():
        print(f"{name} は既に存在します。")
        return 1

    def fill(template: str) -> str:
        return (templates / template).read_text(encoding="utf-8").replace("{{NAME}}", name)

    created = {
        d(config, "sources") / name / "paper.md": fill("paper.md"),
        d(config, "sources") / name / "claims.md": fill("claims.md"),
        d(config, "sources") / name / "targets.json": fill("targets.json"),
        src / "README.md": fill("src_README.md"),
        src / "__init__.py": "",
        src / config["pure_layer"]["dir_name"] / "__init__.py": "",
        src / "algorithm" / "__init__.py": "",
        d(config, "tests") / name / "__init__.py": "",
        d(config, "tests") / name / "claims" / "__init__.py": "",
        d(config, "tests") / name / "unit" / "__init__.py": "",
        d(config, "experiments") / name / ".gitkeep": "",
    }
    for path, content in created.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"作成: {rel(path)}")
    print(f"\n次: {rel(d(config, 'sources') / name / 'paper.md')} に論文の Markdown を貼ってください。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
