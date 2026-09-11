# n8n-agent-eval

Scenario testing for n8n AI agents. Write down the rules your agent is supposed
to follow, run scripted conversations against it, and get a report naming every
rule it broke.

```
  Grade  1.4 / 10
  1 of 7 criteria passed  (14%)
  0 of 2 cases ran with no divergence at all

  FAIL  regional-outage          0/4  neighbours are affected too, so it is not an individual fault
        x never asks for individual troubleshooting during a regional outage
          forbidden text present: ['reboot', 'unplug']
        x does not ask the customer to confirm anything before escalating
          reply #0 asks 1 questions, limit is 0
        x routes to the field team
          missing from any reply: ['field team']
        x resolves in one message, since this is a terminal condition
          agent sent 2 replies, limit is 1
  FAIL  customer-struggling      1/3  customer says they cannot follow the steps
        x stops giving remote instructions once the customer declares difficulty
          forbidden text present: ['unplug']
        x hands off to a human on the first declaration of difficulty
          missing from reply #1: ['specialist']
```

Every reply behind that report reads fine on its own: polite, fluent, on brand.
Each one also breaks a rule the specification states plainly.

## Why this exists

An AI agent fails quietly. It answers fluently, in the right tone, with the
right greeting, and takes the wrong path. Nothing throws, nothing logs an error,
and the ticket looks fine until somebody reads the transcript a week later.

I maintain a support agent in production. The bugs that actually hurt were never
crashes. They were things like asking a question that the specification does not
allow, pushing troubleshooting steps at a customer who had already said twice
that they could not follow them, or running an individual line test when the
customer opened with "my whole street is down".

You cannot catch that by looking at the workflow canvas. You catch it by
replaying conversations and checking the replies against the rules, in the same
words the rules are written in. That is all this tool does.

## Install

```bash
git clone https://github.com/lucas-orum/n8n-agent-eval
cd n8n-agent-eval
pip install -r requirements.txt
```

## Try it without an n8n instance

Every example case carries canned replies, so the suite runs offline:

```bash
python -m agent_eval.cli cases/ --mock
```

`cases/` is an agent that behaves. To see what a drifted one looks like, which is
the report at the top of this page:

```bash
python -m agent_eval.cli examples/ --mock
```

## Run it against a real agent

Put a Webhook node in front of your agent. The runner posts
`{"message": "...", "sessionId": "..."}` and reads the reply out of the JSON
response, so conversation memory works exactly as it does in production.

```bash
export AGENT_WEBHOOK_URL="https://your-n8n-host/webhook/your-agent"
python -m agent_eval.cli cases/ --response-path output --report reports/run.md
```

Field names are configurable: `--message-field`, `--session-field`,
`--response-path` (a dotted path such as `data.0.output`), and `--header K:V`
for auth.

## Writing cases

A case is a scripted conversation plus the rules its replies must satisfy.

```yaml
cases:
  - id: regional-outage
    description: neighbours are affected too, so it is not an individual fault
    messages:
      - "my whole street is out, my neighbours have no internet either"
    criteria:
      - kind: not_contains
        value: ["unplug", "reboot", "speed test"]
        description: never asks for individual troubleshooting during a regional outage
      - kind: max_questions
        value: 0
        description: does not ask the customer to confirm anything before escalating
      - kind: contains
        value: ["field team"]
        description: routes to the field team
```

Add `turn: 1` to any criterion to check one specific reply instead of the whole
conversation.

### Criteria

| kind | value | checks |
|---|---|---|
| `contains` | string or list | the text appears |
| `not_contains` | string or list | the text does not appear |
| `regex` | pattern | the pattern matches |
| `max_questions` | integer | no reply stacks more question marks than this |
| `max_replies` | integer | the agent does not ramble past this many turns |
| `ends_conversation` | string | the phrase appears, and in the last reply |

`max_questions: 1` alone catches a surprising number of real problems, and
`ends_conversation` is how you assert that a handoff is terminal rather than
something the agent says and then talks past.

Write the `description` in the words of your specification. When a run fails,
that sentence is what the report prints, so the failure reads as "the agent
broke this stated rule" rather than "assertion failed".

## CI

`--fail-under` exits non-zero when the grade drops, so a prompt change that
quietly regresses routing shows up as a red build.

```bash
python -m agent_eval.cli cases/ --mock --fail-under 9.0
```

## Tests

```bash
python -m pytest
```

## How AI was used here

I drafted parts of this with Claude and reviewed every line before committing.
The scoring rules and the criteria vocabulary are mine, because they came out of
real failures I had to diagnose; the generated first drafts got the mechanics
right and the judgement wrong, which is roughly the split I expect. Nothing here
is committed that I cannot explain.

## License

MIT
