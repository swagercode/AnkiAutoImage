# Auto Images (Google CSE) — Anki Add-on

Adds images to notes using Google Custom Search JSON API (image search). Run over selected notes from the Browser, or over an entire deck from Tools.

If it's useful please star so employers think I'm cool.

Menu entries in Anki:
- Tools → Auto Images (Google) (run over a deck)
- Browser → Edit → Auto Images (Google) (run over selected notes)

## Install

1. Place this folder as an add-on in Anki's add-ons directory (or zip and import).
2. Edit `config.json` (see below) to set your Google API key and CSE id.
3. Restart Anki.

## Getting API Keys
1. Google API key from this link: https://developers.google.com/custom-search/v1/overview
2. CX Key from here: https://programmablesearchengine.google.com/controlpanel/create

## Configure

Edit `config.json` (keys shown below):

```
{
	"google_api_key": "REPLACE_WITH_YOUR_GOOGLE_API_KEY",
	"google_cx": "REPLACE_WITH_YOUR_GOOGLE_CX",
	"reviewer_hotkey": "Ctrl+Shift+G",
	"default_replace": false,
	"query_prefix": "",
	"query_suffix": "",
	"ui_default_suffix": "イラスト"
}
```

- `google_api_key`/`google_cx`: Required for Google Custom Search (image).
- `reviewer_hotkey`: Keybind to add/overwrite an image while reviewing (default: `Ctrl+Shift+G`).
- `default_replace`: If true, overwrite the Target Field instead of appending.
- `query_prefix`/`query_suffix`: Applied to the query text taken from the Query Field.
- `ui_default_suffix`: Default suffix shown in the dialog; `イラスト` by default.

Notes on quota:
- Google CSE requires both `google_api_key` and `google_cx`. The dialog shows a convenience counter (out of 100/day) and stores it in `user_files/quota.json`; you are still responsible for your own quota limits.

## Usage

- Open the dialog, choose a deck (Tools) or select notes (Browser).
- Enter `Query Field` (source text) and `Target Field` (where the `<img>` will be written).
-- Optional: adjust `Replace existing` and the query suffix (defaults to `イラスト`).
- Click Run. The add-on searches Google, downloads one image, saves it to Anki media, and writes an `<img src="...">` tag to the Target Field.

While reviewing:
- Press the configured hotkey to add an image to the current card immediately.
- Uses the last settings from the dialog (Query/Target/Suffix). If none saved, attempts sensible defaults based on the note's fields.
- Always overwrites the target field when invoked via hotkey.

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

## Attribution

Inspired by the design and UX flow in the Yomitan backfill add-on: https://github.com/Manhhao/backfill-anki-yomitan
