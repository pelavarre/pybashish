#!/usr/bin/env python3

import os
import pprint


# Struggle to import more  # FIXME: packaging


def import_subsh():

    import os
    import sys

    sys.path.append(os.path.join(os.path.split(__file__)[0], os.pardir, "bin"))

    import subsh

    return subsh


subsh = import_subsh()


# Call "import subsh" briefly

echo = subsh.ShVerb("echo")

rc = echo("Hello", "ShVerb", "World")
print("+ exit {}".format(rc))
pprint.pprint(rc.vars)


# Pile up the trash somewhere in particular

os.chdir("__pycache__")


# Call "import subsh" simply

rm = subsh.ShVerb("rm")
mkdir = subsh.ShVerb("mkdir")
ls = subsh.ShVerb("ls")
touch = subsh.ShVerb("touch")
tar = subsh.ShVerb("tar")
grep = subsh.ShVerb("grep")


# Let each exit status return

echo("Hello", "ShVerb", "World")
rm("-fr", "alef/", "alef.gz")
mkdir("alef")
ls("-d", "alef/")
touch("alef/bet")
tar("vcf", "alef.gz", "alef/")
tar("vtkf", "alef.gz")
grep("--exclude-dir", ".git", "-lR", "subsh", ".")


# Explicitly discard each exit status

_ = echo("Hello", "ShVerb", "World")
_ = rm("-fr", "alef/", "alef.gz")
_ = mkdir("alef")
_ = ls("-d", "alef/")
_ = touch("alef/bet")
_ = tar("vcf", "alef.gz", "alef/")
_ = tar("vtkf", "alef.gz")
_ = grep("--exclude-dir", ".git", "-lR", "subsh", ".")


# Let args, stdout, stderr, returncode, etc return

echo("Hello", "ShVerb", "World").vars
rm("-fr", "alef/", "alef.gz").vars
mkdir("alef").vars
ls("-d", "alef/").vars
touch("alef/bet").vars
tar("vcf", "alef.gz", "alef/").vars
tar("vtkf", "alef.gz").vars
grep("--exclude-dir", ".git", "-lR", "subsh", ".")


# Empty the trash

_ = rm("-fr", "alef/", "alef.gz")


# copied from:  git clone https://github.com/pelavarre/pybashish.git
