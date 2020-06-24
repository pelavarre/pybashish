#!/usr/bin/env python3


# demo briefly

import pprint
import shlex

import subsh

echo = subsh.ShVerb("echo")

rc = echo("Hello", "ShVerb", "World")
rc
pprint.pprint(rc.vars)


# add verbs

rm = subsh.ShVerb("rm")
mkdir = subsh.ShVerb("mkdir")
ls = subsh.ShVerb("ls")
touch = subsh.ShVerb("touch")
tar = subsh.ShVerb("tar")
grep = subsh.ShVerb("grep")


# let each exit status return

echo("Hello", "ShVerb", "World")
rm("-fr", "alef/", "alef.gz")
mkdir("alef")
ls("-d", "alef/")
touch("alef/bet")
tar("vcf", "alef.gz", "alef/")
tar("vtkf", "alef.gz")
grep(*shlex.split("--exclude-dir .git -lR subsh ."))


# explicitly discard each exit status

_ = echo("Hello", "ShVerb", "World")
_ = rm("-fr", "alef/", "alef.gz")
_ = mkdir("alef")
_ = ls("-d", "alef/")
_ = touch("alef/bet")
_ = tar("vcf", "alef.gz", "alef/")
_ = tar("vtkf", "alef.gz")
_ = grep(*shlex.split("--exclude-dir .git -lR subsh ."))


# let args, stdout, stderr, returncode, etc return

echo("Hello", "ShVerb", "World").vars
rm("-fr", "alef/", "alef.gz").vars
mkdir("alef").vars
ls("-d", "alef/").vars
touch("alef/bet").vars
tar("vcf", "alef.gz", "alef/").vars
tar("vtkf", "alef.gz").vars
grep(*shlex.split("--exclude-dir .git -lR subsh .")).vars


# pulled from:  git clone https://github.com/pelavarre/pybashish.git
