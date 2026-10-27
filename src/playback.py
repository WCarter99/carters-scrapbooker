"""Slide selection logic, independent of any UI."""
import random

import template_manager as tm

LOOKAHEAD = 10  # photos considered when filling extra zones
MULTI_MODES = ("mixed", "same")  # extra zones: prefer other folders / lead's folder
MULTI_LABELS = {"mixed": "different folders where possible", "same": "same folder"}


class PhotoPool:
    """One self-refilling shuffled pool per folder, plus the order folders take turns in."""

    def __init__(self, folders):
        self.photos = {f["name"]: f["photos"] for f in folders if f["photos"]}
        self.names = list(self.photos)
        self.pools = {}
        self.turn = 0
        self.bag = []

    def next_folder(self, sequential):
        """Next lead folder: strictly in order, or random without repeats until all have had a turn."""
        if sequential:
            name = self.names[self.turn % len(self.names)]
            self.turn += 1
            return name
        if not self.bag:
            self.bag = random.sample(self.names, len(self.names))
        return self.bag.pop()

    def following(self, name):
        """The other folders, in turn order, starting after `name`."""
        i = self.names.index(name)
        return self.names[i + 1:] + self.names[:i]

    def peek(self, name, k, exclude=()):
        """Up to k upcoming photos from the folder (refilling it when exhausted), skipping `exclude` paths."""
        pool = self.pools.setdefault(name, [])
        cands = [p for p in reversed(pool) if p["path"] not in exclude][:k]
        if not cands:
            fresh = [p for p in self.photos[name] if p["path"] not in exclude]
            random.shuffle(fresh)
            pool[:0] = fresh  # unseen photos stay at the end and are used first
            cands = [p for p in reversed(pool) if p["path"] not in exclude][:k]
        return cands or list(self.photos[name])[:k]  # folder smaller than the frame: allow repeats

    def take(self, name, photo):
        pool = self.pools.get(name, [])
        if photo in pool:
            pool.remove(photo)


def build_slide(pool, templates, mode, multi_source):
    """Pick a lead photo, a matching template, and fill the remaining zones.

    mode: "rotating" takes folders in order, anything else picks randomly.
    multi_source: "same" fills extra zones from the lead's folder, "mixed" from other folders.
    """
    folder = pool.next_folder(mode == "rotating" or multi_source == "same")
    lead = pool.peek(folder, 1)[0]
    pool.take(folder, lead)
    template = tm.pick_template(templates, lead, random)
    zones = template["photo_zones"]
    lead_idx = min(range(len(zones)), key=lambda i: tm.zone_distance(lead, zones[i]))
    photos = [None] * len(zones)
    photos[lead_idx] = lead
    others = pool.following(folder)
    for i, zone in enumerate(zones):
        if photos[i] is not None:
            continue
        if multi_source == "same" or not others:
            src = folder
        else:  # mixed: next folder in turn, wrapping only if there are fewer folders than zones
            src = others.pop(0)
            others.append(src)
        taken = [p["path"] for p in photos if p]
        best = tm.select_best_photo_for_zone(pool.peek(src, LOOKAHEAD, taken), zone)
        pool.take(src, best)
        photos[i] = best
    caption = next((p["caption_text"] for p in photos if p["caption_text"]), None) \
        if template.get("text_zones") else None
    return {"template": template, "paths": [p["path"] for p in photos],
            "caption": caption, "count": len({p["path"] for p in photos})}
