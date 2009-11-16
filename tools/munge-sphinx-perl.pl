#!/usr/bin/perl -w

use strict;

# Sphinx is not really designed to work with Perl documentation (for
# instance, it can't cope with the Perl "class is a module" equivalence,
# so gets very confused about the saliweb::frontend class inside the
# saliweb::frontend module). So we fix up the output HTML here.

my $backup;
for my $file (glob('doc/.build/html/*.html'),
              glob('doc/.build/html/*.inv'),
              glob('doc/.build/html/*.js'),
              glob('doc/.build/html/modules/*.html')) {
    $backup = $file . ".backup";
    rename($file, $backup) or die "Cannot rename $file to $backup: $!";
    open(IN, "$backup") or die "Cannot open $backup: $!";
    open(OUT, ">$file") or die "Cannot open $file: $!";
    while(<IN>) {
        # Add :: back to the saliweb::frontend class (Sphinx doesn't
        # allow :: in class names, so we call the class saliwebfrontend
        # in the rst)
        s/saliwebfrontend/saliweb::frontend/g;
        s/saliwebTest/saliweb::Test/g;

        # Fix Python-style links generated by Sphinx (saliweb::frontend.myclass)
        # to be valid Perl syntax (saliweb::frontend::myclass).
        s/saliweb::frontend\./saliweb::frontend::/g;
        s/saliweb::Test\./saliweb::Test::/g;

        # Since the saliweb::frontend class is not defined in a module,
        # Sphinx will call it a built-in class in the index. Correct that
        # to "Perl class".
        s/built\-in class/Perl class/g;

        print OUT;
    }
    close IN or die "Cannot close $backup: $!";
    close OUT or die "Cannot close $file: $!";
    unlink($backup) or die "Cannot unlink $backup: $!";
}
