"""One folder on this computer (~/.scopeguard, or SCOPEGUARD_HOME): clients, every check, and the ledger.
Readable JSON; copy it to keep it, delete it to forget everything."""

from __future__ import annotations

import copy
import json
import os
import threading
from datetime import UTC, datetime
from pathlib import Path


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def home_dir() -> Path:
    raw = os.environ.get("SCOPEGUARD_HOME", "").strip()
    return Path(raw).expanduser() if raw else Path.home() / ".scopeguard"


class Store:
    def __init__(self, home: Path | None = None) -> None:
        self.home = home or home_dir()
        self.home.mkdir(parents=True, exist_ok=True)
        self.path = self.home / "scopeguard.json"
        self._lock = threading.RLock()
        self.data = {"clients": {}, "checks": {}, "ledger": [], "next": 1}
        if self.path.exists():
            try:
                self.data.update(json.loads(self.path.read_text("utf-8")))
            except ValueError:
                self.path.replace(self.path.with_suffix(".unreadable.json"))  # never silently lose records

    def _save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=1), "utf-8")
        tmp.replace(self.path)

    def _id(self) -> int:
        n = self.data["next"]
        self.data["next"] += 1
        return n

    def add_client(self, **c) -> int:
        with self._lock:
            cid = self._id()
            self.data["clients"][str(cid)] = {"id": cid, "created_at": now_iso(), **c}
            self._save()
            return cid

    def client(self, cid: int) -> dict | None:
        with self._lock:
            c = self.data["clients"].get(str(cid))
            return copy.deepcopy(c) if c else None

    def clients(self) -> list[dict]:
        with self._lock:
            return [copy.deepcopy(c) for c in self.data["clients"].values()]

    def add_check(self, **c) -> int:
        with self._lock:
            kid = self._id()
            self.data["checks"][str(kid)] = {"id": kid, "at": now_iso(), **c}
            self._save()
            return kid

    def check(self, kid: int) -> dict | None:
        with self._lock:
            c = self.data["checks"].get(str(kid))
            return copy.deepcopy(c) if c else None

    def checks(self, client_id: int) -> list[dict]:
        with self._lock:
            return [copy.deepcopy(c) for c in reversed(list(self.data["checks"].values())) if c["client_id"] == client_id]

    def decide(self, kid: int, idx: int, decision: str, hours: float, amount: float) -> bool:
        """Record what the freelancer did about one request: quoted it, or waived it. Deciding again replaces it."""
        with self._lock:
            chk = self.data["checks"].get(str(kid))
            if not chk or not 0 <= idx < len(chk["items"]):
                return False
            it = chk["items"][idx]
            self.data["ledger"] = [e for e in self.data["ledger"] if not (e["check_id"] == kid and e["idx"] == idx)]
            self.data["ledger"].append({"check_id": kid, "idx": idx, "client_id": chk["client_id"], "at": now_iso(),
                                        "summary": it["summary"], "decision": decision, "hours": hours, "amount": amount})
            self._save()
            return True

    def ledger(self, client_id: int | None = None) -> list[dict]:
        with self._lock:
            return [copy.deepcopy(e) for e in self.data["ledger"] if client_id in (None, e["client_id"])]
