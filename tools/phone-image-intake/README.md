# Phone Image Intake

Minimal human workflow:

1. Generate an image in the ChatGPT phone app.
2. Download the approved candidate.
3. Run `monad-image-push` in Termux.
4. Tell the Captain: `Review the latest image.`
5. After review, tell the Captain: `Publish it.`

The uploader selects the newest PNG, JPEG, or WebP in Android Downloads,
uploads it over SSH, and invokes Granite's validator. The validator checks
content type and size, hashes the image, and stores it under the ignored private
directory `data/image-intake/pending/` with a JSON provenance sidecar.

Nothing in this intake step writes under `web/` or publishes an image.

## One-time phone installation

After phone-to-Granite SSH is working:

```bash
termux-setup-storage
mkdir -p ~/bin
scp cgl@192.168.0.100:/home/cgl/dev/monad/tools/phone-image-intake/monad-image-push ~/bin/
chmod 700 ~/bin/monad-image-push
```

Ensure `~/bin` is on the Termux `PATH`, then run:

```bash
monad-image-push
```

Override connection details with `MONAD_GRANITE_HOST` or
`MONAD_GRANITE_REPO` when necessary.
