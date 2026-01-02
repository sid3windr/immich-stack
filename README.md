# Immich Stacker

## Introduction

While it's less common these days with everyone using their smartphones as a
digital camera, my older albums have both the JPG and the NEF (RAW) version
of my pictures. As Immich supports both formats, it's reporting them as
duplicates. With this script, you can automatically stack these duplicates, if the
filenames are equal (apart from the extension).

## Requirements

* Python 3
* An [Immich](https://immich.app) account
* An API key for your account

## Creating an API key

* Click on your profile icon in the top right, then choose **Account Settings**.
* Fold out **API Keys** and click **New API Key**.
* Give it a useful name, like **immich-stack**.
* Give it **album.read**, **duplicate.read** and **stack.create** permissions .
* Click **Create**. You'll be presented with a single chance to copy this API
key to your clipboard. Put it in your INI file (see below) and/or your
password manager.

## Configuration

### INI configuration

The script reads `immich.ini` in the same directory as the script.

```
[immich]
url=https://immich.example.com
api_key=f9c899b3bef7fbe7c77729099c1463e5
```

The `immich` section requires your Immich instance's URL, and the API key as
created above.

### Environment variables

The script can also use environment variables instead of the INI file.
If the INI value is set, it will take precedence over the environment
variables.

Immich environment variable names are `IMMICH_URL` and `IMMICH_API_KEY`.

## Usage

To just show what would be stacked, without actually
stacking, use the dry run option:

```
./stack.py --dry-run
```

To stack your identically named duplicates, just run:

```
./stack.py --stack
```

While the script only has one function, I didn't want to start messing with
your Immich instance if you ran it without parameters.

**Important**: If you don't pass either the `all-albums` or one or more `--album`
parameters, the script will ONLY process the pictures Immich itself already detected
as duplicates.

The `--album` parameter takes an Immich album ID (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx).
The `--all-albums` parameter simply processes every one of your albums in sequence.

To stack all similarly named photos in all of your albums, run:

```
./stack.py --stack --all-albums
```
