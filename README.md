# Auto Images from Pexels (Anki Add-on)

Adds images to notes using the Pexels API. Run over selected notes from the Browser, or over an entire deck from Tools.

## Install

1. Place this folder as an add-on in Anki's add-ons directory (development install), or zip and import.
2. Add your Pexels API key to `config.json`.
3. Restart Anki.

## Configure

Edit `config.json`:

```
{
	"pexels_api_key": "YOUR_KEY",
	"default_per_page": 1,
	"default_replace": false
}
```

- `pexels_api_key`: Your Pexels API key
- `default_per_page`: Number of results requested from Pexels (takes first)
- `default_replace`: Replace existing target field content if true

## Usage

- Tools → Auto Images from Pexels: select deck, choose Query Field and Target Field, set options, Run
- Browser → Edit → Auto Images from Pexels: works on currently selected notes

The add-on takes the text from the Query Field, searches Pexels, downloads the first match, stores it in media, and writes an `<img>` tag to the Target Field.

## Notes

- Some searches may return no images; those notes are skipped.
- Large downloads can be slow depending on connection.
- Logs are written to `user_files/auto-image.log`.

## Attribution

Inspired by the design and UX flow in the Yomitan backfill add-on: [backfill-anki-yomitan](https://github.com/Manhhao/backfill-anki-yomitan).

