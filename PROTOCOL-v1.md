# ICOM Compact Handoff Protocol — v1 ("CHP/1")

Status: adopted for Laputka Law Office, 2026-10-22. The grammar is CHP/1. The names, the lane, and the topics are the firm's. Topics are ICX codes from https://github.com/attorneylaputka/icx . The generic sample registry this text used to show was not a live firm book and is not kept. Where an older sentence and `codebook.yaml` disagree, `codebook.yaml` wins.

This firm enforces rule 12 strict: one header line, no prose body. A house `D/R/F/O/Q/A` line, a second line, or a quoted sentence is NAK `why=prose`.

## 1. Hard rules
1. **Client email, letters, filings, and anything a person outside the system reads stay plain English.** ICOM never appears in those documents. Charles gets English from MARIAG only. No other assistant speaks to Charles.
2. One message = one header line. Unknown code: reply `NAK` with the code. Never guess.
3. Reference, don't restate: point to `f=` paths, ticket `#T-1001`, commit ids.
4. Never put secrets, tokens, or keys in a message. Name the place with `f=` or `ref=`. Never write the value.
5. This firm does not use the quoted-value exception. Free text is prose and is NAK'd.

## 2. Grammar
```
msg     = header
header  = routed / direct
routed  = "@" from ">" "ICOM" ">" to [ "," to ]* SP pri SP lane SP ticket SP verb [SP action] SP topic *(SP kv)
direct  = "@" "ICOM" ">" to [ "," to ]* SP pri SP lane SP ticket SP verb [SP action] SP topic *(SP kv)
from    = AGENT-code            ; codebook.agents except ICOM (ICOM uses direct)
to      = AGENT-code            ; codebook.agents
pri     = "P0" / "P1" / "P2" / "P3"
lane    = "INT0"                ; codebook.clients; no client list
ticket  = "#T-" 1*DIGIT         ; required, e.g. #T-1001; missing → NAK why=no-ticket
verb    = GO / HOLD / DONE / BLOCKED / REC / FYI / ASK / ACK / NAK
action  = verb                  ; only after REC (REC HOLD, REC GO)
topic   = ICX code              ; codebook.objects, optional ~facet; unknown concept is x.<word>
kv      = key "=" value         ; value: token, list "a,b", or alternatives "a|b"
```
The only line that may omit `ticket` is ICOM's own NAK `why=no-ticket`. That line is not relayed and is not logged as a ticket comment.

Example: `@JEN>ICOM>GAUNT P2 INT0 #T-1001 BLOCKED pr.appt.book why=conflict ask=rebook|cancel f=~/work/cal/appt-1001.md cc=MARIAG`

Mapping to the old house style, kept so older notes are readable: DONE≈D, REC≈R, f=≈F, #ticket/own=≈O, ASK/ask=≈Q, nx=/ret=≈A. This firm does not send house lines.

## 3. Codebook (see codebook.yaml)
YAML with sections `verbs, priority, agents, reports, clients, objects, facets, fields, paths`. Rules: codes are 6 characters or fewer; assistants and lanes are UPPER; topics are lower.dot; after version 2.0.0 the book is append-only; a retired code is tombstoned and never reused. ICOM is the sole editor and proposes additions weekly (a free-text topic seen 5 or more times). MARIAG approves. ICOM applies a code only after that GO.

Registries: `codebook.yaml`. Lane: INT0 only. Verbs: the nine above. Topics: the firm's ICX book, copied into `objects`.

Check: `python3 tools/icom_validate.py`.

## 4. Replies
Threads keep the ticket.
`@MARIAG>ICOM>JEN P2 INT0 #T-1001 ACK pr.appt.book`
`@MARIAG>ICOM>JEN P2 INT0 #T-1001 GO pr.appt.rebook`
`@ICOM>JEN P2 INT0 #T-1001 NAK pr.appt.book why=unk`

## 5. Measurements
These token counts are the upstream measurement of CHP/1 on the generic sample (tiktoken, 5 handoffs, 2026-10-18). They are not firm traffic, and they were not re-measured for this adoption.

| format | cl100k tokens | saved vs English | o200k tokens | saved vs English | vs house (o200k) |
|---|---|---|---|---|---|
| English prose | 429 | — | 424 | — | −40% |
| House TL;DR+codes | 305 | 28.9% | 303 | 28.5% | — |
| **CHP v1** | **248** | **42.2%** | **250** | **41.0%** | **+17.5% saved** |
| JSON compact | 369 | 14.0% | 377 | 11.1% | −24% (worse) |
| TOON | 376 | 12.4% | 377 | 11.1% | −24% (worse) |
| JSON pretty | 558 | −30.1% | 559 | −31.8% | −85% |
| base64 of v1 | 641 | −49.4% | 604 | −42.5% | −99% |

Notes from that measurement: full paths were about 25–35% of a v1 message; a short path alias (for example `%w=~/work`) saved a few more tokens. One sample was 3 tokens longer than house style. Measured with tiktoken encodings cl100k_base and o200k_base.

## 6. Optional cost guidance
1. One model turn per handoff where possible.
2. No ack-only messages unless the sender asked for ACK.
3. Hand back a file path, not a summary chain.
4. Run long analysis, drafting, log review, and audits on the cheapest capable model or worker. Keep the router thin.
5. Cap the number of concurrent helper assistants.
6. Shared memory is files: standing rules in the codebook, tasks on a ticket. Read the ticket before acting. Write the result back.
7. Every active task needs a ticket before work starts. A GO, a decision, a result, and a file path are logged on that ticket. No ticket, no work.

