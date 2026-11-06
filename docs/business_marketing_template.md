# Business and marketing worksheet

**Template only.** Fill after the assigned challenge. Bracketed entries are unresolved placeholders, not facts, research results or validated forecasts. Requirements trace to guide pp.3-4,7-8. Keep underlying calculations and direct sources accessible to judges.

## Problem and customer

- Assigned challenge: [announced wording and constraints]
- One-sentence problem: [specific user] struggles to [task] because [cause], causing [evidenced pain].
- Buyer vs user: [who pays] / [who uses]. Initial segment/geography: [precise definition].
- Evidence of scale: [figure or other evidence], [date], [population], [direct source].
- Why RAG: [need for reliable document-grounded answers and citations]. Alternatives: [standalone LLM, keyword search, current workflow].
- Local fit: [Arabic/dialect], [privacy], [internet], [cost], [accessibility].

## Source and assumption ledger

| Claim/input | Value and unit | Fact or assumption | Direct source/title/date/access date | Geography/population | Calculation/limitation |
|---|---|---|---|---|---|
| [input] | [unfilled] | [fact/assumption] | [unfilled] | [unfilled] | [unfilled] |

Facts require supporting sources. An estimate remains an assumption even if plausible. Do not manufacture citations, customers, interviews, conversion rates, statistics or partnerships.

## TAM / SAM / SOM

Use consistent units, geography and period. Distinguish annual revenue opportunity from number of users.

- TAM = [all eligible buyers] x [declared annual revenue per buyer], or explain a justified alternative.
- SAM = [buyers serviceable with actual language/geography/product constraints] x [same compatible revenue unit].
- SOM = [realistically reachable paying buyers over specified horizon] x [annual revenue per buyer]. Explain sales/channel capacity; do not select an arbitrary market percentage without rationale.
- Source customer counts; label price/penetration/uptake estimates. Check SOM <= SAM <= TAM when units and periods match.
- Missing evidence: [what is unknown and how it will be researched].

## Pricing and unit economics

| Input | Value | Evidence or assumption | Sensitivity |
|---|---|---|---|
| Buyer, billing period and reason to pay | [unfilled] | [unfilled] | [unfilled] |
| Price and included usage | [unfilled] | [unfilled] | [unfilled] |
| Variable cost per customer/period | [unfilled] | [unfilled] | [unfilled] |
| Sales/marketing acquisition spend | [unfilled] | [unfilled] | [unfilled] |
| New paying customers attributable to spend | [unfilled] | [unfilled] | [unfilled] |
| Retention/churn or estimated lifetime | [unfilled] | [unfilled] | [unfilled] |

Formulas (declare model applicability and matching time units):

- Gross profit/customer/period = revenue/customer/period - variable cost/customer/period.
- Gross margin = gross profit / revenue; undefined when revenue is zero.
- CAC = acquisition spend / new paying customers; undefined if none acquired. A prelaunch CAC is an assumption, not measured acquisition performance.
- LTV can be modeled as periodic revenue x gross margin x expected paid lifetime; disclose retention/lifetime assumptions and limitations. Do not infer validated LTV from a short demo.
- API cost/answer = input tokens x input rate + output tokens x output rate, adjusted for provider billing units and any separately charged usage. Include embeddings/rerank if hosted and billed.
- Monthly query volume at 10,000 users = 10,000 x [active share] x [queries/active user/month]. This is a forecast, not observed load.

## Costs, 12-36 month forecast and break-even

Separate one-time build/setup from ongoing API, hosting/storage, staff, support, acquisition and other justified costs. Local prototype hardware is not proof production hosting is free. Save date/model/currency/unit for pricing sources.

| Month (expand through chosen 12-36-month horizon) | Opening paid customers | New | Lost | Closing | Revenue | Variable cost | Fixed cost | Acquisition spend | Net cash/result |
|---|---|---|---|---|---|---|---|---|---|
| [month] | [unfilled] | [unfilled] | [unfilled] | [unfilled] | [unfilled] | [unfilled] | [unfilled] | [unfilled] | [unfilled] |

Define whether revenue uses opening, average or closing customers; keep it consistent. Break-even customers = fixed recurring costs / positive contribution per customer, if the simplified model applies. If contribution is nonpositive or cumulative cash never crosses zero, state that honestly. Distinguish monthly operating break-even from cumulative payback. Show a conservative/base/optimistic sensitivity using explicitly declared assumptions, especially the weakest one.

## Marketing and first 90 days

- Persona: [role], [organization], [trigger], [workflow], [constraints], [buyer authority].
- Positioning: For [segment], [product] helps [outcome] using [demonstrable difference].
- Alternatives/competitors: [current options], [sourced capabilities/prices], [actual measured difference], [our limitations].
- Initial channels: [audience-specific channels], [why realistic], [owner], [estimated spend].
- Potential partners: [hypotheses and benefit]; distinguish a possible partner from an agreed partnership.
- First three prospective customers: [real suitable organizations/roles after assignment], [why], [draft message]. No outreach is authorized by this worksheet.

| Period | Action | Owner | Estimated budget | Numeric target (not actual) | How measured |
|---|---|---|---|---|---|
| Days 1-30 | [discovery/pilot scope] | [unfilled] | [unfilled] | [unfilled] | [unfilled] |
| Days 31-60 | [launch/channel experiment] | [unfilled] | [unfilled] | [unfilled] | [unfilled] |
| Days 61-90 | [retention/expansion decision] | [unfilled] | [unfilled] | [unfilled] | [unfilled] |

Define activated users, conversion numerator/denominator, retention cohort/window and paid customer consistently. Label targets separately from actual measurements. End with the concrete ask: [pilot access, introductions or next-step resource justified by plan].
