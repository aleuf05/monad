"""Recovery Literature Index & Query Engine.

Provides programmatic search, verification, and mapping across the A.A. recovery corpus:
- Standard 4th Edition Big Book chapter and concept pagination maps
- 12 Steps operational functions, Big Book anchors, and 12&12 essay links
- 12 Traditions failure-mode prevention and governance rules
- P-11 (Medications) and P-35 (Problems Other Than Alcohol) boundary rules
- H&I / Bridging the Gap protocol verification
- Demarcation between 12th Step volunteerism, Peer Support, and Clinical Therapy
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class BigBookChapter:
    chapter_num: int
    title: str
    pages: str
    main_problem: str
    mechanism: str
    relevant_steps: list[int]
    recurring_concepts: list[str]


@dataclass(frozen=True)
class StepEntry:
    step_num: int
    title: str
    practical_function: str
    big_book_source: str
    twelve_twelve_essay: str
    failure_mode_prevented: str


@dataclass(frozen=True)
class TraditionEntry:
    tradition_num: int
    short_form: str
    long_form_summary: str
    failure_mode_prevented: str
    governance_seam: str


@dataclass(frozen=True)
class PolicyEntry:
    key: str
    title: str
    authority_source: str
    core_rule: str
    demarcation: str
    practical_application: str


BIG_BOOK_CHAPTERS: list[BigBookChapter] = [
    BigBookChapter(
        chapter_num=0,
        title="The Doctor's Opinion",
        pages="xxiii–xxxii",
        main_problem="Physical allergy triggering uncontrollable craving once alcohol is ingested, paired with mental obsession prior to drinking.",
        mechanism="Complete abstinence based on psychic change; medical recognition of the condition's hopelessness under willpower alone.",
        relevant_steps=[1],
        recurring_concepts=["Phenomenon of craving", "Physical allergy", "Hopeless condition", "Psychic change", "Dr. William D. Silkworth"],
    ),
    BigBookChapter(
        chapter_num=1,
        title="Bill's Story",
        pages="1–16",
        main_problem="Progressive demoralization, professional collapse, self-delusion, and total failure of intellectual willpower.",
        mechanism="Peer-to-peer identification (Ebby Thacher); ego deflation; spiritual surrender at Towns Hospital; practical 12th Step work.",
        relevant_steps=[1, 2, 3, 12],
        recurring_concepts=["Ego deflation", "Catastrophic collapse", "Oxford Group principles", "God as you understand Him", "Carrying message"],
    ),
    BigBookChapter(
        chapter_num=2,
        title="There Is A Solution",
        pages="17–29",
        main_problem="Terminal isolation of the alcoholic and the inability of human fellowship alone to arrest self-destruction.",
        mechanism="The Common Peril and Common Solution; vital spiritual experience; Jungian formulation (spiritus contra spiritum).",
        relevant_steps=[1, 2],
        recurring_concepts=["Fellowship of the Spirit", "Real alcoholic vs heavy drinker", "Profound psychic change", "Carl Jung verdict"],
    ),
    BigBookChapter(
        chapter_num=3,
        title="More About Alcoholism",
        pages="30–43",
        main_problem="The Mental Obsession — the subtle delusion and strange mental blank spot that precedes the first drink.",
        mechanism="Eradication of the illusion of control; recognizing that knowledge and willpower fail completely at the moment of choice.",
        relevant_steps=[1],
        recurring_concepts=["Illusion of control", "Strange mental blank spot", "Jaywalker analogy", "No effective mental defense"],
    ),
    BigBookChapter(
        chapter_num=4,
        title="We Agnostics",
        pages="44–57",
        main_problem="Intellectual prejudice, pride, and skepticism toward religious dogma preventing spiritual connection.",
        mechanism="Non-dogmatic spiritual foundation ('God as we understood Him'); tapping the deep inner spiritual resource.",
        relevant_steps=[2],
        recurring_concepts=["Spiritual prejudice", "Willing suspension of disbelief", "Realm of power", "Deep down inner resource"],
    ),
    BigBookChapter(
        chapter_num=5,
        title="How It Works",
        pages="58–71",
        main_problem="Self-centeredness and self-will run riot ('the actor who wants to run the whole show'); fear, resentment, dishonesty.",
        mechanism="Rigorous honesty; Step Three decision; 3-column moral inventory analyzing Resentments, Fears, and Harms.",
        relevant_steps=[3, 4],
        recurring_concepts=["Selfishness as root cause", "Actor and stage", "Three-column inventory", "Prayer for the resentful"],
    ),
    BigBookChapter(
        chapter_num=6,
        title="Into Action",
        pages="72–88",
        main_problem="Guilt, hidden secrets, damaged interpersonal relationships, emotional defects, and reactive daily drift.",
        mechanism="Step 5 verbal admission; Steps 6–7 character defect removal; Steps 8–9 direct amends; Step 10 daily maintenance; Step 11 morning/evening cadence.",
        relevant_steps=[5, 6, 7, 8, 9, 10, 11],
        recurring_concepts=["Pocket of pride", "Direct restitution", "Ninth Step Promises", "Emotional sobriety", "Morning meditation cadence"],
    ),
    BigBookChapter(
        chapter_num=7,
        title="Working With Others",
        pages="89–103",
        main_problem="Vulnerability to relapse during boredom, stress, or emotional downturns; lingering self-absorption.",
        mechanism="Intensive 12th Step work with other alcoholics as the sovereign immunity against relapse; non-coercive approach.",
        relevant_steps=[12],
        recurring_concepts=["Sovereign immunity", "Twelfth Step work", "Attraction not promotion", "No financial entanglement", "Letting prospect diagnose"],
    ),
    BigBookChapter(
        chapter_num=8,
        title="To Wives",
        pages="104–121",
        main_problem="Family codependency, resentment, fear of future wreckage, and mistrust.",
        mechanism="Patience; mutual spiritual growth; letting go of policing and surveillance.",
        relevant_steps=[8, 9, 12],
        recurring_concepts=["Family illness", "Ceasing surveillance", "Spiritual growth takes time"],
    ),
    BigBookChapter(
        chapter_num=9,
        title="The Family Afterward",
        pages="122–135",
        main_problem="Post-sobriety friction, unrealistic expectations of overnight perfection, financial distress.",
        mechanism="Spiritual principles applied in the home; family members cleaning their side of the street.",
        relevant_steps=[8, 9, 10, 12],
        recurring_concepts=["Patience over perfection", "Household spiritual atmosphere", "Rebuilding trust through action"],
    ),
    BigBookChapter(
        chapter_num=10,
        title="To Employers",
        pages="136–150",
        main_problem="Workplace dishonesty, lost productivity, stigma, and firing vs rehabilitating employees.",
        mechanism="Professional transparency, clear performance standards, non-punitive support for treatment.",
        relevant_steps=[8, 9, 12],
        recurring_concepts=["Workplace transparency", "Clear boundaries", "Economic salvage"],
    ),
    BigBookChapter(
        chapter_num=11,
        title="A Vision For You",
        pages="151–164",
        main_problem="Isolation, loneliness, and lack of community after stopping drinking.",
        mechanism="Building fellowship where none exists; joyful and purposeful life in the real world.",
        relevant_steps=[12],
        recurring_concepts=["Fellowship of the Spirit", "Abandonment to God", "Community building", "Give freely of what you find"],
    ),
]

STEPS_MAP: list[StepEntry] = [
    StepEntry(
        step_num=1,
        title="Admitted powerlessness over alcohol—that our lives had become unmanageable.",
        practical_function="Complete ego deflation; destruction of the delusion of control; admission of biological/psychological defeat.",
        big_book_source="Doctor's Opinion (xxiii–xxxii), Ch. 1 (pp. 1–16), Ch. 3 (pp. 30–43)",
        twelve_twelve_essay="Surrender is the foundation of freedom. The obsession to control drinking must be eliminated at the root.",
        failure_mode_prevented="Delusion of Control / Willpower Fallacy: Prevents repeated relapse cycles caused by belief in moderation or situational fixes.",
    ),
    StepEntry(
        step_num=2,
        title="Came to believe that a Power greater than ourselves could restore us to sanity.",
        practical_function="Cognitive opening; willing suspension of cynicism; acknowledging need for an external stabilizing reference point.",
        big_book_source="Ch. 4 'We Agnostics' (pp. 44–57), Appendix II (pp. 567–568)",
        twelve_twelve_essay="Addresses intellectual pride, spiritual prejudice, and belligerent denial. Defines insanity as repeating destructive behavior expecting different results.",
        failure_mode_prevented="Nihilistic Despair / Intellectual Pride: Prevents spiritual isolation and the closed-minded rejection of help.",
    ),
    StepEntry(
        step_num=3,
        title="Made a decision to turn our will and our lives over to the care of God as we understood Him.",
        practical_function="Operational surrender of self-centered control; conscious decision to align will with spiritual principles.",
        big_book_source="Ch. 5 'How It Works' (pp. 58–63)",
        twelve_twelve_essay="Clarifies the role of will: we use our will to align with spiritual principles rather than using self-will to manipulate reality.",
        failure_mode_prevented="Self-Will Run Riot: Prevents chronic frustration, resentment, and manipulation of people and circumstances.",
    ),
    StepEntry(
        step_num=4,
        title="Made a searching and fearless moral inventory of ourselves.",
        practical_function="Systematic forensic audit of life patterns: Resentments, Fears, Harms, and Sexual/Relational conduct.",
        big_book_source="Ch. 5 'How It Works' (pp. 63–71)",
        twelve_twelve_essay="Analyzes the fundamental instincts (security, social, sexual) and how their distortion produces crippling resentments and irrational fears.",
        failure_mode_prevented="Victimhood & Denial: Prevents toxic blame-shifting, unresolved emotional debt, and unconscious self-sabotage.",
    ),
    StepEntry(
        step_num=5,
        title="Admitted to God, to ourselves, and to another human being the exact nature of our wrongs.",
        practical_function="Total verbal disclosure of inventory to God, self, and another human being; shatters terminal isolation.",
        big_book_source="Ch. 6 'Into Action' (pp. 72–75)",
        twelve_twelve_essay="Emphasizes the psychological breakthrough of full transparency. Breaks the 'pocket of pride' and dissolves isolating shame.",
        failure_mode_prevented="Terminal Isolation & Toxic Secrets: Prevents the solitary harboring of hidden guilt that triggers relapse.",
    ),
    StepEntry(
        step_num=6,
        title="Were entirely ready to have God remove all these defects of character.",
        practical_function="Cultivation of willingness to release character defects (pride, anger, greed, sloth, envy, gluttony).",
        big_book_source="Ch. 6 'Into Action' (p. 76)",
        twelve_twelve_essay="Highlights the difficulty of letting go of familiar defects that provide perverse comfort or pleasure. Stresses progress over perfection.",
        failure_mode_prevented="Defective Comfort Zones: Prevents clinging to destructive coping habits out of fear of living without them.",
    ),
    StepEntry(
        step_num=7,
        title="Humbly asked Him to remove our shortcomings.",
        practical_function="Active practice of humility; recognizing that true strength flows from alignment rather than ego demand.",
        big_book_source="Ch. 6 'Into Action' (p. 76)",
        twelve_twelve_essay="Bill W.'s defining essay on humility as the cornerstone of character and emotional sobriety.",
        failure_mode_prevented="Ego Reconstruction: Prevents the covert return of grandiosity and self-righteousness.",
    ),
    StepEntry(
        step_num=8,
        title="Made a list of all persons we had harmed, and became willing to make amends to them all.",
        practical_function="Complete listing of all persons harmed and preparation for restorative action; shift from grievance to restitution.",
        big_book_source="Ch. 6 'Into Action' (pp. 76–77)",
        twelve_twelve_essay="Distinguishes between cataloging our own wrongs and rehashing other people's faults. Demands rigorous willingness before action.",
        failure_mode_prevented="Selective Amnesia & Spite: Prevents lingering animosity and self-justifying rationalizations.",
    ),
    StepEntry(
        step_num=9,
        title="Made direct amends to such people wherever possible, except when to do so would injure them or others.",
        practical_function="Concrete, restorative restitution to individuals and institutions, subject to the safety of others.",
        big_book_source="Ch. 6 'Into Action' (pp. 77–84)",
        twelve_twelve_essay="Practical guidelines on timing, prudence, discretion, financial repayment, and avoiding harm to innocent third parties.",
        failure_mode_prevented="Avoidance / Reckless Confession: Prevents damaging others under the guise of 'clearing one's conscience.'",
    ),
    StepEntry(
        step_num=10,
        title="Continued to take personal inventory and when we were wrong promptly admitted it.",
        practical_function="Real-time emotional maintenance: spot-checking resentment, fear, dishonesty, and selfishness; prompt admission.",
        big_book_source="Ch. 6 'Into Action' (pp. 84–85)",
        twelve_twelve_essay="Focuses on 'emotional sobriety.' Developing an automatic habit of catching emotional disturbances before they metastasize.",
        failure_mode_prevented="Emotional Drift & Relapse Build-up: Prevents slow accumulation of unexamined daily resentments and stress.",
    ),
    StepEntry(
        step_num=11,
        title="Sought through prayer and meditation to improve our conscious contact with God as we understood Him, praying only for knowledge of His will for us and the power to carry that out.",
        practical_function="Daily discipline of conscious contact: morning constructive planning, evening review, pausing when agitated.",
        big_book_source="Ch. 6 'Into Action' (pp. 85–88)",
        twelve_twelve_essay="Bill W.'s expansive essay on meditation techniques (the Prayer of St. Francis), seeking knowledge of God's will and power to carry it out.",
        failure_mode_prevented="Spiritual Stagnation / Reactive Living: Prevents slipping back into reactive autopilot, panic, and self-delusion.",
    ),
    StepEntry(
        step_num=12,
        title="Having had a spiritual awakening as the result of these steps, we tried to carry this message to alcoholics, and to practice these principles in all our affairs.",
        practical_function="Carrying the message to others and practicing these principles in all affairs; complete outward altruistic orientation.",
        big_book_source="Ch. 7 'Working With Others' (pp. 89–103)",
        twelve_twelve_essay="Synthesizes the entire journey: unconditional giving without expectation of reward; love and service as the ultimate stabilizers.",
        failure_mode_prevented="Relapse through Inward Collapse: Protects sobriety by converting personal recovery into life-saving service for others.",
    ),
]

TRADITIONS_MAP: list[TraditionEntry] = [
    TraditionEntry(
        tradition_num=1,
        short_form="Our common welfare should come first; personal recovery depends upon A.A. unity.",
        long_form_summary="Individual recovery is impossible without fellowship survival. Group unity overrides individual preference.",
        failure_mode_prevented="Factionalism & Balkanization: Prevents internal splintering, ego clashes, and group dissolution.",
        governance_seam="Subordinates individual demands to the preservation of the fellowship.",
    ),
    TraditionEntry(
        tradition_num=2,
        short_form="For our group purpose there is but one ultimate authority—a loving God as He may express Himself in our group conscience. Our leaders are but trusted servants; they do not govern.",
        long_form_summary="Leadership in A.A. functions through sacrifice, guidance, and consultation, never coercion or executive fiat.",
        failure_mode_prevented="Autocracy & Personality Cults: Prevents power-seeking, hierarchy, and dominant personalities dictating policy.",
        governance_seam="The General Service Conference and Group Conscience express collective spiritual discernment.",
    ),
    TraditionEntry(
        tradition_num=3,
        short_form="The only requirement for A.A. membership is a desire to stop drinking.",
        long_form_summary="Total inclusion: no fees, no background checks, no moral tests, no religious conformity.",
        failure_mode_prevented="Gatekeeping & Exclusivity: Prevents moral snobbery, sectarian exclusion, and social stratification.",
        governance_seam="Removes all barriers between the suffering alcoholic and the fellowship.",
    ),
    TraditionEntry(
        tradition_num=4,
        short_form="Each group should be autonomous except in matters affecting other groups or A.A. as a whole.",
        long_form_summary="Groups may experiment freely with format and local customs, provided they do not harm fellowship reputation.",
        failure_mode_prevented="Rigid Centralization / Rogue Harm: Balances local operational freedom against collective institutional integrity.",
        governance_seam="Autonomy ends where harm to neighboring groups or A.A. as a whole begins.",
    ),
    TraditionEntry(
        tradition_num=5,
        short_form="Each group has but one primary purpose—to carry its message to the alcoholic who still suffers.",
        long_form_summary="Singular operational focus maximizes effectiveness; broad scope causes catastrophic failure.",
        failure_mode_prevented="Mission Drift & Dilution: Prevents A.A. from becoming a general clinic, social club, political committee, or church.",
        governance_seam="Keeps every resource focused exclusively on 12th Step work.",
    ),
    TraditionEntry(
        tradition_num=6,
        short_form="An A.A. group ought never endorse, finance, or lend the A.A. name to any related facility or outside enterprise, lest problems of money, property, and prestige divert us from our primary purpose.",
        long_form_summary="Strict separation of A.A. from hospitals, retreat centers, treatment facilities, and outside literature. Cooperation without affiliation.",
        failure_mode_prevented="Corporate Co-optation & Commercialization: Prevents commercial capture, brand contamination, and legal entanglement.",
        governance_seam="Foundation for H&I / Treatment Committee boundaries.",
    ),
    TraditionEntry(
        tradition_num=7,
        short_form="Every A.A. group ought to be fully self-supporting, declining outside contributions.",
        long_form_summary="A.A. accepts donations only from its own members, with strict contribution limits. Declines outside grants or gifts.",
        failure_mode_prevented="Financial Dependence & Outside Influence: Prevents wealthy donors or state agencies from controlling fellowship policy.",
        governance_seam="Guarantees absolute independence and spiritual integrity.",
    ),
    TraditionEntry(
        tradition_num=8,
        short_form="Alcoholics Anonymous should remain forever non-professional, but our service centers may employ special workers.",
        long_form_summary="Twelfth Step work is freely given and can never be bought or sold. Special workers may be hired for routine tasks.",
        failure_mode_prevented="Commercialization of Recovery: Prevents monetizing sponsorship or turning spiritual sharing into paid therapy.",
        governance_seam="Separates 12th Step spiritual fellowship from paid professional services.",
    ),
    TraditionEntry(
        tradition_num=9,
        short_form="A.A., as such, ought never be organized; but we may create service boards or committees directly responsible to those they serve.",
        long_form_summary="A.A. has no top-down command structure, no executive enforcement power, and no disciplinary committees.",
        failure_mode_prevented="Bureaucracy & Authoritarianism: Prevents the rise of an institutional hierarchy enforcing obedience.",
        governance_seam="Inverts the traditional pyramid: Groups hold ultimate power; G.S.O. and Trustees are servants.",
    ),
    TraditionEntry(
        tradition_num=10,
        short_form="Alcoholics Anonymous has no opinion on outside issues; hence the A.A. name ought never be drawn into public controversy.",
        long_form_summary="Total neutrality on politics, religion, medicine, public health mandates, and international disputes.",
        failure_mode_prevented="Partisan Splintering & Public Backlash: Protects fellowship reputation from being weaponized in cultural wars.",
        governance_seam="Preserves safe harbor for individuals of all viewpoints.",
    ),
    TraditionEntry(
        tradition_num=11,
        short_form="Our public relations policy is based on attraction rather than promotion; we need always maintain personal anonymity at the level of press, radio, and films.",
        long_form_summary="Humility at the public level. We do not boast, advertise, or use celebrity endorsements. Personal anonymity protects the fellowship.",
        failure_mode_prevented="Sensationalism & Celebrity Vulnerability: Prevents fellowship damage when a prominent public member relapses.",
        governance_seam="Mandates strict modesty in all public communications.",
    ),
    TraditionEntry(
        tradition_num=12,
        short_form="Anonymity is the spiritual foundation of all our traditions, ever reminding us to place principles before personalities.",
        long_form_summary="Anonymity is profound humility. It demands self-effacement, equal standing, and subordination of ambition to principles.",
        failure_mode_prevented="Ego Domination & Hubris: Prevents any individual from placing personal prestige above the collective message.",
        governance_seam="Principles before personalities governs all Monad operations.",
    ),
]


POLICIES_MAP: list[PolicyEntry] = [
    PolicyEntry(
        key="p-11",
        title="The A.A. Member—Medications and Other Drugs",
        authority_source="A.A. General Service Conference Approved Pamphlet (P-11 / P-87)",
        core_rule="Prescribed psychiatric and somatic medications taken under the care of an informed physician do NOT compromise A.A. sobriety.",
        demarcation="A.A. members are NOT physicians and are explicitly prohibited from offering amateur medical advice or telling members to stop prescribed medications.",
        practical_application="Full medical honesty with prescribing doctors; zero medical advice given by sponsors or group members.",
    ),
    PolicyEntry(
        key="p-35",
        title="Problems Other Than Alcohol",
        authority_source="A.A. General Service Conference Approved Pamphlet (P-35 / Tradition 3 & 5)",
        core_rule="A.A. protects its singleness of purpose to survive. Anyone who has a desire to stop drinking is welcomed as an A.A. member.",
        demarcation="A.A. is not a general drug addiction or psychiatric treatment facility. Dual-addicted members participate freely on the common ground of alcoholism.",
        practical_application="Focus shared meeting language on recovery from alcoholism while welcoming those with multiple dependencies.",
    ),
    PolicyEntry(
        key="hi-btg",
        title="Hospitals & Institutions / Bridging the Gap",
        authority_source="A.A. World Services Guidelines (MG-14 / MG-05)",
        core_rule="12th Step institutional panels and Bridging the Gap serve solely as temporary bridges connecting patients in treatment to outside meetings.",
        demarcation="Strictly voluntary, non-professional, non-residential, non-custodial, and non-financial. Zero involvement in hospital administration or discharge planning.",
        practical_application="Volunteers meet patients, take them to their first outside meetings, introduce them to members, and step aside.",
    ),
    PolicyEntry(
        key="peer-vs-clinical",
        title="Peer 12th Step Service vs. Clinical Therapy",
        authority_source="A.A. Traditions (Tradition 8 & 6) / Doctrine 043",
        core_rule="Fellowship service is based on mutual identification, shared suffering, and Step spiritual recovery, free of commercial fees.",
        demarcation="Clinicians diagnose pathology, prescribe medications, and provide billable psychotherapy. 12th Step peers share experience, strength, and hope.",
        practical_application="Sponsors and peers never attempt to practice unlicensed psychotherapy, clinical counseling, or crisis triage.",
    ),
    PolicyEntry(
        key="home-first",
        title="Home First Resource Boundaries",
        authority_source="Doctrine 043 (Ground Plane Operational Handoff)",
        core_rule="The domestic home remains a home first, and a recovery-support resource second.",
        demarcation="No conversion of domestic residence into a crash pad, sober house, or emergency shelter. Zero taking financial or legal custody of external crises.",
        practical_application="Recovery service occurs in meetings, intergroups, and designated community facilities; home remains protected sanctuary.",
    ),
]


class RecoveryIndex:
    """Index interface for recovery corpus queries."""

    def __init__(self) -> None:
        self.chapters = {c.chapter_num: c for c in BIG_BOOK_CHAPTERS}
        self.steps = {s.step_num: s for s in STEPS_MAP}
        self.traditions = {t.tradition_num: t for t in TRADITIONS_MAP}
        self.policies = {p.key: p for p in POLICIES_MAP}

    def get_chapter(self, num: int) -> Optional[BigBookChapter]:
        return self.chapters.get(num)

    def get_step(self, num: int) -> Optional[StepEntry]:
        return self.steps.get(num)

    def get_tradition(self, num: int) -> Optional[TraditionEntry]:
        return self.traditions.get(num)

    def get_policy(self, key: str) -> Optional[PolicyEntry]:
        return self.policies.get(key)

    def search(self, query: str) -> dict[str, list[dict[str, Any]]]:
        q = query.lower()
        results: dict[str, list[dict[str, Any]]] = {
            "chapters": [],
            "steps": [],
            "traditions": [],
            "policies": [],
        }
        for chap in self.chapters.values():
            if q in chap.title.lower() or q in chap.main_problem.lower() or q in chap.mechanism.lower() or any(q in c.lower() for c in chap.recurring_concepts):
                results["chapters"].append(asdict(chap))
        for step in self.steps.values():
            if q in step.title.lower() or q in step.practical_function.lower() or q in step.failure_mode_prevented.lower() or q in step.twelve_twelve_essay.lower():
                results["steps"].append(asdict(step))
        for trad in self.traditions.values():
            if q in trad.short_form.lower() or q in trad.long_form_summary.lower() or q in trad.failure_mode_prevented.lower() or q in trad.governance_seam.lower():
                results["traditions"].append(asdict(trad))
        for pol in self.policies.values():
            if q in pol.key.lower() or q in pol.title.lower() or q in pol.core_rule.lower() or q in pol.demarcation.lower() or q in pol.practical_application.lower():
                results["policies"].append(asdict(pol))
        return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Query A.A. Recovery Research Index")
    parser.add_argument("--step", type=int, help="Query specific Step (1-12)")
    parser.add_argument("--tradition", type=int, help="Query specific Tradition (1-12)")
    parser.add_argument("--chapter", type=int, help="Query specific Big Book Chapter (0-11)")
    parser.add_argument("--policy", type=str, help="Query specific Policy/Boundary (p-11, p-35, hi-btg, peer-vs-clinical, home-first)")
    parser.add_argument("--search", type=str, help="Search terms across entire recovery corpus")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    args = parser.parse_args()

    index = RecoveryIndex()

    if args.step:
        step = index.get_step(args.step)
        if not step:
            print(f"Step {args.step} not found (must be 1-12).", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(asdict(step), indent=2))
        else:
            print(f"=== STEP {step.step_num} ===")
            print(f"Title: {step.title}")
            print(f"Practical Function: {step.practical_function}")
            print(f"Big Book Source: {step.big_book_source}")
            print(f"12&12 Essay: {step.twelve_twelve_essay}")
            print(f"Failure Mode Prevented: {step.failure_mode_prevented}")
        return 0

    if args.tradition:
        trad = index.get_tradition(args.tradition)
        if not trad:
            print(f"Tradition {args.tradition} not found (must be 1-12).", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(asdict(trad), indent=2))
        else:
            print(f"=== TRADITION {trad.tradition_num} ===")
            print(f"Short Form: {trad.short_form}")
            print(f"Long Form Summary: {trad.long_form_summary}")
            print(f"Failure Mode Prevented: {trad.failure_mode_prevented}")
            print(f"Governance Seam: {trad.governance_seam}")
        return 0

    if args.chapter is not None:
        chap = index.get_chapter(args.chapter)
        if not chap:
            print(f"Chapter {args.chapter} not found (must be 0-11).", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(asdict(chap), indent=2))
        else:
            label = "Doctor's Opinion" if chap.chapter_num == 0 else f"Chapter {chap.chapter_num}: {chap.title}"
            print(f"=== {label} (pp. {chap.pages}) ===")
            print(f"Main Problem: {chap.main_problem}")
            print(f"Mechanism: {chap.mechanism}")
            print(f"Relevant Steps: {chap.relevant_steps}")
            print(f"Recurring Concepts: {', '.join(chap.recurring_concepts)}")
        return 0

    if args.policy:
        pol = index.get_policy(args.policy)
        if not pol:
            print(f"Policy '{args.policy}' not found (options: p-11, p-35, hi-btg, peer-vs-clinical, home-first).", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(asdict(pol), indent=2))
        else:
            print(f"=== POLICY: {pol.title} ===")
            print(f"Authority: {pol.authority_source}")
            print(f"Core Rule: {pol.core_rule}")
            print(f"Demarcation: {pol.demarcation}")
            print(f"Practical Application: {pol.practical_application}")
        return 0

    if args.search:
        results = index.search(args.search)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print(f"Search results for '{args.search}':")
            print(f"  Chapters matched: {len(results['chapters'])}")
            for c in results["chapters"]:
                print(f"    - Ch. {c['chapter_num']}: {c['title']} (pp. {c['pages']})")
            print(f"  Steps matched: {len(results['steps'])}")
            for s in results["steps"]:
                print(f"    - Step {s['step_num']}: {s['title'][:60]}...")
            print(f"  Traditions matched: {len(results['traditions'])}")
            for t in results["traditions"]:
                print(f"    - Tradition {t['tradition_num']}: {t['short_form'][:60]}...")
            print(f"  Policies & Boundaries matched: {len(results['policies'])}")
            for p in results["policies"]:
                print(f"    - {p['title']} [{p['key']}]")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
