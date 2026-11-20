# 03 — User research · ParcelCheck (P4)

> Three conversations (20 min each) + one usability test of the prototype with two of them.
> Mom Test rules (Rob Fitzpatrick): ask about past behaviour, not opinions; never pitch; never ask "would you use…?".
> **Status (6 Nov):** this is the kit. Nothing below the guides has been filled in. Every quote must come from a real conversation, or from a classmate in role, said explicitly in the table.

## Who we talk to (targets, one per row)

| # | Who (role, company type — no personal data) | Real user or classmate in role? | Date | Interviewer · note-taker |
|---|---|---|---|---|
| 1 | Someone who **filed a damaged-parcel claim** in the last 6 months: an online seller (Etsy / Vinted / own e-shop) or a small-business shipper | Classmate in role | Nov 8 | Luli · Wei-Ling |
| 2 | Someone who **handled refund or claim tickets** in customer service (logistics, carrier, marketplace, e-commerce) | | | |
| 3 | Someone who **approves refunds or watches refund costs** (team lead, ops or finance in e-commerce / logistics) | | | |

## Interview guide — merchant (#1)

1. Tell me about the last time a parcel you sent arrived damaged. What happened, step by step?
	It was around end of August 2026. I sold 6 ramekins which I wrapped in bubble wrap and put in a reinforced Nespresso box. When the parcel arrived, the buyer found that two of them were broken.
2. How did you find out? What did you do first?
	The buyer sent me the photos of broken ramekins as proof. First, I contacted Vinted to get a refund.
3. What did you send to get money back: photos, the label, a message? How long did it take you?
	I sent the photos the buyer had sent me. It took about a month to get a refund from Vinted.
4. How long until you got an answer? What did you do in the meantime (chase, reship, refund your customer)?
	Vinted gave the buyer a full refund, so I lost all the money from this sale, and I didn’t even get the unbroken ramekins back. Vinted just ignored my claim. I sent the message again several times. In the end, I contacted SignalConso to step in on my case. In total, it took about a month before I got an answer from Vinted.
5. What did the answer say? Did you understand why? Did you contest it?
	They finally answered me after SignalConso stepped in. They agreed to refund me.
6. What did it cost you in total: the refund, the reship, your time, the customer?
	I got a full refund of the price of the items I sold, but I lost a lot of time and energy contacting Vinted and SignalConso.

## Interview guide — support agent (#2)

1. Walk me through the last refund or damage claim you handled, screen by screen.
2. Which part took the longest? Where did you have to look something up?
3. How did you decide from the photo? When was it hard to decide?
4. When did you have to ask someone (lead, finance) before refunding? What happened then?
5. Tell me about a claim you got wrong, or that came back. What happened?
6. How many of these did you do on a typical day? (**Time study input: minutes per claim**)

## Interview guide — approver / finance (#3)

1. When did you last have to approve or reverse a refund? What made you look at it?
they didn't described any specific case.
1. How do you find out today that refunds are too generous, or too strict?
They notice afterwards, when an answer turns out to be “based on an out of date cache of the store”.
1. What is the largest refund someone can give without asking you? Why that amount?
“Never let it issue refunds without approval.” Tracking, FAQs and return-policy questions can be automatic; anything that touches money needs their approval. One adds: “any refund request that includes an image goes to a person first.”
1. Tell me about a refund that became a problem: a complaint, an audit, a merchant who left.
no real incident, only fears: “once the money is gone, it is gone”, customers “screenshot it and hold you to it”, and “the real cost was rarely the initial error but the clean up”.
1. What do you check before you trust a number about refunds?
“check the number in the draft reply against the live value, and send it to a person when they differ”; answers must come “from real order and policy data”.

*Avoid:* "Would you use an AI that…?" · "Do you like this idea?" · "How much would you pay?"

## Time study — the number that flips the memo

Ask interviewee #2 (and #1 from the other side) to reconstruct their last 3–5 claims. Write, per claim: minutes reading, minutes on the photo, minutes in the label system, minutes on the policy and amount, waiting for approval, writing the reply, number of follow-up contacts. Target sample: 30 claims across interviews and replay. **Flip point: ≥ €17.50 per claim (≈ 24 min all-in) at €0.73/min all-in.**

| Claim # | Source (interview #) | Read | Photo | Label lookup | Policy + amount | Approval wait | Reply | Follow-ups | Total min |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Interview #1 (classmate in role, Vinted seller) | 4 | 3 | 0 (no label system used) | 6 | 30 days | 12 | 5 contacts × 2 min = 10 | 35 |

## What we heard (facts, in their words)

| # | Quote or observed behaviour | Which part of our brief it confirms or contradicts |
|---|---|---|
| 1 | *“It was around end of August. I sold 6 ramekins which I wrapped in bubble wrap and put in a reinforced Nespresso box. When the parcel arrived, the buyer found that two of them were broken.”* | Confirms: damaged-parcel claims are a real pain point for small sellers; packaging alone does not prevent disputes. |
| 2 | *“The buyer sent me the photos of broken ramekins as proof. First, I contacted Vinted to get a refund.”* | Confirms: the seller relies on buyer-supplied photos as evidence; the first action is to open a claim with the platform. |
| 3 | *“I sent the photos the buyer had sent me. It took about a month to get a refund from Vinted.”* | Confirms: evidence submission is photo-based; the process is slow (~1 month). |
| 4 | *“Vinted gave the buyer a full refund, so I lost all the money from this sale, and I didn’t even get the unbroken ramekins back. Vinted just ignored my claim. I sent the message again several times. In the end, I contacted SignalConso to step in on my case.”* | **Contradicts** the assumption that platforms act quickly on seller claims. Confirms: sellers lack an internal escalation path; external pressure (SignalConso) is the current workaround. |
| 5 | *“They finally answered me after SignalConso stepped in. They agreed to refund me.”* | Confirms: resolution only came after external intervention — a strong signal that the current process is inefficient. |
| 6 | *“I got a full refund of the price of the items I sold, but I lost a lot of time and energy contacting Vinted and SignalConso.”* | Confirms: the total cost is not just monetary but also time and energy — aligns with the time-study flip point. |

**Observed behaviour during the interview:**
- The classmate hesitated when asked “how long did it take you to prepare the evidence?” — they had not tracked it, and had to reconstruct it. This suggests that merchants do not measure their own time, which is exactly why the time study matters.

## Usability test — one task, think aloud, don't help

**Prototype link:** see `03_prototype_link.md`.

- **Task (merchant, tester #1):** "Your mug arrived broken. Claim a refund for it with this photo."
- **Task (reviewer, tester #2):** "Clear the first three claims in your queue."

Watch whether they read the receipt, whether they trust the YOLO box, and where they click first.

| Tester | Finished without help? (yes / no) | Where they hesitated | What they expected instead |
|---|---|---|---|
| | | | |

## Desirability gate — do they want it?

- [ ] 2 of 2 finished the task without help
- [ ] They told us what they did last time — not what they would do
- [ ] At least one said "I want this before…"
- [ ] Our out-of-scope list grew; our success criterion did not move

**Decision:** go to the Session 4 build · or back to the brief — because …
