# ICOM — Laputka Law Office

This is Laputka Law Office's working copy of ICOM (Inter-agent Comms), a one-line format for assistant-to-assistant messages. The standard was written by Robert Stanley / Iron Noodle Technologies. Upstream: [rstan251/icom-standard](https://github.com/rstan251/icom-standard). This fork is the firm's book. It is public, so it holds codes and rules, not client names, matter names, company names, phone numbers, account numbers, or secrets.

Firm book: **codebook 2.0.0**, adopted 2026-10-22.

## Message format
```
@FROM>ICOM>TO P0-3 LANE #ticket VERB topic key=val
```
A line ICOM itself sends does not add a second hop: `@ICOM>TO P0-3 LANE #ticket VERB topic key=val`.
- `FROM` / `TO`: assistant codes in `codebook.yaml`. More than one recipient is `>TO1,TO2`.
- `P0-3`: priority. P0 now, P1 today, P2 this week, P3 whenever.
- `LANE`: `INT0` for internal work. This book has no client list.
- `#ticket`: an Iron Docket id, for example `#T-1001`. Required. Iron Docket is not installed yet; the id is still required. No ticket is NAK.
- `VERB`: GO HOLD DONE BLOCKED REC FYI ASK ACK NAK.
- `topic`: an [ICX](https://github.com/attorneylaputka/icx) code, coarse to fine, for example `pr.appt.book`. Then `key=val` tokens.

```
@JEN>ICOM>MARIAG P2 INT0 #T-1001 DONE pr.appt.book n=1 f=~/work/logs/appt-book.log nx=GAUNT:review
```

A message with no ticket, an unknown code, or prose is NAK. ICOM does not relay it.

## Who is who
MARIAG (Maria G, chief of staff) is the only assistant who speaks to Charles, and she approves new codes. ICOM is the router and the only editor of the codebook. Proposals go to MARIAG once a week.

| Code | Who | Reports to |
|---|---|---|
| MARIAG | Maria G, chief of staff; codebook approver; only assistant who speaks to Charles | Charles (plain English) |
| JEN | calendar and email | MARIAG |
| GAUNT | Gauntlet, independent reviewer | MARIAG |
| POLL | Inbox Puller | MARIAG |
| ICOM | router; codebook editor | MARIAG |
| CTO | technology | MARIAG |
| TEAMS | Teams Bot | MARIAG |
| CFO | finance lead | MARIAG |
| CLAP, CILL, CCLR, CWAT, CMON, CPRE, CBIG, CFUN, CWES | comptrollers, one code each; the company name stays out of the book | CFO only |
| TRAV | Travel Agent | MARIAG |
| FLT, HTL, CAR, REST, TRV | flight, hotel, rental car, restaurant, travel review | TRAV |

The only lane is INT0.

## Topics
ICOM says how a message is built. [ICX](https://github.com/attorneylaputka/icx) says what it is about. Use the firm's book, `examples/codebook.yaml` and `examples/index.yaml` in that repo. The same codes are copied into `objects` in this repo's `codebook.yaml` so a line can be checked offline. A topic with no code yet is sent as `x.<word>`. ICOM files it on the weekly proposal. MARIAG approves before it is added.

## Plain English, secrets, and money
English is for Charles, for clients, and for anyone outside the firm. MARIAG is the only assistant who speaks to Charles. ICOM never appears in a client email, letter, or filing.

No secrets in a message. Name the place a record or secret is kept (`f=` or `ref=`). Never write the value.

No money moves without Charles's explicit approval, routed through MARIAG (`org.rule.apprv`, `fin.paybl.apprv`). Payroll codes are reminders only.

## Pilot
Start with three assistants plus the router: MARIAG, JEN, and GAUNT. ICOM routes their lines and audits them for one week. MARIAG then sends `GO org.agent` to ICOM, and the rest of the roster comes on. Until that GO, ICOM NAKs any other sender with `why=pilot`.

## What to paste
- Every assistant except ICOM: paste `adopt/HDR.txt` at the top of that assistant's instructions.
- ICOM: paste `AGENT-INSTRUCTIONS.md` as its instructions. Do not also paste the header.

## Checking
```
python3 tools/icom_validate.py
python3 tools/icom_validate.py --icx /path/to/icx/examples/codebook.yaml
```
The second command checks this book's topics against the firm's ICX codebook. It needs PyYAML.

## Files
- `PROTOCOL-v1.md` — the spec, with this firm's names and topics
- `codebook.yaml` — assistants, the INT0 lane, verbs, topics, fields
- `examples.txt` — one internal handoff in English, house style, ICOM, and a few other formats
- `AGENT-INSTRUCTIONS.md` — the ICOM assistant's instructions
- `adopt/HDR.txt` — the block pasted at the top of every other assistant's instructions
- `tools/icom_validate.py` — checks the book and the sample lines
- `CONTRIBUTING.md`, `LICENSE` (MIT, upstream)
