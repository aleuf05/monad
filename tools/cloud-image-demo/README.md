# Cloud Image Demonstration

This demonstration proves the bounded pipeline:

1. a prompt derived from Admiral/Captain conversation;
2. cloud generation through OpenAI's Image API;
3. base64 decoding to a local PNG;
4. a JSON provenance sidecar with model, request ID, and SHA-256;
5. a separately authorized installation into Monad's live `web/` tree.

The generator defaults to `artifacts/cloud-image-demo/`, which is not served by
the live site. It refuses destinations under `web/` unless
`--allow-live-target` is supplied.

## Prepared generation command

```bash
python3 tools/cloud-image-demo/generate_image.py \
  --prompt-file tools/cloud-image-demo/monad-actual.prompt.txt
```

The command requires `OPENAI_API_KEY` in the process environment. Never place
the key in the prompt, command history, repository, output sidecar, or website.
The API call may incur cost and may require OpenAI organization verification.

## Live demonstration boundary

After generation, inspect the PNG and sidecar. A separate production-approved
step will:

1. copy the accepted PNG to `web/assets/generated/monad-actual.png`;
2. copy a public-safe provenance record without request identifiers or secrets;
3. add a prominent `NEW` card to `web/index.html`;
4. regenerate `web/command-deck.html` with
   `python3 tools/sync-command-deck.py --write`;
5. verify the asset and homepage through `https://cameronlampley.com/`.

Do not call the image live until both URLs return the expected content.
