# Publish this project page on GitHub Pages

The page is a standalone static website in `docs/`. It needs no npm install,
build service, API key or database.

For the repository owner, the first publication requires one repository setting:

1. Open **Settings → Pages**.
2. Under **Build and deployment → Source**, select **GitHub Actions**.
3. In **Actions → Project page**, run the workflow on `main` if the initial
   push preceded enablement.

Subsequent changes to `docs/` deploy automatically. The workflow publishes only
`docs/`, not the source package or local data. The expected public URL is:

https://oliverdou776.github.io/Transporting-Root-Evidence-for-Repeated-Adsorption-Ranking/

To preview locally:

```bash
python -m http.server 8000 --directory docs
```

Then open http://localhost:8000. The recorded-results selector uses bundled
JavaScript values; it performs no new scientific computation.
