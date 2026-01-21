# Study Roulette: A Stable Randomizer for Study Recruitment Links

This project is intended for situations where multiple studies are simultaneously recruiting from the same recruitment link. So, a link like:

https://example.edu/sr?email=foo@bar.baz&ts=1769010749&cn=2772222584

might redirect to one of:

https://redcap.example.edu/surveys/?s=12345678&email=foo@bar.baz&ts=1769010749&cn=2772222584
https://redcap.example.edu/surveys/?s=abcdef12&email=foo@bar.baz&ts=1769010749&cn=2772222584

This process merges URL parameters, with configuration-provided parameters taking precedence.

This randomization is stable -- the same initial link will randomize to the same target, even if the available list of studies changes.

## Implementation

This project uses python and fastapi. It does not have a traditional database; it uses text files stored in the filesystem. This should be performant enough for up to a few hundred thousand unique redirect URLs.

Required settings:

* `LOOKUP_DIR` a path, must be readable/writable by this process, where we'll store the computed redirects
* `STUDIES_FILE` A path, must be readable by this process, that will list the potential study links in a weighted list

### Algorithm

* Get the URL parameters, compute a SHA256 hash from them -- I think json.dumps(params, sort_keys=True) will do this stably, store it in `url_hash`
* Set `destination_url` to None
* Look for `LOOKUP_DIR`/`url_hash`
* If it's found, read the file and store the contents in `destination_url`
* Otherwise, pick a random URL from `STUDIES_FILE`, merge the parameters and store the result in `destination_url`
* Store `destination_url` in `LOOKUP_DIR`/`url_hash`
* Return a 302 to `destination_url`

URLs will be parsed, parameter merged, and generated using python's `urllib` module.

### Routes

#### GET /sr

Runs the above algorithm, returns a 302 Found if this is found, or 500 if the algorithm fails for any reason

#### GET /health

Checks to make sure we can read and write to `LOOKUP_DIR` and that `STUDIES_FILE` is readable and well-formed. Always returns a JSON string with the keys `status` and `errors`. If things are okay, return 200 OK with `status` = `'ok'` and `errors` = `[]`. If there are errors, return 500 with `status` = `'error'` and `errors` = `{array_of_error_strings}`.

### `STUDIES_FILE`

This is a tab-delimited file with a header row and two columns, in this order:

1. `URL` A URL to redirect to
2. `weight` A weight for this URL

Lines are separated by either `\n` or `\r\n`. Both (sigh) can be mixed in the same file.

Lines starting with `#` are ignored. Empty lines are completely ignored.

The file must contain at least one non-header, non-ignored row.

URLs are stripped of whitespace and must be parsed correctly by urllib.parse.

Weights must be nonnegative real numbers. Weights are relative -- all weights are divided by the total sum of the weights, so `[1, .5]` and `[100, 50]` will behave identically. A weight of 0 is valid and removes the URL from consideration in randomization. At least one weight must be positive.

### `LOOKUP_DIR`

Contains a set of files with names as lowercase sha256 hex digests. The contents of each file will be a single URL, optionally terminated with a newline. File contents should be trimmed of whitespace before redirecting to URLs. URL format will not be checked before redirecting.

**Important:** `LOOKUP_DIR` should be on a local filesystem that supports POSIX file locking (e.g., ext4, APFS). Network filesystems (NFS, SMB) may not provide reliable locking semantics and could lead to race conditions.

## Troubleshooting

Did a bad redirect wind up in LOOKUP_DIR? Find the file with the bad lookup (use something like `grep`) and edit or delete it.

## Developing

Before comitting changes, make sure `uv run pytest` and `uv run ty check` pass without errors.

## Credits

Written by Nate Vack <njvack@wisc.edu> at the Center for Healthy Minds, UW-Madison.

This work was supported by National Institute of Mental Health under grant 1R01MH139512-01: Optimizing the integration between human and digital support in a meditation app for depression and anxiety

## Copyright

Study Roulette is copyright(c) 2026 Board of Regents of the University of Wisconsin System