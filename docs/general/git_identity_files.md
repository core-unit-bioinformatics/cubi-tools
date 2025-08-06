# Requirements: (git) identity file(s)

*The following is only relevant for the tool `ct-git` (legacy name: `auto_git.py`)*

Configuring a git repository requires setting a user name and email address before commits to the repo can be made.
The `ct-git` utility extracts that info from local files. Those files are referred to as "identity files".
By default, these identity files are expected to be located in `$HOME/.config/cubi-tools` and there must be one such file
for each remote that is to be configured; that is, typically, two files will be present: `github.id` and `githhu.id`.
**If these files are not found**, the `ct-git` utility is querying the user for that information and creates
the files for all standard CUBI git remotes.

Identity files are simple text files with two lines:
1. line one specifies the user name
2. line two specifies the email address:

```
your-name
your-email
```

That information is then used to perform the following operation:

```bash
git config user.name <USERNAME>
git config user.email <EMAIL>
```
