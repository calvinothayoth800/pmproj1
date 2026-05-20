# Edge Cases & Failure Handling

Reference for implementation and QA. Each case lists **symptom**, **cause**, and **recommended handling**.

---

## 1. Data ingestion & preprocessing

| Edge case | Example | Handling |
|-----------|---------|----------|
| Missing or null `rate` | `NaN`, empty string | Set `rating = None`; exclude from `min_rating` filter or treat as below threshold |
| Non-numeric rating | `"NEW"`, `"-"`, `"4.5/5"` | Parse `X/5` → float; map `NEW`/`-` to `None`; log count of unparsed |
| Rating out of range | `6.0`, negative | Clamp to `[0, 5]` or drop row |
| Missing `approx_cost(for two people)` | null, `""` | `cost_for_two = None`; exclude from strict budget filter or use city median imputation (document choice) |
| Cost as range | `"500-1,000"`, `"1,000 - 2,000"` | Use midpoint or lower bound; document in `DATA_NOTES.md` |
| Cost with symbols | `"₹1,200"`, `"1,200 for two"` | Strip non-digits except hyphen; then parse |
| Invalid cost after parse | `0`, negative | Set `None`; do not assign `budget_tier` |
| Empty `cuisines` | null, `""` | Empty list; row can still match on city/rating only |
| Multi-cuisine string | `"North Indian, Chinese, Mughlai"` | Split on comma; trim; lowercase for matching |
| Typos in cuisine | user `"Chineese"` | Fuzzy match optional (Phase 2+); MVP: exact substring after normalize |
| City name mismatch | user `"Bengaluru"` vs data `"Bangalore"` | Maintain alias map in `canonical_city()` |
| User city not in dataset | `"Goa"` (if absent) | Return empty filter + message: city not available; suggest nearest from `DATA_NOTES.md` |
| Duplicate restaurants | same `name` + similar `address` | Dedupe keeping highest `votes` or first; log duplicate count |
| Huge text columns | `reviews_list`, `menu_item` | Never load into parquet cache; prevents memory blowups |
| HF download failure | network, timeout | Retry 3× with backoff; clear error: check connection |
| Corrupt cache file | truncated parquet | Detect on load; delete cache and rebuild with `--force` |
| Schema change on HF | new columns | Bump `CACHE_VERSION`; invalidate old parquet |

---

## 2. User input & preferences

| Edge case | Example | Handling |
|-----------|---------|----------|
| Empty city | `""` | Pydantic validation error before filter |
| Unknown city spelling | `"delhi"` vs `"New Delhi"` | Case-insensitive match; alias table |
| No cuisines selected | `[]` | Skip cuisine filter (widen results); show UI hint |
| Too many cuisines | 10+ selected | AND vs OR: use **OR** (any match) per spec; cap UI at ~5 to avoid over-filtering |
| `min_rating = 0` | default | No rating floor (still drop `None` ratings if business rule requires) |
| `min_rating = 5` | very strict | Often zero results → `explain_empty()` + suggest lowering |
| Conflicting extras | quick service + fine dining vibe | Apply both filters (may empty); message to relax one |
| Budget vs actual cost missing | medium budget, no cost on row | Exclude from budget filter or include as “unknown” bucket (document) |
| Invalid budget enum | typo in API | Validate `Literal["low","medium","high"]` |
| Free-text “additional preferences” | long paragraph | Phase 3+: pass to LLM only, not hard filter; truncate to token limit |
| SQL/injection in city string | `"; DROP TABLE` | No raw SQL; pandas only; strip dangerous chars if exposing API |

---

## 3. Filtering engine

| Edge case | Symptom | Handling |
|-----------|---------|----------|
| Zero candidates after all filters | empty DataFrame | Return `RecommendationResponse` with `items=[]`, `reasons=[...]` from `explain_empty()` |
| Too many candidates (>500) | slow LLM | Always `head(MAX_CANDIDATES)` after scorer |
| Single candidate | LLM ranks 1 | Still call LLM for explanation or use template fallback |
| Cuisine partial match | `"Cafe"` vs `"Cafe, Italian"` | Substring/token match on normalized list |
| Location vs city | user picks city, restaurant in sub-location | Match `listed_in(city)` first; optional loose `location` contains |
| All rows missing rating but `min_rating > 0` | empty | Explain: “No rated restaurants match”; offer to lower rating |
| Budget tier boundary | cost exactly at percentile | Inclusive boundaries; document quantile logic per city |
| Ties in scorer | same score | Secondary sort: `votes` desc, then `name` asc for stability |
| Case sensitivity | `"italian"` vs `"Italian"` | Lowercase everywhere before compare |

