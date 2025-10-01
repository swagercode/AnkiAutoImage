# Auto Images — Anki Add-on

Adds images to notes using multiple providers:
- Google Custom Search JSON API (image search)
- DuckDuckGo Images
- Yahoo Images (with optional Playwright scraping)
- Nadeshiko (image + audio, picks the longest sentence)
- Google GenAI (Imagen) image generation

Run over selected notes from the Browser, or over an entire deck from Tools.

If it's useful please star so employers think I'm cool.

Menu entries in Anki:
- Tools → Auto Images (Google) (run over a deck)
- Browser → Edit → Auto Images (Google) (run over selected notes)

## Install

1. Place this folder as an add-on in Anki's add-ons directory (or zip and import).
2. If you plan to commit a ready-to-run build, vendor the dependencies:
   - Run: `python tools/vendor_deps.py` (installs into `vendor/` from `vendor_requirements.txt`).
   - Commit the `vendor/` directory so users don't need to `pip install`.
3. Edit `config.json` (see below) for provider/API settings and hotkeys.
4. Restart Anki.

## Getting API Keys
1. Google API key from this link: https://developers.google.com/custom-search/v1/overview
2. CX Key from here: https://programmablesearchengine.google.com/controlpanel/create

## Configure

Edit `config.json` (keys shown below):

```
{
	"default_replace": false,
	"query_prefix": "",
	"query_suffix": "",
	"append_photo_suffix": true,
	"provider_preference": ["google"],
	"ddg_locale": "ja-jp",
	"google_api_key": "REPLACE_WITH_YOUR_GOOGLE_API_KEY",
	"google_cx": "REPLACE_WITH_YOUR_GOOGLE_CX",
	"reviewer_hotkey": "Ctrl+Shift+G",
	"reviewer_hotkey_nadeshiko": "Ctrl+Shift+Y",
	"reviewer_hotkey_genai": "Ctrl+Shift+U",
	"nadeshiko_api_key": "REPLACE_WITH_YOUR_NADESHIKO_API_KEY",
	"nadeshiko_base_url": "https://api.brigadasos.xyz/api/v1",
	"nadeshiko_image_field": null,
	"nadeshiko_audio_field": null,
	"nadeshiko_query_suffix": "",
	"google_genai_api_key": "REPLACE_WITH_YOUR_GENAI_API_KEY",
	"google_genai_model": "models/imagen-4.0-fast-generate-001",
	"google_genai_aspect_ratio": "1:1",
	"google_genai_person_generation": "ALLOW_ALL",
	"google_genai_prompt_template": "create an image to demonstrate the meaning of {term}"
}
```

- `default_replace`: If true, overwrite the Target Field instead of appending.
- `query_prefix` / `query_suffix`: Prepended/appended to the field text when searching.
- `append_photo_suffix`: When true, UI defaults to adding a suffix like `イラスト` to Google queries.
- `provider_preference`: Search order for backfill. Any of `"ddg"`, `"yahoo"`, `"google"`.
- `ddg_locale`: Locale passed to DuckDuckGo (e.g., `ja-jp`).
- `google_api_key` / `google_cx`: Required for Google Custom Search (image).
- `reviewer_hotkey`: Quick-add Google image on current card. Default `Ctrl+Shift+G`.
- `reviewer_hotkey_nadeshiko`: Quick-add Nadeshiko image+audio. Default `Ctrl+Shift+Y`.
- `reviewer_hotkey_genai`: Quick-generate image via Google GenAI. Default `Ctrl+Shift+U`.
- `nadeshiko_*`: API key and options. The add-on requests the longest sentence directly from the API (descending length) and uses the first result.
- `google_genai_*`: Settings for Imagen generation (model, aspect ratio, person generation policy, prompt template).

Notes on quota:
- Google CSE requires both `google_api_key` and `google_cx`. The dialog shows a convenience counter (out of 100/day) and stores it in `user_files/quota.json` (Pacific Time rollover). You are responsible for your own quota limits.

## Usage

- Open the dialog, choose a deck (Tools) or select notes (Browser).
- Enter `Query Field` (source text).
- Provider:
  - Google/DDG/Yahoo: also select `Target Field` for the image.
  - Nadeshiko: select image/audio/sentence fields; the API returns the longest sentence for the query.
  - Gemini (Google GenAI): select `Target Field`; generates an image with the configured prompt template.
- Options: `Replace existing`, and an optional query suffix for Google (defaults to `イラスト`).
- Click Run. The add-on saves media to Anki and writes `<img src="...">` or `[sound:...]` accordingly.

While reviewing (hotkeys):
- Google image: `Ctrl+Shift+G`
- Nadeshiko image+audio: `Ctrl+Shift+Y`
- Google GenAI image: `Ctrl+Shift+U`

Hotkeys use the last settings chosen in the dialog (per provider). Google and GenAI overwrite the target field when invoked via hotkey.

If keys are missing, the dialog will warn you.

## Logs

- Rotating logs are written to `user_files/auto-image.log`.
- If Google is used, a simple daily quota counter is kept at `user_files/quota.json` (Pacific Time rollover).

## Test without Anki (optional)

You can fetch images to a folder from the command line for quick testing:

```
python test_fetch_images.py --query "猫" --count 5 --out test_images --provider google
```

This respects `config.json` (Google keys).

## Example

<img width="847" height="657" alt="image" src="https://github.com/user-attachments/assets/5f3a1d7e-02e0-468b-bf6e-2887e78c4413" />


## Attribution

Inspired by the design and UX flow in the Yomitan backfill add-on: https://github.com/Manhhao/backfill-anki-yomitan
