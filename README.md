# Agentic Loop Lab: setup

A hands-on lab for the "Agentic Process in Claude" microlearning. It shows real Claude API responses inside a Rise 360 Code Block. The course itself never calls the API.

## Files

| File | What it is |
|---|---|
| `capture_lab_data.py` | Python script. Calls the Claude API, runs a real tool-use agent loop, and builds `index.html`. |
| `lab_template.html` | The lab page with no data in it. The script fills it in. Don't rename it. |
| `index.html` | The finished lab. The version you have now shows **hand-written preview data** with a warning banner, so you can see the layout. Running the script replaces it with real responses. |

## 1. Capture real responses (about 5 minutes)

1. Get an API key at console.anthropic.com. Calls cost money, but one run of this script is a few cents.
2. Put all three files in one folder, open a terminal there, and run:

   ```
   pip install anthropic
   export ANTHROPIC_API_KEY="sk-ant-..."      # Windows: set ANTHROPIC_API_KEY=sk-ant-...
   python capture_lab_data.py
   ```

3. Open the new `index.html` in your browser. The orange "Preview data" banner should be gone, and the subtitle should show the model and the date.

Don't like the run? Run the script again; every run is a little different. To use a cheaper model, set `CLAUDE_MODEL=claude-haiku-5-5` first.

## 2. Add it to Rise 360

1. In your Rise lesson, insert a **Code** block.
2. Choose **Add code** and paste in the full contents of `index.html`, or choose **Upload project** and upload a ZIP with `index.html` at the root (not inside a folder).
3. Turn on **Set completion requirements**. The lab already sends Rise's completion signal once the learner answers both questions and reaches the last step of the loop.
4. Add a **Continue** block after it, set to require completion of the block above.
5. Preview it in Review 360. Rise notes that LMS and web exports can't preview code blocks locally.

## Change the scenario

All the content lives at the top of `capture_lab_data.py`:

- `FEEDBACK_FILES`: the fake data the agent reads. The September file has no comments on purpose, so the agent has to catch the problem.
- `CANNED_USER_ANSWER`: the "learner's" reply when Claude stops to ask a question.
- `PROMPTS`: the vague and specific requests.
- `AGENT_SYSTEM`: the instructions Claude follows during the loop.

Each step is labeled Plan, Act, Check, Adjust, Ask or Done by the script, based on what happened. To change a label, edit it in `lab_data.json` and paste the updated data back into `index.html`, or ask Claude to help.

## Note

Claude decides its own path, so a real run may not ask about September. It might skip the file and explain why instead. Either way, the Check → Adjust part is still visible. If you want the "Ask you" checkpoint to appear every time, run the script again until it does.
