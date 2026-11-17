#!/usr/bin/env python3
"""
Capture real Claude API responses for the "Agentic Loop" hands-on lab.

What it does
  1. Sends two versions of the same request (vague vs. specific) to Claude and
     saves how Claude plans each one.
  2. Runs a real tool-use agent loop: Claude gets three tools (list_files,
     read_file, ask_user) over a small sample feedback folder, and the script
     records every step - plan, tool call, tool result, adjustment, final answer.
  3. Writes everything into index.html (from lab_template.html) so the lab is
     a single self-contained file you can paste or upload into a Rise 360
     Code Block. No API calls happen in the course itself.

Setup
  pip install anthropic
  export ANTHROPIC_API_KEY="sk-ant-..."        # Windows: set ANTHROPIC_API_KEY=...
  python capture_lab_data.py

Options
  CLAUDE_MODEL=claude-haiku-5-5 python capture_lab_data.py   # cheaper/faster model
"""

import datetime
import json
import os
import pathlib
import sys

try:
    import anthropic
except ImportError:
    sys.exit("Missing package. Run: pip install anthropic")

HERE = pathlib.Path(__file__).resolve().parent
TEMPLATE = HERE / "lab_template.html"
OUT_HTML = HERE / "index.html"
OUT_JSON = HERE / "lab_data.json"
PLACEHOLDER = "/*__LAB_DATA__*/null"

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5")
MAX_TURNS = 10  # hard limit on the agent loop, as Anthropic recommends

# --------------------------------------------------------------------------
# Sample "feedback folder" the agent works in. Fictional data.
# The September file deliberately has no comments column, so the agent has
# to Check, notice the problem, and Adjust (or Ask).
# --------------------------------------------------------------------------
FEEDBACK_FILES = {
    "q3_july.csv": (
        "id,rating,comment\n"
        "101,2,The dashboard takes forever to load in the mornings\n"
        "102,5,Support fixed my issue in ten minutes - amazing\n"
        "103,3,I was charged twice and the invoice page is confusing\n"
        "104,2,Pages load slowly when I filter reports\n"
        "105,4,Love the new export button\n"
        "106,1,Mobile app crashes every time I upload a photo\n"
    ),
    "q3_august.csv": (
        "id,rating,comment\n"
        "201,2,Still slow. Reports take a minute to open\n"
        "202,3,Billing page doesn't explain the new plan tiers\n"
        "203,5,Your support team is the best part of the product\n"
        "204,2,The app crashed twice during a client demo\n"
        "205,2,Load times are hurting my team's productivity\n"
        "206,4,Support walked me through setup - very patient\n"
    ),
    "q3_september.csv": (
        "id,rating\n"
        "301,3\n302,2\n303,4\n304,2\n305,5\n306,3\n"
    ),
}

# What the "user" answers if Claude stops to ask a question (the checkpoint).
CANNED_USER_ANSWER = (
    "Good catch. Leave September out of the themes, but mention its average "
    "rating in one line so my manager knows it exists."
)

# --------------------------------------------------------------------------
# Part 1: vague vs. specific request
# --------------------------------------------------------------------------
PLAN_SYSTEM = (
    "You are an AI agent with tools to list and read files in the user's "
    "'feedback' folder. Do not act yet. Reply only with a short numbered plan "
    "and any questions you need answered before starting. Under 120 words."
)

PROMPTS = {
    "vague": "Look into our customer feedback.",
    "specific": (
        "Summarize our Q3 customer feedback into a one-page brief for my "
        "manager: the top three themes, how many comments mention each, and "
        "one short quote per theme. Use only the files in the feedback folder."
    ),
}

# --------------------------------------------------------------------------
# Part 2: the agent loop
# --------------------------------------------------------------------------
AGENT_SYSTEM = (
    "You are an AI agent working in the user's 'feedback' folder using tools. "
    "Before your first tool call, state a brief numbered plan. After each tool "
    "result, say in one or two sentences what you found and whether your plan "
    "changes. If something blocks the task and only the user can decide, use "
    "ask_user instead of guessing. Finish with the brief in Markdown, under "
    "250 words."
)

TOOLS = [
    {
        "name": "list_files",
        "description": "List the files in the user's feedback folder.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "read_file",
        "description": "Read one file from the feedback folder. Returns its full text (CSV).",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string", "description": "File name, e.g. q3_july.csv"}},
            "required": ["name"],
        },
    },
    {
        "name": "ask_user",
        "description": "Ask the user a question when only they can decide how to proceed. Returns their answer.",
        "input_schema": {
            "type": "object",
            "properties": {"question": {"type": "string"}},
            "required": ["question"],
        },
    },
]


