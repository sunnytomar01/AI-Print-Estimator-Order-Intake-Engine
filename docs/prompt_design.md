# Prompt Design

We ask the LLM to return strict JSON only. Example template:

```
You are a strict JSON extractor. Given the following order text, output EXACTLY a JSON object (no explanations) matching schema:
{
  "product_type": "",
  "quantity": 0,
  "size": "",
  "paper_type": "",
  "color": "",
  "finishing": [],
  "turnaround_days": 0,
  "rush": false,
  "missing_fields": []
}
Ensure you respond ONLY with JSON. If a field cannot be found, set it to null and include the field name in `missing_fields`.
```

Notes:
- Force `JSON-only` by instructing the model and providing examples.
- Clean model output by extracting the first JSON object in the response.
- Provide a validation pass after parsing to identify missing or malformed fields.
