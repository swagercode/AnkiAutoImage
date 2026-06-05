> **Disclaimer:** Google image search through Custom Search JSON API / Programmable Search Engine is legacy and fragile. Existing `google_api_key` + `google_cx` setups may keep working until January 1, 2027, but broad Google image search is not expected to be available after that date and Google has not provided a direct Google Images API replacement path. Prefer Nadeshiko for sentence media or Gemini Image for generated images.

# Auto Images - Anki Add-on

Adds media to Anki notes from:
- DDG/Yahoo image backfill, with legacy Google Custom Search support for existing Google setups
- Nadeshiko sentence image/audio/text
- Gemini Image generation through Google GenAI

## Install
1. Install the add-on in Anki.
2. Open `Tools -> AutoImage -> Settings` and add the API keys you use.
3. Run `Tools -> AutoImage -> Run` or `Browser -> Edit -> Auto Images` once before using review hotkeys, so the hotkeys can reuse your selected fields.

## API Keys
- Nadeshiko: https://nadeshiko.co/settings/developer
- Gemini API: https://aistudio.google.com/apikey
- Legacy Google image search: https://developers.google.com/custom-search/v1/overview and `cx` from https://programmablesearchengine.google.com/controlpanel/create

## Config
See [config.json](config.json) for the full default config.

- `provider_preference`: image backfill order. Use any of `ddg`, `yahoo`, `google`.
- `google_api_key` / `google_cx`: only needed for legacy Google Custom Search image results.
- `google_genai_api_key`: required for Gemini Image generation. `GEMINI_API_KEY` also works.
- `google_genai_model`: defaults to `gemini-3.1-flash-image`. Imagen model IDs are still supported if configured explicitly.
- `google_genai_prompt_template`: prompt template for generated images. Use `{term}` for the source field value.
- `nadeshiko_api_key`: required for Nadeshiko.
- `nadeshiko_min_length` / `nadeshiko_max_length`: optional sentence length bounds. `0` disables the max bound.
- `nadeshiko_sentence_lang` / `nadeshiko_sentence_en_lang`: defaults to Japanese in the main sentence field and English in the optional EN field.
- `reviewer_hotkey`, `reviewer_hotkey_nadeshiko`, `reviewer_hotkey_genai`: review-mode shortcuts.

## Usage
- Open `Tools -> AutoImage -> Run` for a deck, or `Browser -> Edit -> Auto Images` for selected notes.
- Choose a `Query Field`.
- Choose a provider:
  - `Google`: image-search backfill using `provider_preference`.
  - `Nadeshiko`: image/audio/sentence fields, with optional `Sentence EN Field`.
  - `Gemini Image`: generated image written to the target field.
- Click `Run`.

Review hotkeys:
- Google/image backfill: `Ctrl+Shift+G`
- Nadeshiko image/audio/sentence: `Ctrl+Shift+Y`
- Gemini Image: `Ctrl+Shift+U`

Hotkeys use the last saved fields for that provider. Google and Gemini Image hotkeys overwrite the target image field. The Nadeshiko hotkey overwrites image/audio fields and writes sentence text when matching fields are available.

## Logs
- Logs: `user_files/auto-image.log`
- Legacy Google quota counter: `user_files/quota.json`

## Attribution
Inspired by the design and UX flow in the Yomitan backfill add-on: https://github.com/Manhhao/backfill-anki-yomitan
