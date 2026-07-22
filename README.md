# Documentation for API-first fintechs, in one click

## What this is and isn't

This script is a scaffold, not a magic pill. It handles the initial setup and
routes you around every known pitfall—each check inside was earned on a real
installation. It doesn't change three facts: the ecosystem keeps moving, you
still write the content for your product, and keeping documentation in sync
with reality is a separate discipline that no generator solves. The author
writes about that discipline separately. <!-- TODO: link -->

The author maintains the scaffold, tracks version compatibility, and updates
the checks. Issues and pull requests are welcome. For anything beyond the
scaffold—tailoring it to your product, design work, an audit of your existing
documentation, or running the portal as a managed service—[contact the
author](https://www.linkedin.com/in/egolovachuk/).

## What you get

A dark terminal-style theme, a deliberate section structure, an API reference
generated from your OpenAPI spec, spec linting, and CI with publishing. The
[official generator](https://github.com/PaloAltoNetworks/docusaurus-openapi-docs)
of the OpenAPI plugin creates the site; the author's content layers on top.
The site ships in English by default, with Russian available as a second
locale.

```bash
python3 bootstrap.py
```

---

## Step 0: Check the prerequisites

Before you start, make sure you have:

- **Python 3.9 or later.** To check, run `python3 --version`.
- **Node.js 20 or later.** To check, run `node --version`. If Node.js is
  missing or older, install the LTS release from
  [nodejs.org](https://nodejs.org), or run `nvm install 22 && nvm use 22`.
- **Your OpenAPI spec** (YAML or JSON). This is optional: without it, the
  script wires up a detailed example spec that you replace later.
- **Internet access.** The script downloads the template and dependencies.

The script also checks the environment and tells you what's missing.

## Step 1: Install

To create the portal in `./api-docs`, run:

```bash
python3 bootstrap.py
```

To use a different folder name, pass it as an argument:

```bash
python3 bootstrap.py my-docs
```

Answer four questions: product name, company, public URL, and the path to
your spec. The script then runs seven steps on its own, marking each with a
green checkmark: it checks the environment, scaffolds the reference site from
the plugin maintainers, adds your content (Quickstart, Authentication,
Scenarios, Error catalog, Changelog), applies the branded theme, configures
the site and removes the demo content, installs dependencies, generates the
reference, and starts a preview at `http://localhost:3000`.

When the script can't configure something automatically, it flags the item
with a yellow `!` and tells you what to fix by hand.

The script accepts these flags:

- `--defaults`: skip the questions and use demo values.
- `--no-start`: don't start the preview server.
- `--skip-scaffold`: use a reference site that's already in place.
- `--deploy=s3`: set up AWS S3 deployment (see [Step 3](#step-3-publish)).

## Step 2: Make the first commit

```bash
cd api-docs
git init && git add -A && git commit -m "docs portal"
```

Commit `package-lock.json`. It pins the verified combination of versions, so
anyone who clones the repository builds the same site you did.

## Step 3: Publish

Choose one of two paths.

### Path A: GitLab Pages or GitHub Pages

You don't configure anything. The pipelines are already in the repository
(`.gitlab-ci.yml` and `.github/workflows/docs.yml`). Push to the default
branch. CI lints the spec, builds the site, and publishes it. To find the
page URL, go to **Settings > Pages** in GitLab or GitHub.

### Path B: AWS S3

To set up S3 deployment, run:

```bash
python3 bootstrap.py --deploy=s3
```

The script asks for two bucket names (staging and production) and a region,
then generates a pipeline with three behaviors: it lints and builds on every
push, deploys to staging automatically from the default branch, and deploys
to production only when you click the manual button in the pipeline. You don't
deploy to production from a laptop.

If you already installed the portal in Step 1 without this flag, don't
reinstall. Run the following instead, which rebuilds only the CI and config
and leaves your content untouched:

```bash
python3 bootstrap.py api-docs --skip-scaffold --deploy=s3
```

#### Set up AWS from scratch

If you've never used AWS, follow these steps.

1. **Create two buckets.** In the AWS Console, go to **S3 > Create bucket**.
   Use the names you give the script, for example `mycompany-docs-staging` and
   `mycompany-docs-prod`. Bucket names are globally unique. Choose one region
   for both, and give that region to the script.
2. **Enable website hosting.** In each bucket, go to **Properties > Static
   website hosting** and select **Enable**. Set the index document to
   `index.html` and the error document to `404.html`. Then, under
   **Permissions**, turn off **Block public access** and add a bucket policy
   that allows `s3:GetObject` for everyone. The console suggests a policy
   template. For a private or production setup, put CloudFront in front of the
   bucket so the bucket stays closed. You can add CloudFront later.
3. **Create keys for CI.** In the AWS Console, go to **IAM > Users > Create
   user**. Name the user `docs-ci` and skip console access. For permissions,
   attach a policy scoped to these two buckets—at minimum `s3:PutObject`,
   `s3:DeleteObject`, and `s3:ListBucket`. The managed `AmazonS3FullAccess`
   policy works at first, but narrow it later. Then go to **Security
   credentials > Create access key** and choose **Third-party service**. You
   get an access key ID and a secret access key. AWS shows the secret only
   once, so save it now.
4. **Store the keys in GitLab, and nowhere else.** In your project, go to
   **Settings > CI/CD > Variables** and add two variables:
   - `AWS_ACCESS_KEY_ID`: the key from step 3.
   - `AWS_SECRET_ACCESS_KEY`: the secret from step 3. Select **Masked**. Also
     select **Protected** if you deploy only from protected branches.

   The keys never enter the repository files. If you set up CloudFront, add a
   third variable, `CLOUDFRONT_DISTRIBUTION_ID`. The pipeline then invalidates
   the cache after each deploy.
5. **Push.** The pipeline builds the site and uploads it to the staging
   bucket. To find the address, go to the bucket's **Static website hosting >
   Bucket website endpoint**. When you're ready to go live, go to **CI/CD >
   Pipelines** in GitLab and click the play button on the `deploy_prod` job.

The script already added `trailingSlash: true` to the config. Without it,
static routing on S3 returns 404 on inner pages.

## Step 4: Maintain the site

Three tasks cover most of the work:

- **Edit content.** Edit the Markdown in `docs/`. The dev server (`npm start`)
  re-renders as you save. Docusaurus compiles `.md` files as MDX, so keep code
  examples that contain `{}` or `<>` inside code blocks.
- **Update the API.** Edit `openapi/openapi.yaml`, then run
  `npm run lint:spec && npx docusaurus gen-api-docs all`. Don't edit the
  `docs/api` folder by hand—the script generates it. Groups in the reference
  map to tags in your spec.
- **Change the look and navigation.** Edit `docusaurus.config.ts` for titles
  and the navbar, and `src/css/custom.css` for colors. The color variables sit
  at the top of the CSS file.

The section structure follows the order of an integrator's questions. Each
section explains its own reasoning. The most important part is the
seven-question scenario template in `docs/scenarios/`.

## Troubleshooting

- **`Minimum Node.js version not met`.** Update Node.js: `nvm install 22`.
- **An error at the scaffolding step.** This is the generator's own output,
  usually a network or proxy problem. To scaffold manually, run
  `npx create-docusaurus-openapi-docs@latest api-docs`, then
  `python3 bootstrap.py api-docs --skip-scaffold`.
- **Reference generation failed.** The spec is almost always invalid. Run
  `npm run lint:spec` to find the problem.
- **`MDX compilation failed ... <!--`.** MDX doesn't allow HTML comments. Use
  `{/* text */}` instead. The script converts them during installation.
- **A page crashes with `... is not defined`.** The Markdown contains bare
  curly braces, such as template placeholders `{{...}}`, and MDX runs them as
  code. Move the example into a code block or remove it.
- **`Hook useDoc is called outside the <DocProvider>`.** Two copies of
  `@docusaurus` packages are in `node_modules`. Run
  `rm -rf node_modules package-lock.json && npm install && npm dedupe`.
- **Anything odd after a version change.** Do a full rebuild:
  `rm -rf node_modules package-lock.json .docusaurus docs/api && npm install &&
  npx docusaurus gen-api-docs all`.

## Versions: why they're pinned and how to upgrade

Docusaurus and the OpenAPI plugin and theme are designed as matched sets. The
base is the maintainers' official template, and the lock file pins the
versions. Don't upgrade these packages one at a time. Instead, check the
compatibility table in the
[plugin's README](https://github.com/PaloAltoNetworks/docusaurus-openapi-docs),
upgrade the whole set together, and do a full rebuild with the command in
[Troubleshooting](#troubleshooting).

## License

MIT. Fork it and use it freely. A credit link to the author is appreciated.
