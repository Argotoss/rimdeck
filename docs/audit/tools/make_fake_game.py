"""Generate a synthetic RimWorld install with a realistic-sized mod collection.

Usage: uv run python docs/audit/tools/make_fake_game.py <root> [mod_count] [active_count]
"""

import random
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QPainter

WORDS = (
    "Vanilla Expanded Combat Factions Psycasts Furniture Hair Apparel Weapons "
    "Genes Xenotypes Animals Plants Biomes Storage Quality Interface Medical "
    "Prisoners Mechanoids Royalty Ideology Anomaly Odyssey Power Tech Cooking "
    "Brewing Trading Caravans Raids Events Quests Textures Sounds Music Tweaks "
    "Performance Optimizer Fixes Patch Framework Library Core Extended Better "
    "Simple Smart Realistic Hardcore Dubs Rimfeller Rimatomics Alpha Save Our"
).split()
AUTHORS = (
    "Oskar Potocki", "Dubwise", "Sarg Bjornson", "Taranchuk", "Mlie", "Owlchemist",
    "erdelf", "Jecrell", "Brrainz", "UnlimitedHugs", "Andromeda", "Smash Phil",
    "Killathon", "ISOREX", "Kentington", "Neceros", "Roolo", "Fluffy", "Nals",
)
DLCS = ("Royalty", "Ideology", "Biotech", "Anomaly", "Odyssey")
LOREM = (
    "Adds a broad set of new content that integrates with the base game and its "
    "expansions. Every item is balanced against vanilla progression and comes "
    "with full translations. Safe to add to existing saves. Compatible with "
    "Combat Extended via built-in patches. Report issues on the discussion page."
)


def sub(parent: ET.Element, tag: str, items: list[str]) -> None:
    if not items:
        return
    node = ET.SubElement(parent, tag)
    for item in items:
        ET.SubElement(node, "li").text = item


def write_about(
    folder: Path,
    package_id: str,
    name: str,
    author: str,
    deps: list[str],
    after: list[str],
    before: list[str],
    versions: list[str],
    with_preview: bool,
) -> None:
    about = folder / "About"
    about.mkdir(parents=True, exist_ok=True)
    meta = ET.Element("ModMetaData")
    ET.SubElement(meta, "name").text = name
    ET.SubElement(meta, "packageId").text = package_id
    ET.SubElement(meta, "author").text = author
    ET.SubElement(meta, "url").text = "https://example.invalid/" + package_id
    sub(meta, "supportedVersions", versions)
    if deps:
        node = ET.SubElement(meta, "modDependencies")
        for dep in deps:
            li = ET.SubElement(node, "li")
            ET.SubElement(li, "packageId").text = dep
            ET.SubElement(li, "displayName").text = dep.split(".")[-1]
    sub(meta, "loadAfter", after)
    sub(meta, "loadBefore", before)
    paragraphs = random.randint(1, 4)
    ET.SubElement(meta, "description").text = "\n\n".join([LOREM] * paragraphs)
    ET.ElementTree(meta).write(about / "About.xml", encoding="utf-8")
    if with_preview:
        img = QImage(640, 360, QImage.Format.Format_RGB32)
        img.fill(QColor.fromHsv(random.randint(0, 359), 120, 160))
        painter = QPainter(img)
        painter.setPen(QColor("white"))
        painter.setFont(QFont("Helvetica", 36))
        painter.drawText(img.rect(), 0x84, name)
        painter.end()
        img.save(str(about / "Preview.png"))


def main() -> None:
    root = Path(sys.argv[1]).resolve()
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 600
    active_count = int(sys.argv[3]) if len(sys.argv) > 3 else 300
    random.seed(1)
    _app = QGuiApplication([])
    game = root / "RimWorld"
    (game / "Mods").mkdir(parents=True, exist_ok=True)
    (game / "Version.txt").write_text("1.6.4633 rev1261", encoding="utf-8")
    core_ids = ["Ludeon.RimWorld"] + [f"Ludeon.RimWorld.{d}" for d in DLCS]
    for i, dlc in enumerate(("Core",) + DLCS):
        write_about(
            game / "Data" / dlc, core_ids[i], dlc if i else "Core", "Ludeon Studios",
            [], core_ids[:i], [], ["1.6"], False,
        )
    frameworks = ["brrainz.harmony", "unlimitedhugs.hugslib", "oskarpotocki.vanillafactionsexpanded.core"]
    ids: list[str] = []
    for n in range(count):
        if n < len(frameworks):
            pid = frameworks[n]
            name = ["Harmony", "HugsLib", "Vanilla Expanded Framework"][n]
        else:
            name = " ".join(random.sample(WORDS, random.randint(2, 5)))
            if random.random() < 0.1:
                name += " (Continued)"
            pid = f"{random.choice(AUTHORS).split()[0].lower()}.{name.lower().replace(' ', '').replace('(', '').replace(')', '')}{n}"
        deps = []
        if n >= len(frameworks) and random.random() < 0.6:
            deps.append(random.choice(frameworks))
        after = random.sample(ids, k=min(len(ids), random.choice([0, 0, 1, 2]))) if ids else []
        if random.random() < 0.05:
            deps.append(f"missing.dependency{n}")
        versions = random.choice([["1.6"], ["1.5", "1.6"], ["1.4", "1.5"], ["1.6"]])
        write_about(
            game / "Mods" / f"{n:04d}_{pid.split('.')[-1][:30]}", pid, name,
            random.choice(AUTHORS), deps, after, [], versions, random.random() < 0.8,
        )
        ids.append(pid)
    config = root / "Config"
    config.mkdir(parents=True, exist_ok=True)
    active = core_ids[:4] + frameworks + random.sample(ids[3:], active_count)
    cfg = ET.Element("ModsConfigData")
    ET.SubElement(cfg, "version").text = "1.6.4633 rev1261"
    sub(cfg, "activeMods", active)
    sub(cfg, "knownExpansions", core_ids[1:4])
    ET.ElementTree(cfg).write(config / "ModsConfig.xml", encoding="utf-8")
    print(f"game={game}\nconfig={config}\nmods={count} active={len(active)}")


if __name__ == "__main__":
    main()