## Rule 11 — ICOM routing
All assistant-to-assistant messages route through ICOM, MARIAG included. No direct assistant-to-assistant sends.
Format: `@FROM>ICOM>TO[,TO] P0-3 INT0 #ticket VERB [ACTION] topic key=val`
- Address sends to ICOM only. `>TO` after ICOM names the final recipient.
- ICOM relays the line unchanged to TO and logs it.
- Replies come back the same way: `@TO>ICOM>FROM ...` with real codes.
- ICOM keeps the sender's priority.
- Example: `@JEN>ICOM>MARIAG P2 INT0 #T-1001 DONE pr.appt.book f=~/work/logs/appt-book.log nx=GAUNT:review`

### Enforcement
The rule-11 header is required. ICOM sends MARIAG a daily digest of untagged or direct messages, flagging senders by count. Hard enforcement can use per-assistant inboxes that only ICOM may write.

### Ticket logging
- Every message cites an Iron Docket ticket (`#T-1001`). Iron Docket is not installed yet. The id is still required.
- Until Iron Docket is installed, ICOM appends each relay to `~/work/icom/relay/YYYY-MM-DD.log`.
- When Iron Docket is installed, each relay is also a comment on that ticket:
  `ICOM: <exact line>` / `Plain English: <one sentence, no codes>`
- No ticket cited: ICOM NAKs the sender and does not relay. Shape: `@ICOM>JEN P2 INT0 NAK org.proto why=no-ticket`
- Comments never include a secret, a card number, or a full account id. Name the place only.
- P0 and P1 are logged immediately. FYI and P2–P3 items are batched into one comment per ticket per hour.

### ICOM stall fallback
If ICOM has not relayed a message within 1 hour, the sender may send it direct with the full rule-11 header and cc MARIAG. ICOM backfills the log afterward. The daily digest does not flag these sends as bypasses.
Stall-fallback direct messages are internal only. Client email, letters, and filings wait for MARIAG. ICOM does not send them, and the name ICOM never appears in them.

## Rule 12: shorthand only
- Assistant chat and handoffs are CHP only. No English prose between assistants.
- MARIAG alone speaks English to Charles.
- Client email, letters, and filings stay plain English. ICOM never appears in them.
- The future Iron Docket comment keeps the `Plain English:` line.
- ICOM NAKs prose: `@ICOM>JEN P2 INT0 #T-1001 NAK org.proto why=prose ask=resend`

## Rule 12 strict
- Header plus `key=val` tokens only. One line.
- Banned: a "TL;DR:" sentence, prose, a numbered explanation, a quote. Point at `f=` instead.
- ICOM NAKs a non-compliant message and does not relay it. The daily audit includes the fail count.

## Rule 12a scope
- English only for Charles, for clients, and for people outside the firm.
- ICOM format for everything else, including each assistant's own chat display, status, and summaries.
- English otherwise only when Charles explicitly asks MARIAG for it.
- An assistant's own chat display stays ICOM even if Charles reads it. English to Charles goes through MARIAG only. Another assistant does not answer him in prose.

## Rule 14: ICX topic codes
- The header topic is an ICX code: class.division.section, coarse to fine, for example `lg.court.efil~err`.
- Every registered prefix is a valid code. The lane stays in the lane slot, never inside the topic.
- Exact values (ids, amounts, dates, paths) stay in `key=val`. They are never part of the topic.
- Unknown concept: send `x.<word>`. ICOM puts it on the next weekly proposal. MARIAG approves before it is added. An unregistered code is NAK `why=icx.unk`.
- Firm book, index, and validator: https://github.com/attorneylaputka/icx

## Rule 17: REC-LABEL (2026-10-19)
- Every recommendation surfaced to Charles is prefixed `AGENTCODE: action`. AGENTCODE is the assistant who originated it.
- Examples: `JEN: reschedule the consultation`; `CFO: hold the refund`.
- MARIAG keeps the label unchanged when she speaks to Charles.
- No unlabeled recommendation to Charles.
- ICOM does not deliver the recommendation to Charles. MARIAG does.

### Reporting and money
- Comptrollers (CLAP, CILL, CCLR, CWAT, CMON, CPRE, CBIG, CFUN, CWES) report only to CFO. Their REC goes to CFO.
- FLT, HTL, CAR, REST, and TRV report to TRAV. Their REC goes to TRAV.
- Every other assistant reports to MARIAG.
- No money moves without Charles's explicit approval, routed through MARIAG. The standing topic is `org.rule.apprv`. MARIAG records the approval as `GO fin.paybl.apprv` on that ticket. A GO on `fin.paybl` or `fin.fee.refund` waits for that line and comes from CFO. `fin.payrl` is a reminder only.

## Changelog
- 2026-10-19: rule 17 REC-LABEL added.
- 2026-10-22: Laputka Law Office adoption. Firm assistant codes, lane INT0, topics from the firm ICX book. MARIAG approves codes and is the only assistant who speaks to Charles. Ticket required, form `#T-1001`. Iron Docket not installed yet.
