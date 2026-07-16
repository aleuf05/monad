#!/usr/bin/env python3
"""Create and score blind rich-voice character/performance listening trials."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import Counter
from pathlib import Path


LINES = [
    ("routine", "Status steady. We have room to proceed."),
    ("warning", "Contact ahead. Hold the formation and reduce speed."),
    ("recovery", "The immediate danger has passed, but remain attentive."),
    ("private", "Between us, I am less certain than the report suggests."),
    ("ceremonial", "We carry this record forward in the name of those who kept station."),
    ("humor", "A flawless plan, apart from the part where reality arrived."),
]


def blind_id(character_id: str, line_id: str, seed: str) -> str:
    return hashlib.sha256(f"{seed}:{character_id}:{line_id}".encode()).hexdigest()[:12]


def build_manifest(characters: list[str], artifact_lookup: dict, seed="monad-voice-v1") -> dict:
    trials = []
    for character_id in characters:
        for line_id, transcript in LINES:
            key = f"{character_id}:{line_id}"
            if key not in artifact_lookup:
                continue
            trials.append({
                "trial_id": blind_id(character_id, line_id, seed),
                "line_id": line_id,
                "transcript": transcript,
                "audio": artifact_lookup[key],
                "answer": {"character_id": character_id, "intent": line_id},
            })
    random.Random(seed).shuffle(trials)
    return {"schema_version": "monad.voice-eval.v0.1", "seed": seed, "trials": trials}


def public_manifest(manifest: dict) -> dict:
    return {**manifest, "trials": [{k: v for k, v in trial.items() if k != "answer"} for trial in manifest["trials"]]}


def score(manifest: dict, responses: list[dict]) -> dict:
    answers = {trial["trial_id"]: trial["answer"] for trial in manifest["trials"]}
    judged = [response for response in responses if response.get("trial_id") in answers]
    character_correct = sum(response.get("character_id") == answers[response["trial_id"]]["character_id"] for response in judged)
    intent_correct = sum(response.get("intent") == answers[response["trial_id"]]["intent"] for response in judged)
    caricature = sum(bool(response.get("caricature")) for response in judged)
    transcript_error = sum(bool(response.get("transcript_error")) for response in judged)
    count = len(judged)
    ratio = lambda value: value / count if count else 0
    return {
        "judged": count,
        "character_accuracy": ratio(character_correct),
        "intent_accuracy": ratio(intent_correct),
        "caricature_rate": ratio(caricature),
        "transcript_error_rate": ratio(transcript_error),
        "pass": count > 0 and ratio(character_correct) >= 0.75 and ratio(intent_correct) >= 0.80 and ratio(caricature) < 0.10 and transcript_error == 0,
        "response_counts": dict(Counter(response.get("character_id", "missing") for response in judged)),
    }


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create")
    create.add_argument("artifacts", type=Path, help="JSON map of character_id:line_id to audio URL")
    create.add_argument("--characters", nargs="+", required=True)
    create.add_argument("--out", type=Path, required=True)
    grade = sub.add_parser("score")
    grade.add_argument("manifest", type=Path); grade.add_argument("responses", type=Path)
    args = parser.parse_args()
    if args.command == "create":
        manifest = build_manifest(args.characters, json.loads(args.artifacts.read_text()))
        args.out.write_text(json.dumps(manifest, indent=2) + "\n")
        args.out.with_name(args.out.stem + "-public.json").write_text(json.dumps(public_manifest(manifest), indent=2) + "\n")
    else:
        print(json.dumps(score(json.loads(args.manifest.read_text()), json.loads(args.responses.read_text())), indent=2))


if __name__ == "__main__": main()
