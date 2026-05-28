"""Worksite safety officer assistant.

Run it with:
    python safety_agent.py

This tool supports quick hazard assessment, control suggestions, checklist
review, toolbox talk prompts, and a simple action report.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from textwrap import fill


LIKELIHOOD_LABELS = {
    1: "Rare",
    2: "Unlikely",
    3: "Possible",
    4: "Likely",
    5: "Almost certain",
}

SEVERITY_LABELS = {
    1: "Minor first aid",
    2: "Medical treatment",
    3: "Lost time injury",
    4: "Serious injury",
    5: "Fatality or multiple serious injuries",
}


@dataclass
class Hazard:
    task: str
    hazard: str
    people_at_risk: str
    likelihood: int
    severity: int
    controls: list[str] = field(default_factory=list)

    @property
    def score(self) -> int:
        return self.likelihood * self.severity

    @property
    def level(self) -> str:
        if self.score >= 16:
            return "High"
        if self.score >= 8:
            return "Medium"
        return "Low"

    @property
    def action(self) -> str:
        if self.level == "High":
            return "Stop or pause the task until stronger controls are in place."
        if self.level == "Medium":
            return "Improve controls and brief the team before work continues."
        return "Continue with normal supervision and routine checks."


CONTROL_LIBRARY = {
    "fall": [
        "Use certified fall protection and inspect harnesses before use.",
        "Install guardrails, toe boards, covers, or exclusion zones at edges and openings.",
        "Confirm workers are trained for work at height and rescue arrangements are ready.",
    ],
    "height": [
        "Use a suitable access platform instead of standing on unstable surfaces.",
        "Keep three points of contact on ladders and secure ladders before use.",
        "Stop work in unsafe wind, rain, or poor visibility.",
    ],
    "electric": [
        "Isolate, lock out, and tag out energy sources before work starts.",
        "Use tested equipment, correct grounding, and dry working conditions.",
        "Keep unqualified workers outside the electrical work area.",
    ],
    "lifting": [
        "Check the lifting plan, load weight, rigging gear, and crane capacity.",
        "Keep workers clear of suspended loads and use a banksman or signaler.",
        "Inspect slings, hooks, shackles, and lifting points before each lift.",
    ],
    "vehicle": [
        "Separate pedestrians and moving plant with barriers or marked routes.",
        "Use spotters, reversing alarms, lights, and agreed traffic flow.",
        "Set speed limits and keep blind spots clear.",
    ],
    "chemical": [
        "Review the safety data sheet and use correct PPE.",
        "Label containers, provide ventilation, and keep spill kits nearby.",
        "Store incompatible chemicals separately.",
    ],
    "fire": [
        "Remove ignition sources and combustible materials from the work area.",
        "Keep suitable extinguishers available and inspect hot-work permits.",
        "Maintain clear emergency exits and assembly routes.",
    ],
    "machine": [
        "Keep machine guards in place and test emergency stops.",
        "Lock out equipment before maintenance or clearing jams.",
        "Allow only trained and authorized operators to use the equipment.",
    ],
    "confined": [
        "Use a confined-space permit and test the atmosphere before entry.",
        "Provide ventilation, standby rescue support, and communication.",
        "Control engulfment, toxic gas, and oxygen-deficiency risks.",
    ],
    "excavation": [
        "Locate underground services before digging.",
        "Use shoring, benching, or battering to prevent collapse.",
        "Keep spoil, vehicles, and materials away from excavation edges.",
    ],
    "housekeeping": [
        "Clear walkways, remove trip hazards, and manage cables properly.",
        "Store materials safely and keep emergency access routes open.",
        "Clean spills quickly and use warning signs until dry.",
    ],
}

GENERAL_CONTROLS = [
    "Confirm the method statement and risk assessment match the actual task.",
    "Brief the crew before work starts and confirm everyone understands the controls.",
    "Use the correct PPE for the task and verify it is in good condition.",
    "Assign a responsible person to inspect controls during the job.",
]

CHECKLIST = [
    "Access routes are clear, stable, and well lit.",
    "Emergency exits, muster points, and first-aid arrangements are known.",
    "Workers have the correct PPE and task training.",
    "Tools and equipment are inspected and suitable for the job.",
    "Energy sources are isolated where needed.",
    "Work areas are separated from pedestrians and other trades.",
    "Weather, visibility, noise, heat, and fatigue risks are considered.",
    "Permits are in place for hot work, confined space, excavation, or lifting.",
]


def ask(prompt: str) -> str:
    while True:
        answer = input(prompt).strip()
        if answer:
            return answer
        print("Please enter a value.")


def ask_score(prompt: str, labels: dict[int, str]) -> int:
    print(prompt)
    for number, label in labels.items():
        print(f"  {number}. {label}")

    while True:
        answer = input("Choose 1-5: ").strip()
        if answer.isdigit() and 1 <= int(answer) <= 5:
            return int(answer)
        print("Enter a number from 1 to 5.")


def suggest_controls(text: str) -> list[str]:
    lowered = text.lower()
    controls: list[str] = []

    for keyword, suggestions in CONTROL_LIBRARY.items():
        if keyword in lowered:
            controls.extend(suggestions)

    if not controls:
        controls.extend(GENERAL_CONTROLS)

    return list(dict.fromkeys(controls))


def assess_hazard() -> Hazard:
    print("\nNew Hazard Assessment")
    task = ask("Task or work activity: ")
    hazard_text = ask("Main hazard observed: ")
    people = ask("People at risk: ")
    likelihood = ask_score("Likelihood if no extra controls are added:", LIKELIHOOD_LABELS)
    severity = ask_score("Worst credible severity:", SEVERITY_LABELS)
    controls = suggest_controls(f"{task} {hazard_text}")

    hazard = Hazard(
        task=task,
        hazard=hazard_text,
        people_at_risk=people,
        likelihood=likelihood,
        severity=severity,
        controls=controls,
    )

    print_hazard(hazard)
    return hazard


def print_hazard(hazard: Hazard) -> None:
    print("\nRisk Summary")
    print(f"Task: {hazard.task}")
    print(f"Hazard: {hazard.hazard}")
    print(f"People at risk: {hazard.people_at_risk}")
    print(
        "Risk score: "
        f"{hazard.score} ({hazard.level}) "
        f"[Likelihood {hazard.likelihood} x Severity {hazard.severity}]"
    )
    print(f"Action: {hazard.action}")
    print("Suggested controls:")
    for control in hazard.controls:
        print(f"- {control}")


def run_checklist() -> None:
    print("\nPre-Task Safety Checklist")
    issues: list[str] = []

    for item in CHECKLIST:
        answer = input(f"{item} [y/n]: ").strip().lower()
        if answer not in {"y", "yes"}:
            issues.append(item)

    if not issues:
        print("\nChecklist passed. Continue monitoring the work area.")
        return

    print("\nItems needing action before or during work:")
    for issue in issues:
        print(f"- {issue}")


def toolbox_talk() -> None:
    topic = ask("\nToolbox talk topic or task: ")
    controls = suggest_controls(topic)

    print("\nToolbox Talk Prompt")
    print(fill(f"Today we are discussing: {topic}.", width=78))
    print("Key points:")
    print("- What can hurt someone during this task?")
    print("- Who is exposed and how will we separate them from the hazard?")
    for control in controls[:4]:
        print(f"- {control}")
    print("- Stop work and report changes, near misses, or unsafe conditions immediately.")


def show_report(hazards: list[Hazard]) -> None:
    print("\nSafety Agent Report")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    if not hazards:
        print("No hazards assessed yet.")
        return

    high_count = sum(1 for hazard in hazards if hazard.level == "High")
    medium_count = sum(1 for hazard in hazards if hazard.level == "Medium")
    low_count = sum(1 for hazard in hazards if hazard.level == "Low")

    print(f"Total hazards: {len(hazards)}")
    print(f"High: {high_count} | Medium: {medium_count} | Low: {low_count}")

    for index, hazard in enumerate(hazards, start=1):
        print(f"\n{index}. {hazard.task}")
        print(f"   Hazard: {hazard.hazard}")
        print(f"   Risk: {hazard.score} ({hazard.level})")
        print(f"   Action: {hazard.action}")


def main() -> None:
    hazards: list[Hazard] = []

    print("Worksite Safety Officer Agent")
    print("This assistant supports safety decisions but does not replace a competent person.")

    while True:
        print("\nMenu")
        print("1. Assess a hazard")
        print("2. Run pre-task checklist")
        print("3. Generate toolbox talk")
        print("4. Show safety report")
        print("5. Exit")

        choice = input("Choose an option: ").strip()

        if choice == "1":
            hazards.append(assess_hazard())
        elif choice == "2":
            run_checklist()
        elif choice == "3":
            toolbox_talk()
        elif choice == "4":
            show_report(hazards)
        elif choice == "5":
            print("Stay safe. Goodbye!")
            break
        else:
            print("Choose a number from 1 to 5.")


if __name__ == "__main__":
    main()
