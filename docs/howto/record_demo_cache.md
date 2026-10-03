# Record the demo cache

Demo mode replays **real** chat answers recorded earlier, so the showcase works even when no model is loaded. Recordings are never edited; a stream that ended in an error is not stored.

1. Start Ollama with the profile's model (the `full` profile is preferred for recordings).
2. Record:

   ```bash
   uv run poe record-demo                              # every IPO with an X-Ray
   uv run poe record-demo -- --ipo ather-energy-2025  # one IPO
   ```

   For each IPO it asks the suggested questions (normal, a scale trick, Hindi and an advice question) and a few extra questions, through the real chat pipeline. The events are stored exactly as sent, in `data/demo_cache/<ipo_id>/`.
3. Stop Ollama afterwards.
4. Turn demo mode on with `DEMO_MODE=1`: recorded questions are replayed and any other question goes to the live model. A request with `demo: true` and no recording gets an error event, never an invented answer.

The cache is not committed. Re-record it after any change to retrieval, prompts or the verifier.
