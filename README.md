> **Disclaimer:** Google image search through Custom Search JSON API / Programmable Search Engine is legacy and fragile. Existing `google_api_key` + `google_cx` setups may keep working until January 1, 2027, but broad Google image search is not expected to be available after that date and Google has not provided a direct Google Images API replacement path. Prefer Nadeshiko for sentence media or Gemini Image for generated images.

# Auto Images - Anki Add-on

Adds media to Anki notes from:
- Yahoo image backfill, with legacy Google Custom Search support
- Nadeshiko sentence image/audio/text
- Gemini Image generation through Google GenAI

## Install
1. Install the add-on in Anki.
2. Open `Tools -> AutoImage -> Settings` and add the API keys you use.
3. Run `Tools -> AutoImage -> Run` or `Browser -> Edit -> Auto Images` once before using review hotkeys, so the hotkeys can reuse your selected fields.

## API Keys
- Nadeshiko: https://nadeshiko.co/user/developer
- Gemini API: https://aistudio.google.com/apikey
- Legacy Google image search: https://developers.google.com/custom-search/v1/introduction and `cx` from https://programmablesearchengine.google.com/controlpanel/all

## Settings
Open `Tools -> AutoImage -> Settings`. The settings UI is also used by Anki's add-on `Config` button.

Tabs:
- `General`: replace behavior, image-search provider order, and shared query prefix/suffix settings.
- `Legacy Google`: Google Custom Search API key and Programmable Search engine ID for existing Google setups.
- `Nadeshiko`: API key, sentence length bounds, default media/sentence fields, sentence languages, and query suffix.
- `Gemini Image`: Gemini API key, image model, aspect ratio, person-generation policy, and prompt template.
- `Hotkeys`: review-mode shortcuts for image search, Nadeshiko, and Gemini Image.

See [config.json](config.json) for the shipped defaults. Advanced users can still edit the raw JSON through Anki's add-on config storage, but normal setup should use the Settings UI.

## Usage
- Open `Tools -> AutoImage -> Run` for a deck, or `Browser -> Edit -> Auto Images` for selected notes.
- Choose a `Query Field`.
- Choose a provider:
  - `Image Search`: image-search backfill using the provider order from Settings.
  - `Nadeshiko`: image/audio/sentence fields, with optional `Sentence EN Field`.
  - `Gemini Image`: generated image written to the target field.
- Click `Run`.

Yahoo is the default no-key image-search provider.

Review hotkeys:
- Image search backfill: `Ctrl+Shift+G`
- Nadeshiko image/audio/sentence: `Ctrl+Shift+Y`
- Gemini Image: `Ctrl+Shift+U`

Hotkeys use the last saved fields for that provider. Image Search and Gemini Image hotkeys overwrite the target image field. The Nadeshiko hotkey overwrites image/audio fields and writes sentence text when matching fields are available.

## Example

<img width="847" height="657" alt="image" src="https://github.com/user-attachments/assets/5f3a1d7e-02e0-468b-bf6e-2887e78c4413" />

## Logs
- Logs: `user_files/auto-image.log`
- Legacy Google quota counter: `user_files/quota.json`

## Attribution
Inspired by the design and UX flow in the Yomitan backfill add-on: https://github.com/Manhhao/backfill-anki-yomitan