---

## 4. LLM / Groq integration

| Edge case | Symptom | Handling |
|-----------|---------|----------|
| Missing `GROQ_API_KEY` | auth error | Fallback ranker; UI: “Set GROQ_API_KEY in .env” |
| Invalid / revoked key | 401 | User message; no retry; log once |
| Rate limit | 429 | Exponential backoff (2–3 retries); then fallback |
| Model deprecated / wrong name | 404 | Surface model name from config; link to Groq docs |
| Timeout | >30s | Retry once; fallback with template explanations |
| Empty LLM response | `""` | Fallback |
| Malformed JSON | prose + JSON mix | Extract JSON block with regex; if fail → fallback |
| Truncated JSON | mid-array cut | Parser error → fallback; reduce `MAX_CANDIDATES` or shorten prompt |
| Hallucinated restaurant | name not in candidates | `drop_unknown_names()`; if < K left, fill from scorer |
| Wrong rating/cost in LLM output | drift from data | `enrich_from_dataframe()` overwrite from ground truth |
| Duplicate ranks | two `#1` | Renumber by appearance or re-sort by rank field |
| LLM returns fewer than K | 2 items when K=5 | Accept partial; optionally pad from scorer |
| LLM returns more than K | 10 items | Take first K after validation |
| Token limit exceeded | 413 / context error | Reduce candidates; shorten fields sent (drop `dish_liked` from prompt) |
| Content policy refusal | safety block | Fallback + generic message |
| Concurrent Streamlit clicks | double API calls | Disable button while `recommend()` running |

### Groq-specific

| Edge case | Handling |
|-----------|----------|
| `LLM_BASE_URL` must be `https://api.groq.com/openai/v1` | Enforce in `.env.example`; validate in client startup |
| Use `GROQ_API_KEY` not OpenAI key | `src/config.LLM_API_KEY` selects by `LLM_PROVIDER` |
| Fast inference, strict TPS | Cache identical preference hashes (Phase 5 optional) |
| Model `llama-3.3-70b-versatile` unavailable | Fallback model in env comment; catch 404 and suggest alternate |

---

## 5. UI / presentation

| Edge case | Handling |
|-----------|----------|
| Cache file missing on first run | Banner: run `python scripts/build_cache.py` |
| Parquet load slow | `@st.cache_resource`; show “Loading data…” once |
| Very long explanation | CSS/markdown truncate with “Read more” expander |
| `rating` is `None` in result | Display “Rating N/A” |
| `cost_for_two` is `None` | Display “Price not listed” |
| Unicode in restaurant name | UTF-8 throughout; Streamlit handles if data is clean |
| No API key in demo | Show fallback results + setup instructions |
| User changes prefs without resubmit | Do not auto-call Groq (cost control) |

---

## 6. Security & operations

| Edge case | Handling |
|-----------|----------|
| API key in chat / committed to git | **Rotate key in Groq console**; use `.env` only for secrets; avoid pushing `.env.example` with real keys to public repos |
| Logging prompts | Redact phone numbers; do not log full API key |
| PII in dataset | `phone` excluded from cache and LLM payload |
| `.env` not found | `load_dotenv` silent; warn if `LLM_API_KEY` missing at LLM call time |

---

## 7. Testing matrix (smoke)

Use these inputs during Phase 04–05:

1. **Happy path**: Bangalore, medium, Chinese, min 4.0 → non-empty, 5 results, all names in filter set  
2. **Strict**: min rating 5.0 + high budget + rare cuisine → empty or 1–2 results + helpful message  
3. **Wide**: city only, no cuisine, min 0 → many candidates, LLM still returns ≤ K  
4. **Alias city**: Delhi vs New Delhi → consistent behavior after canonical map  
5. **Groq down**: mock 503 → fallback + `llm_used=false` in response  
6. **Bad cache**: delete/truncate parquet → clear rebuild instructions  

---

## 8. Implementation checklist

When coding each layer, verify:

- [ ] No crash on `None` rating/cost in filter or display  
- [ ] Empty filter never calls Groq (save quota)  
- [ ] Every LLM restaurant name validated against candidate `id` or `name`  
- [ ] Groq 429/401 distinguished in logs and user messages  
- [ ] `explain_empty()` returns at least one actionable suggestion  
