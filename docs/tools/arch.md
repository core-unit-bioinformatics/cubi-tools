# CUBI Tool "arch" / cubitools arch

## Developer info

The `arch` subcommand has already been refactored to support the `cubitools` library, i.e.
the shared codebase for all CUBI Tools. Notably, the `arch` subcommand works **w/o** the
CUBI Tools TOML configuration file (as opposed to other subcommands such as `git`, see
details about the CUBI Tools TOML configuration file in [the git docs](git.md)).
A missing CUBI Tools TOML configuration will raise a warning during startup that
can be ignored.

## Main usecases

The `arch` subcommand aims at supporting the following usecases:

### 1 - archiving project directories

Create a `.tar[.compress-suffix]` of one or many project directories, potentially split over
several files to ease file transfer or meet upload requirements.

The following is an exemplified standard invocation:

```bash
# after installing the CUBI tools...
$ cubitools arch --archive-dirs dirpath1 dirpath2 dirpath3 --out-prefix some/path/to/out/archive-prefix

```

This call will achieve the following:

1. scan all files in all folders specified after `--archive-dirs`.
    - by default: this skips over hidden and symbolic entries
2. group all files in batches by `dirpath`
    - by default: the total file size per batch is limited to 1 terabyte, which can be changed via `--chunk-limit`.
    - by default: the grouping does not cross `dirpath` boundaries, i.e. files from one `dirpath` will end
      up in the same archive `.tar` or be distributed over several `.tar` archives, but they won't be
      mixed with files from another `dirpath`
        - reasoning: this enables you to logically separate files from projects, e.g., separating custom annotation
          or reference files from actual results. If data need to be recovered from the archive, this putatively
          limiting the number of `.tar` files that need to be touched during that process.
3. obtains size information and computes checksums for all files
    - by default: MD5 and SHA256 are standard; currently, SHA1 is also supported and can be configured via `--checksums`.
    - by default: checksum computation is performed in parallel governed by the `--jobs` parameter, which defaults to 1.
        - if you want to change the `--jobs` parameter, it has to specified before the subcommand, i.e. `cubitools --jobs 10 arch [...]`.
4. creates either a single `.tar`...
    - if a single `dirpath` is specified AND the total size of all files is below the `--chunk-limit`
    - for a single output `.tar` file, the name is fixed to `some/path/to/out/archive-file.tar[.compress-suffix]`
5. or creates multiple `.tar` files...
    - if multiple arguments are specified after `--archive-dirs`
        - in the example above, the minimal output would be three `.tar` files, one per `dirpath`
        - further splitting over several `.tar` files may happen depending on the `--chunk-limit`.
    - for multiple output `.tar` files, the inidvidual files are named following the pattern `some/path/to/out/archive-prefix.part[0,1,2,3...].tar[.compress-suffix]`.
6. compresses the `.tar` files with `gzip` or `xz`, which can be set via `--compress`
    - by default: `gzip` (file extension `.gz`) is used by default because it is assumed to be always available
    - by default: one process (limited by `--jobs`) is started per file group/partition
7. creates one manifest file per `.tar` file
    - by default: the manifest file is of the type 'complete' (see below for other types)
    - a 'complete' manifest file is a TSV file listing the relative file path, the file size in byte, the MD5 and the SHA256 file checksum
    - additional checkums can be set via `--checksums` (currently supported: MD5, SHA1, SHA256)
    - checksums not requested will be listed as `n/a` in the 'complete' manifest
8. creates a SHA256 checksum file for each `.tar` file

### 2 - only computing manifest files

Create a manifest file of one or many project directories. This includes file checksum
computation but does not create the `.tar` archives.

The following is an exemplified standard invocation:

```bash
# after installing the CUBI tools...
$ cubitools arch --archive-dirs dirpath1 dirpath2 dirpath3 --out-prefix some/path/to/out/archive-prefix --manifest-only

```


### 3 - including and excluding files and folders

Create a `.tar[.compress-suffix]` of one or many project directories, potentially split over
several files to ease file transfer or meet upload requirements. Selectively include or exclude
directories or files.

**Note**: by default, `cubitools arch` skips hidden ('dot') files and folders and does not follow
symlinks when traversing a folder hierarchy. These two options are set explicitly by the special
values 'hidden' and 'symbolic' for the `--exclude-*` parameters.

The following is an exemplified standard invocation:

**Caveat**: note the double quotes around the glob pattern `"*.bam"` to prevent it from being
expanded by the shell in the current working directory:

```bash
# after installing the CUBI tools...
$ cubitools arch --archive-dirs dirpath1 dirpath2 dirpath3 --out-prefix some/path/to/out/archive-prefix \
--exclude-file hidden symbolic "*.bam"

```

The above excludes all hidden files (= not directories) and symbolic links, as well as all files matching "*.bam".

In the order of operations, exclusions take precedence over inclusions, e.g., the following does NOT work:

```bash
# after installing the CUBI tools...
$ cubitools arch --archive-dirs dirpath1 dirpath2 dirpath3 --out-prefix some/path/to/out/archive-prefix \
--exclude-file hidden symbolic "*.bam"
--include-file "*.2.bam"  # wrong - these files were already excluded
```

If an inclusion criterion is set, then everything else is excluded by default:

```bash
# after installing the CUBI tools...
$ cubitools arch --archive-dirs dirpath1 dirpath2 dirpath3 --out-prefix some/path/to/out/archive-prefix \
--include-file "*.vcf.gz"
```

In the above call, only files matching `*.vcf.gz` would be archived; if any of the `dirpath`s does not contain
these file types, the respective `dirpath` would be skipped in the archiving process.

If you specify an include rule that leads to no files at all, you will get an error message because this
is probably not what you wanted.


## Manifest types

The four different manifest types that can be specified via `--manifest` are as follows:

1. `--manifest complete` (the default)
    - columns:
        1. relative file path including the path component specified for `--archive-dirs`
        2. file size in byte
        3. (and following) requested checksums as specified via `--checksums`; other supported checksums are listed with the value `n/a`
2. `--manifest minimal`
    - columns:
        1. file name
        2. file size in byte
        3. the shortest of all supported checksums, which currently selects MD5
3. `--manifest coreutils`
    - a manifest file compatible with the `--check` option of the GNU coreutils such as `md5sum`, `sha25sum` and so on.
    - columns:
        1. requested checksum as specified via `--checksums` --- only a single checksum is supported
        2. relative file path including the path component specified for `--archive-dirs`
4. `--manifest skip`
    - no manifest file is created; generally discouraged


## Parallel computations

The `--jobs` parameter should be scaled according to the I/O performance of your system and not by the number
of available CPU cores.

```bash
$ cubitools --jobs 128 arch [...]  # a questionable choice...
```

File checksum computations and creating the (compressed) `.tar` files both work in parallel, so setting `--jobs`
to a high number will likely make your system choke on the parallel I/O and slowdown overall progress.