def run_tool(name, args):
    """Execute a tool locally and return its text result."""
    if name == "list_files":
        return "\n".join(FEEDBACK_FILES)
    if name == "read_file":
        fname = (args or {}).get("name", "")
        return FEEDBACK_FILES.get(fname, f"Error: no file named '{fname}'.")
    if name == "ask_user":
        return CANNED_USER_ANSWER
    return f"Error: unknown tool '{name}'."


def text_of(content):
    return "\n".join(b.text for b in content if b.type == "text").strip()


def usage_of(resp):
    return {"input": resp.usage.input_tokens, "output": resp.usage.output_tokens}


def capture_prompt_comparison(client):
    results = {}
    for key, prompt in PROMPTS.items():
        print(f"  - {key} request...")
        resp = client.messages.create(
            model=MODEL,
            max_tokens=400,
            system=PLAN_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        results[key] = {"prompt": prompt, "response": text_of(resp.content), "usage": usage_of(resp)}
    return results


def classify_text(turn, had_tool_result_before, is_final):
    """Map an assistant text block to a stage of the agentic loop."""
    if is_final:
        return "Done"
    if turn == 1 and not had_tool_result_before:
        return "Plan"
    return "Adjust"


def capture_agent_loop(client):
    task = PROMPTS["specific"]
    messages = [{"role": "user", "content": task}]
    steps, totals = [], {"input": 0, "output": 0}
    seen_tool_result = False

    for turn in range(1, MAX_TURNS + 1):
        print(f"  - turn {turn}...")
        resp = client.messages.create(
            model=MODEL,
            max_tokens=1500,
            system=AGENT_SYSTEM,
            tools=TOOLS,
            messages=messages,
        )
        totals["input"] += resp.usage.input_tokens
        totals["output"] += resp.usage.output_tokens
        is_final = resp.stop_reason != "tool_use"
        messages.append({"role": "assistant", "content": resp.content})

        tool_results = []
        for block in resp.content:
            if block.type == "text" and block.text.strip():
                steps.append({
                    "turn": turn,
                    "stage": classify_text(turn, seen_tool_result, is_final),
                    "kind": "text",
                    "text": block.text.strip(),
                })
            elif block.type == "tool_use":
                steps.append({
                    "turn": turn,
                    "stage": "Ask" if block.name == "ask_user" else "Act",
                    "kind": "tool_call",
                    "tool": block.name,
                    "input": block.input,
                    "raw": {"type": "tool_use", "id": block.id, "name": block.name, "input": block.input},
                })
                output = run_tool(block.name, block.input)
                steps.append({
                    "turn": turn,
                    "stage": "Check",
                    "kind": "tool_result",
                    "tool": block.name,
                    "output": output,
                    "from_user": block.name == "ask_user",
                })
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": output})
                seen_tool_result = True

        if is_final:
            break
        messages.append({"role": "user", "content": tool_results})
    else:
        steps.append({"turn": MAX_TURNS, "stage": "Done", "kind": "text",
                      "text": f"(Stopped: reached the {MAX_TURNS}-turn limit.)"})

    return {"task": task, "steps": steps, "turns": turn, "usage": totals}


def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("Set ANTHROPIC_API_KEY first (see the top of this file).")
    if not TEMPLATE.exists():
        sys.exit(f"Can't find {TEMPLATE.name} next to this script.")

    client = anthropic.Anthropic()
    print(f"Model: {MODEL}")
    print("Part 1: comparing a vague and a specific request")
    comparison = capture_prompt_comparison(client)
    print("Part 2: running the agent loop")
    loop = capture_agent_loop(client)

    data = {
        "isSample": False,
        "model": MODEL,
        "capturedAt": datetime.date.today().isoformat(),
        "files": FEEDBACK_FILES,
        "comparison": comparison,
        "loop": loop,
    }
    OUT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")

    html = TEMPLATE.read_text(encoding="utf-8")
    if PLACEHOLDER not in html:
        sys.exit("Template placeholder not found - was lab_template.html edited?")
    # Escape "</" so captured text can never close the <script> tag early.
    payload = json.dumps(data).replace("</", "<\\/")
    OUT_HTML.write_text(html.replace(PLACEHOLDER, payload), encoding="utf-8")

    tool_calls = sum(1 for s in loop["steps"] if s["kind"] == "tool_call")
    print(f"\nDone. {loop['turns']} turns, {tool_calls} tool calls, "
          f"{loop['usage']['input'] + loop['usage']['output']:,} tokens.")
    print(f"Wrote {OUT_HTML.name} (upload this to the Rise Code Block) and {OUT_JSON.name}.")


if __name__ == "__main__":
    main()
