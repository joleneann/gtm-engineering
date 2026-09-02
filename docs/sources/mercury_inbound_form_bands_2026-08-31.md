# Mercury inbound form: expected balance size bands

**Captured** 2026-08-31.
**Provenance:** screenshot supplied by the user from Mercury's own inbound form. **Not** a fetched
page, so there is no `curl` command to reproduce it and no HTML to diff. This file records what was
seen, by whom, and what is not known.

---

## Verbatim

The form field, transcribed exactly as it appears:

```
Expected balance size*

  ( ) $0-$100k
  ( ) $100k-$1m
  ( ) $1m-$10m
  ( ) $10m-$50m
  ( ) $50m+
```

Single-select radio group. The asterisk marks it **required**.

---

## What this is evidence of

1. **Mercury segments prospects by expected balance**, and asks for it at the point of first contact.
   Balance size is not an inference the seller leaves to the buyer; it is a required field.

2. **The segmentation is logarithmic.** $100k, $1m and $10m are exact decades. The scoring model's
   log compression of the raise amount was, until this capture, my own choice with no evidence from
   the seller behind it. It now has some.

3. **The seller's ceiling is $50m.** Above that, Mercury stops distinguishing: everything collapses
   into one bucket. The scoring model's amount ceiling was $1B, chosen from AI funding headlines
   rather than from Mercury, and it was twenty times too high.

4. **The seller's floor is $0.** There is a band for companies expecting to hold under $100k, so
   Mercury explicitly serves them. The amount floor in the model is a **scoring** floor, never a
   gate, and this capture confirms that reading: the smallest band is a band, not an exclusion.

---

## What this is NOT evidence of

- **Expected balance is not amount raised.** Mercury asks what a company expects to *hold*. Form D
  reports what it *sold*. The two are close at the moment the money lands and diverge as the company
  burns. Tagging a filing with one of these bands would be an **assumption**, not a measurement, and
  it cannot be checked without Mercury's own account data. **Withdrawn 2026-08-31:** a `balance_band`
  column did exactly that, justified by the claim that it made inbound and outbound rankable on one
  scale. Inbound arrives with intent and is never cold-emailed, so the two lanes are not one scale
  and the column is deleted.
- Nothing here says how Mercury weights the bands, what it does with the answer, or which band
  converts best.
- Nothing here concerns Treasury. The $250K Treasury minimum sits *inside* band 2 (`$100k-$1m`),
  which means band 2 is ambiguous on Treasury eligibility while bands 3, 4 and 5 clear it outright.

---

## Gaps in this capture, to be filled if it becomes more load-bearing

| Unknown | Why it matters |
|---|---|
| **The URL** | Not recorded. Without it the capture cannot be refreshed or diffed |
| **Which flow it belongs to** | Contact-sales, Treasury enquiry and general sign-up may ask different questions |
| **Whether the bands vary** | If the band set differs per flow, "Mercury's segmentation" is really "this form's segmentation" |
| **Field name in their system** | Would confirm whether this is a CRM property or a form-only field |

The scoring model uses only points 2, 3 and 4 above, all of which are visible in the transcript and
none of which depend on the unknowns. Point 5, the cross-lane vocabulary claim, was withdrawn on
2026-08-31 and is recorded in the section above.

---

## Where this is used

- `docs/loom_script.md` section 6: the amount curve's two boundaries. **That is the only use.**
- The scoring config: `AMOUNT_FLOOR = 100_000`, `AMOUNT_CEIL = 50_000_000`.
