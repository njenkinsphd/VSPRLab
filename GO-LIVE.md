# Putting the VSPR Lab site online

The folder is already a git repository with everything committed. What remains
is a GitHub account, one push, and one settings toggle.

## 1. Make a GitHub account

Go to https://github.com/signup. Use your wisc.edu address so the account reads
as institutional. Pick a username you are willing to have in a URL forever,
because it becomes part of the web address. Something like `njenkinsphd` or
`vsprlab` works. Free accounts get unlimited public repositories and free
website hosting, which is all this needs.

Turn on two-factor authentication when it offers. GitHub requires it now anyway.

## 2. Create the repository

On github.com click the `+` in the top right, then "New repository".

- Repository name: `<your-username>.github.io` (exactly that, including the
  `.github.io` part). This makes it a user site served at the clean root URL.
- Visibility: Public. Free website hosting requires it.
- Do not add a README, a .gitignore, or a license. This folder already has them.

## 3. Push the folder

Open Terminal and paste these, substituting your username.

```
cd "$HOME/Documents/VSPR Website Landscaping"
git remote add origin https://github.com/<your-username>/<your-username>.github.io.git
git push -u origin main
```

Terminal will ask for a username and password. GitHub no longer accepts your
account password here. Instead go to
https://github.com/settings/tokens?type=beta, generate a fine-grained personal
access token with Contents read and write access to this one repository, and
paste that token as the password. macOS keychain will remember it.

Easier alternative if you prefer clicking to typing: install GitHub Desktop from
https://desktop.github.com, choose "Add an Existing Repository", point it at
this folder, and click Publish.

## 4. Turn on GitHub Pages

In the repository, go to Settings, then Pages in the left sidebar.

- Source: Deploy from a branch
- Branch: `main`, folder `/ (root)`
- Save

Give it about two minutes. The site appears at
`https://<your-username>.github.io/`.

## 5. Let the publications job write back

Settings, then Actions, then General. Scroll to "Workflow permissions", choose
"Read and write permissions", and save.

Without this the monthly PubMed refresh runs but cannot commit its results.

To test it now rather than waiting for the first of the month, go to the Actions
tab, pick "Update publications from PubMed", and click "Run workflow".

## 6. Later, a wisc.edu address

A wisc.edu name can point at this site. The mechanism is a DNS CNAME record, and
nothing about the site has to change.

1. Request the domain through UW's website domain procedure. All third-level
   wisc.edu domains are approved by the Office of Strategic Communication under
   policy UW-207. Ask DoIT for a CNAME record pointing your chosen name at
   `<your-username>.github.io`.
2. Once the record exists, add the domain in Settings, then Pages, under Custom
   domain. GitHub writes a `CNAME` file into the repository and issues a free
   certificate within about fifteen minutes.
3. Tick "Enforce HTTPS".

The github.io address keeps working afterwards and redirects to the new one, so
anything you have already shared stays valid.

Two things worth knowing before you ask. UW-207 requires sites on wisc.edu to
meet campus branding and accessibility standards, so someone in communications
may want to look at the page first. And the School of Education may prefer to
delegate a name under their own subdomain, which is usually faster than a
top-level wisc.edu name.

## Notes

- `Headshot.png` and the saved Iowa people page are deliberately excluded from
  the repository. They are source material, not site content.
- Never hand-edit `publications.html`. It is generated. To drop a paper, add its
  PMID to `pmids_exclude.txt` and rebuild.
- After editing `people.json`, run `python3 scripts/build_people.py` before
  committing.
- Fonts load from Google. If UW ever objects on privacy grounds, they can be
  self-hosted from the repository instead.
