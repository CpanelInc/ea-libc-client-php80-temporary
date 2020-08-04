%if 0%{?rhel} >= 8
%define debug_package %{nil}
%endif

%define soname    c-client
%define somajor   2007
%define shlibname lib%{soname}.so.%{somajor}
%define ea_openssl_ver 1.1.1d-1

%{?scl:%global _scl_prefix /opt/cpanel}
%{?scl:%scl_package lib%{soname}}
%{?scl:BuildRequires: scl-utils-build}
%{?scl:Requires: %scl_runtime}
%{!?scl:%global pkg_name %{name}}

# backwards compatibility so people can build this outside of SCL
%{!?scl:%global _root_sysconfdir %_sysconfdir}
%{!?scl:%global _root_sbindir %_sbindir}
%{!?scl:%global _root_includedir %_includedir}
%{!?scl:%global _root_libdir %_libdir}

Name:    %{?scl_prefix}lib%{soname}
Version: %{somajor}f
# Doing release_prefix this way for Release allows for OBS-proof versioning, See EA-4574 for more details
%define release_prefix 20
Release: %{release_prefix}%{?dist}.cpanel
Summary: UW C-client mail library
Group:   System Environment/Libraries
URL:     http://www.washington.edu/imap/
Vendor: cPanel, Inc.
License: ASL 2.0
Source0: ftp://ftp.cac.washington.edu/imap/imap-%{version}%{?beta}%{?dev}%{?snap}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

%global ssldir  /etc/pki/tls

Patch5: imap-2007e-overflow.patch
Patch9: imap-2007e-shared.patch
Patch10: imap-2007e-authmd5.patch
Patch11: imap-2007f-cclient-only.patch

Patch20: 1006_openssl11_autoverify.patch
Patch21: 2014_openssl1.1.1_sni.patch

Patch30: 0001-add-extra-to-tmp-buffer.patch
Patch31: 0002-These-are-only-used-with-very-old-openssl.patch
Patch32: 0003-I-had-to-repair-this-code-because-I-could-not-turn-l.patch

BuildRequires: krb5-devel%{?_isa}, ea-openssl11 >= %{ea_openssl_ver}, ea-openssl11-devel%{?_isa}, pam-devel%{?_isa}

%description
Provides a common API for accessing mailboxes.

%package devel
Summary: Development tools for programs which will use the UW IMAP library
Group:   Development/Libraries
Requires: %{?scl_prefix}%{pkg_name}%{?_isa} = %{version}-%{release}
Provides: %{?scl_prefix}%{pkg_name}-devel%{?_isa} = %{version}-%{release}

%description devel
Contains the header files and libraries for developing programs
which will use the UW C-client common API.

%package static
Summary: UW IMAP static library
Group:   Development/Libraries
Requires: %{?scl_prefix}%{pkg_name}-devel%{?_isa} = %{version}-%{release}
Provides: %{?scl_prefix}%{pkg_name}-static%{?_isa} = %{version}-%{release}
Requires: krb5-devel%{?_isa}, ea-openssl11-devel%{?_isa}, pam-devel%{?_isa}

%description static
Contains static libraries for developing programs
which will use the UW C-client common API.

%prep
%setup -q -n imap-%{version}%{?dev}%{?snap}

%patch5 -p1 -b .overflow
%patch9 -p1 -b .shared
%patch10 -p1 -b .authmd5
%patch11 -p1 -b .cclient

%patch20 -p1
%patch21 -p1

%if 0%{?rhel} >= 8
%patch30 -p1
%patch31 -p1
%patch32 -p1
%endif

%build
# Kerberos setup
test -f %{_root_sysconfdir}/profile.d/krb5-devel.sh && source %{_root_sysconfdir}/profile.d/krb5-devel.sh
test -f %{_root_sysconfdir}/profile.d/krb5.sh && source %{_root_sysconfdir}/profile.d/krb5.sh
GSSDIR=$(krb5-config --prefix)

# SSL setup, probably legacy-only, but shouldn't hurt -- Rex
export PKG_CONFIG_PATH="/opt/cpanel/ea-openssl11/lib/pkgconfig/"
export EXTRACFLAGS="$EXTRACFLAGS $(pkg-config --cflags openssl 2>/dev/null)"
# $RPM_OPT_FLAGS
export EXTRACFLAGS="$EXTRACFLAGS -fPIC $RPM_OPT_FLAGS"
# jorton added these, I'll assume he knows what he's doing. :) -- Rex
export EXTRACFLAGS="$EXTRACFLAGS -fno-strict-aliasing"
export EXTRACFLAGS="$EXTRACFLAGS -Wno-pointer-sign"
%if 0%{?rhel} >= 8
# In CentOS 8, we have begun a process of what Windows Developers called DLL
# Hell.   Linux probably has a similar expression.
# Anyway the crux of the problem is, libc-client links agains libk5crypto.so
# which in turn links against system openssl, libcrypto.so.
# In CentOS 7, libk5crypto did not link against libcrypto.so, so this was
# introduced in CentOS 8.   So how does this solve the problem?
# Link options -rpath tell it to embed the location in the .so as a place to
# get .so's from.

# MOAR fun: '-Wl,--build-id=uuid'
# This is complex, so bear with me.  Whenever a library or executable is
# linked in Linux, a .build_id is generated and added to the ELF.  This
# .build_id is also shadow linked to a file in /usr/lib.   In all cases the
# .build_id is a cryptographic signature (sha1 hash) of the binaries contents
# and perhaps "seed".  But in the case of libc-client, we build for each
# version of PHP, and just put the library inside the PHP directory namespace,
# but the libraries are binarily identical (at the time of the hash).  So we
# were getting conflicts when we installed the library on multiple versions of
# PHP as both rpm's owned the .build_id file.  So I am telling the linker
# instead of using the normal sha1 hash, to instead use a random uuid, so each
# version of this library will have a different build_id.  Now further
# consideration, the normal form of this would be -Wl,--build-id,uuid, but for
# some reason that form works perfectly for any of the arguments that use a
# single dash, but does not work for the double hash type.  So I did it
# without the comma, and it is treating that as instead of a parameter, value
# but as a single entity on the linker command line.  Man I am getting a
# headache.

export EXTRALDFLAGS="$EXTRALDFLAGS $(pkg-config --libs openssl 2>/dev/null) -Wl,-rpath,/lib64 -Wl,-rpath,/opt/cpanel/ea-openssl11/lib '-Wl,--build-id=uuid'"
%else
export EXTRALDFLAGS="$EXTRALDFLAGS $(pkg-config --libs openssl 2>/dev/null) -Wl,-rpath,/opt/cpanel/ea-openssl11/lib"
%endif

echo -e "y\ny" | \
make %{?_smp_mflags} lnp \
IP=6 \
EXTRACFLAGS="$EXTRACFLAGS" \
EXTRALDFLAGS="$EXTRALDFLAGS" \
EXTRAAUTHENTICATORS=gss \
SPECIALS="GSSDIR=${GSSDIR} LOCKPGM=%{_root_sbindir}/mlock SSLCERTS=%{ssldir}/certs SSLDIR=/opt/cpanel/ea-openssl11 SSLINCLUDE=/opt/cpanel/ea-openssl11/include SSLKEYS=%{ssldir}/private SSLLIB=/opt/cpanel/ea-openssl11/lib" \
SSLTYPE=unix \
CCLIENTLIB=$(pwd)/c-client/%{shlibname} \
SHLIBBASE=%{soname} \
SHLIBNAME=%{shlibname}

%install
rm -rf %{buildroot}

mkdir -p %{buildroot}%{_libdir}/

install -p -m644 ./c-client/c-client.a %{buildroot}%{_libdir}/
ln -s c-client.a %{buildroot}%{_libdir}/libc-client.a

install -p -m755 ./c-client/%{shlibname} %{buildroot}%{_libdir}/

# %%ghost'd c-client.cf
touch c-client.cf
install -p -m644 -D c-client.cf %{buildroot}%{_sysconfdir}/c-client.cf

: Installing development components
ln -s %{shlibname} %{buildroot}%{_libdir}/lib%{soname}.so

mkdir -p %{buildroot}%{_includedir}/c-client/
install -m644 ./c-client/*.h %{buildroot}%{_includedir}/c-client/
# Added linkage.c to fix (#34658) <mharris>
install -m644 ./c-client/linkage.c %{buildroot}%{_includedir}/c-client/
install -m644 ./src/osdep/tops-20/shortsym.h %{buildroot}%{_includedir}/c-client/

%if 0%{?!scl:1}
%post -p /sbin/ldconfig

%postun -p /sbin/ldconfig
%endif

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
%doc LICENSE.txt NOTICE SUPPORT
%doc docs/SSLBUILD docs/RELNOTES docs/*.txt
%ghost %config(missingok,noreplace) %{_sysconfdir}/c-client.cf
%{_libdir}/lib%{soname}.so.*

%files devel
%defattr(-,root,root,-)
%{_includedir}/c-client/
%{_libdir}/lib%{soname}.so

%files static
%defattr(-,root,root,-)
%{_libdir}/c-client.a
%{_libdir}/libc-client.a

%changelog
* Mon Jul 20 2020 Julian Brown <julian.brown@cpanel.net> - 2007-20
- ZC-7170: Add PHP8 macro

* Tue May 26 2020 Julian Brown <julian.brown@cpanel.net> - 2007-19
- ZC-6881: Build on C8

* Mon Jan 27 2020 Daniel Muey <dan@cpanel.net> - 2007-18
- ZC-5915: Rolling “scl-libc-client” back to “c653d5a”: Adding PHP 7.4

* Mon Jan 20 2020 Daniel Muey <dan@cpanel.net> - 2007f-17
- EA-8666: Remove PHP 7.4

* Thu Jan 09 2020 Julian Brown <julian.brown@cpanel.net> - %{somajor}f-16
- ZC-4361: Update to OpenSSL1.1.1

* Tue Dec 24 2019 Daniel Muey <dan@cpanel.net> - 2007f-15
- ZC-5915: Add PHP 7.4

* Tue Feb 05 2019 Daniel Muey <dan@cpanel.net> - 2007f-14
- ZC-4640: Add PHP 7.3

* Mon Apr 16 2018 Rishwanth Yeddula <rish@cpanel.net> - 2007f-13
- EA-7382: Update dependency on ea-openssl to require the latest version with versioned symbols.

* Tue Mar 20 2018 Cory McIntire <cory@cpanel.net> - 2007f-12
- ZC-3552: Added versioning to ea-openssl requirements.
- ZC-3552: Linked to shared openssl .so's.
- ZC-3552: Whitespace clean up.

* Thu Jan 25 2018 Rishwanth Yeddula <rish@cpanel.net> - 2007f-11
- EA-7182: Build against ea-openssl to ensure that any IMAP ssl
  calls made via PHP are functional.

* Tue Aug 22 2017 Dan Muey <dan@cpanel.net> - 2007f-10
- ZC-2810: Add 7.2 support

* Fri Dec 16 2016 Jacob Perkins <jacob.perkins@cpanel.net> - 2007f-9
- EA-5493: Added vendor field

* Mon Aug 01 2016 Edwin Buck <e.buck@cpanel.net> - 2007f-8
- EA-4940: Added support for php71.

* Mon Jun 20 2016 Dan Muey <dan@cpanel.net> - 2007f-7
- EA-4383: Update Release value to OBS-proof versioning

* Thu Jan 28 2016 S. Kurt Newman <kurt.newman@cpanel.net> - 2007f-6.1
- Converted to SCL-compatible package

* Thu Jan 28 2016 S. Kurt Newman <kurt.newman@cpanel.net> - 2007f-5.1
- Package now only compiles libc-client for cPanel PHP packages

* Tue Jan 14 2014 Remi Collet <remi@fedoraproject.org> - 2007f-4.1
- EPEL-7 build (RHEL-7 don't have libc-client)

* Fri Feb 15 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2007f-4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_19_Mass_Rebuild

* Sun Jul 22 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2007f-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_18_Mass_Rebuild

* Sat Jan 14 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2007f-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_17_Mass_Rebuild

* Tue Aug 02 2011 Rex Dieter <rdieter@fedoraproject.org> 2007f-1
- imap-2007f

* Mon Jun 13 2011 Rex Dieter <rdieter@fedoraproject.org> 2007e-13
- _with_system_libc_client option (el6+)
- tight deps via %%?_isa
- drop extraneous Requires(post,postun): xinetd

* Mon Feb 07 2011 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2007e-12
- Rebuilt for https://fedoraproject.org/wiki/Fedora_15_Mass_Rebuild

* Tue Apr 27 2010 Rex Dieter <rdieter@fedoraproject.org> - 2007e-11
- SSL connection through IPv6 fails (#485860)
- fix SSLDIR, set SSLKEYS

* Wed Sep 16 2009 Tomas Mraz <tmraz@redhat.com> - 2007e-10
- use password-auth common PAM configuration instead of system-auth
  where available

* Mon Aug 31 2009 Rex Dieter <rdieter@fedoraproject.org>
- omit -devel, -static bits in EPEL builds (#518885)

* Fri Aug 21 2009 Tomas Mraz <tmraz@redhat.com> - 2007e-9
- rebuilt with new openssl

* Sun Jul 26 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2007e-8
- Rebuilt for https://fedoraproject.org/wiki/Fedora_12_Mass_Rebuild

* Wed Jul 08 2009 Rex Dieter <rdieter@fedoraproject.org> - 2007e-7
- fix shared.patch to use CFLAGS for osdep.c too

* Tue Jul 07 2009 Rex Dieter <rdieter@fedoraproject.org> - 2007e-6
- build with -fPIC
- rebase patches (patch fuzz=0)

* Wed Feb 25 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2007e-5
- Rebuilt for https://fedoraproject.org/wiki/Fedora_11_Mass_Rebuild

* Sun Jan 18 2009 Tomas Mraz <tmraz@redhat.com> 2007e-4
- rebuild with new openssl

* Mon Jan 12 2009 Rex Dieter <rdieter@fedoraproject.org> 2007e-3
- main/-utils: +Req: %%imap_libs = %%version-%%release

* Fri Dec 19 2008 Rex Dieter <rdieter@fedoraproject.org> 2007e-1
- imap-2007e

* Fri Oct 31 2008 Rex Dieter <rdieter@fedoraproject.org> 2007d-1
- imap-2007d

* Wed Oct 01 2008 Rex Dieter <rdieter@fedoraproject.org> 2007b-2
- fix build (patch fuzz) (#464985)

* Fri Jun 13 2008 Rex Dieter <rdieter@fedoraproject.org> 2007b-1
- imap-2007b

* Sun May 18 2008 Rex Dieter <rdieter@fedoraproject.org> 2007a1-3
- libc-client: incomplete list of obsoletes (#446240)

* Wed Mar 19 2008 Rex Dieter <rdieter@fedoraproject.org> 2007a1-2
- uw-imap conflicts with cyrus-imapd (#222486)

* Wed Mar 19 2008 Rex Dieter <rdieter@fedoraproject.org> 2007a1-1
- imap-2007a1
- include static lib
- utils: update %%description

* Thu Mar 13 2008 Rex Dieter <rdieter@fedoraproject.org> 2007a-1
- imap-2007a

* Fri Feb 08 2008 Rex Dieter <rdieter@fedoraproject.org> 2007-3
- respin (gcc43)

* Wed Jan 23 2008 Rex Dieter <rdieter@fedoraproject.org> 2007-2
- Obsoletes: libc-client2006 (#429796)
- drop libc-client hacks for parallel-installability, fun while it lasted

* Fri Dec 21 2007 Rex Dieter <rdieter[AT]fedoraproject.org> 2007-1
- imap-2007

* Tue Dec 04 2007 Rex Dieter <rdieter[AT]fedoraproject.org> 2006k-2
- respin for new openssl

* Fri Nov 09 2007 Rex Dieter <rdieter[AT]fedoraproject.org> 2006k-1
- imap-2006k (final)

* Wed Sep 19 2007 Rex Dieter <rdieter[AT]fedoraproject.org> 2006k-0.1.0709171900
- imap-2006k.DEV.SNAP-0709171900

* Tue Aug 21 2007 Joe Orton <jorton@redhat.com> 2006j-3
- fix License

* Tue Jul 17 2007 Rex Dieter <rdieter[AT]fedoraproject.org> 2006j-2
- imap-2006j2

* Mon Jul 09 2007 Rex Dieter <rdieter[AT]fedoraproject.org> 2006j-1
- imap-2006j1

* Wed Jun 13 2007 Rex Dieter <rdieter[AT]fedoraproject.org> 2006i-1
- imap-2006i

* Wed May 09 2007 Rex Dieter <rdieter[AT]fedoraproject.org> 2006h-1
- imap-2006h
- Obsolete pre-merge libc-client pkgs

* Fri Apr 27 2007 Rex Dieter <rdieter[AT]fedoraproject.org> 2006g-3
- imap-2004a-doc.patch (#229781,#127271)

* Mon Apr  2 2007 Joe Orton <jorton@redhat.com> 2006g-2
- use $RPM_OPT_FLAGS during build

* Mon Apr 02 2007 Rex Dieter <rdieter[AT]fedoraproject.org> 2006g-1
- imap-2006g

* Wed Feb 07 2007 Rex Dieter <rdieter[AT]fedoraproject.org> 2006e-3
- Obsoletes: libc-client2004g
- cleanup/simplify c-client.cf handling

* Fri Jan 26 2007 Rex Dieter <rdieter[AT]fedoraproject.org> 2006e-2
- use /etc/profile.d/krb5-devel.sh

* Fri Jan 26 2007 Rex Dieter <rdieter[AT]fedoraproject.org> 2006e-1
- imap-2006e

* Mon Dec 18 2006 Rex Dieter <rdieter[AT]fedoraproject.org> 2006d-1
- imap-2006d (#220121)

* Wed Oct 25 2006 Rex Dieter <rexdieter[AT]users.sf.net> 2006c1-1
- imap-2006c1

* Fri Oct 06 2006 Rex Dieter <rexdieter[AT]users.sf.net> 2006b-1
- imap-2006b
- %%ghost %%config(missingok,noreplace) %%{_sysconfdir}/c-client.cf

* Fri Oct 06 2006 Rex Dieter <rexdieter[AT]users.sf.net> 2006a-6
- omit EOL whitespace from c-client.cf

* Thu Oct 05 2006 Rex Dieter <rexdieter[AT]users.sf.net> 2006a-5
- %%config(noreplace) all xinetd.d/pam.d bits

* Thu Oct 05 2006 Rex Dieter <rexdieter[AT]users.sf.net> 2006a-4
- eek, pam.d/xinet.d bits were all mixed up, fixed.

* Wed Oct 04 2006 Rex Dieter <rexdieter[AT]users.sf.net> 2006a-3
- libc-client: move c-client.cf here
- c-client.cf: +set new-folder-format same-as-inbox

* Wed Oct 04 2006 Rex Dieter <rexdieter[AT]users.sf.net> 2006a-2
- omit mixproto patch (lvn bug #1184)

* Tue Sep 26 2006 Rex Dieter <rexdieter[AT]users.sf.net> 2006a-1
- imap-2006a
- omit static lib (for now, at least)

* Mon Sep 25 2006 Rex Dieter <rexdieter[AT]users.sf.net> 2006-4
- -devel-static: package static lib separately.

* Mon Sep 25 2006 Rex Dieter <rexdieter[AT]users.sf.net> 2006-3
- License: Apache 2.0

* Fri Sep 15 2006 Rex Dieter <rexdieter[AT]users.sf.net> 2006-2
- imap-2006
- change default (CREATEPROTO) driver to mix
- Obsolete old libc-clients

* Tue Aug 29 2006 Rex Dieter <rexdieter[AT]users.sf.net> 2004g-6
- fc6 respin

* Fri Aug 18 2006 Rex Dieter <rexdieter[AT]users.sf.net> 2004g-5
- cleanup, respin for fc6

* Wed Mar 1 2006 Rex Dieter <rexdieter[AT]users.sf.net>
- fc5: gcc/glibc respin

* Thu Nov 17 2005 Rex Dieter <rexdieter[AT]users.sf.net> 2004g-4
- use pam's "include" feature on fc5
- cleanup %%doc handling, remove useless bits

* Thu Nov 17 2005 Rex Dieter <rexdieter[AT]users.sf.net> 2004g-3
- omit trailing whitespace in default c-client.cf

* Wed Nov 16 2005 Rex Dieter <rexdieter[AT]users.sf.net> 2004g-2
- rebuild for new openssl

* Mon Sep 26 2005 Rex Dieter <rexdieter[AT]users.sf.net> 2004g-1
- imap-2004g
- /etc -> %%_sysconfdir
- use %%{?_smp_mflags}

* Mon Aug 15 2005 Rex Dieter <rexdieter[AT]users.sf.net> 2004e-1
- imap-2004e
- rename: imap -> uw-imap (yay, we get to drop the Epoch)
- sslcerts=%%{_sysconfdir}/pki/tls/certs if exists, else /usr/share/ssl/certs

* Fri Apr 29 2005 Rex Dieter <rexdieter[AT]users.sf.net> 1:2004d-1
- 2004d
- imap-libs -> lib%%{soname}%%{version} (ie, libc-client2004d), so we can
  have multiple versions (shared-lib only) installed
- move mlock to -utils.
- revert RFC2301, locks out too many folks where SSL is unavailable

* Thu Apr 28 2005 Rex Dieter <rexdieter[AT]users.sf.net> 1:2004-0.fdr.11.c1
- change default driver from mbox to mbx
- comply with RFC 3501 security: Unencrypted plaintext passwords are prohibited

* Fri Jan 28 2005 Rex Dieter <rexdieter[AT]users.sf.net> 1:2004-0.fdr.10.c1
- imap-2004c1 security release:
  http://www.kb.cert.org/vuls/id/702777

* Thu Jan 20 2005 Rex Dieter <rexdieter[AT]users.sf.net> 1:2004-0.fdr.9.c
- imap2004c
- -utils: dmail,mailutil,tmail
- -libs: include mlock (so it's available for other imap clients, like pine)
- remove extraneous patches
- %%_sysconfigdir/c-client.cf: use to set MailDir (but don't if upgrading from
  an older version (ie, if folks don't want/expect a change in behavior)

* Mon Sep 13 2004 Rex Dieter <rexdieter at sf.net. 1:2004-0.fdr.8.a
- don't use mailsubdir patch (for now)

* Wed Aug 11 2004 Rex Dieter <rexdieter at sf.net> 1:2004-0.fdr.7.a
- mailsubdir patch (default to ~/Mail instead of ~)

* Fri Jul 23 2004 Rex Dieter <rexdieter at sf.net> 1:2004-0.fdr.6.a
- remove Obsoletes/Provides: libc-client (they can, in fact, co-xist)
- -devel: remove O/P: libc-client-devel -> Conflicts: libc-client-devel

* Fri Jul 16 2004 Rex Dieter <rexdieter at sf.net> 1:2004-0.fdr.5.a
- imap2004a

* Tue Jul 13 2004 Rex Dieter <rexdieter at sf.net> 1:2004-0.fdr.4
- -devel: Req: %%{name}-libs

* Tue Jul 13 2004 Rex Dieter <rexdieter at sf.net> 1:2004-0.fdr.3
- previous imap pkgs had Epoch: 1, we need it too.

* Wed Jul 07 2004 Rex Dieter <rexdieter at sf.net> 2004-0.fdr.2
- use %%version as %%somajver (like how openssl does it)

* Wed Jul 07 2004 Rex Dieter <rexdieter at sf.net> 2004-0.fdr.1
- imap-2004
- use mlock, if available.
- Since libc-client is an attrocious name choice, we'll trump it,
  and provide imap, imap-libs, imap-devel instead (redhat bug #120873)

* Wed Apr 07 2004 Kaj J. Niemi <kajtzu@fi.basen.net> 2002e-4
- Use CFLAGS (and RPM_OPT_FLAGS) during the compilation
- Build the .so through gcc instead of directly calling ld

* Fri Mar  5 2004 Joe Orton <jorton@redhat.com> 2002e-3
- install .so with permissions 0755
- make auth_md5.c functions static to avoid symbol conflicts
- remove Epoch: 0

* Tue Mar 02 2004 Kaj J. Niemi <kajtzu@fi.basen.net> 0:2002e-2
- "lnp" already uses RPM_OPT_FLAGS
- have us conflict with imap, imap-devel

* Tue Mar  2 2004 Joe Orton <jorton@redhat.com> 0:2002e-1
- add post/postun, always use -fPIC

* Tue Feb 24 2004 Kaj J. Niemi <kajtzu@fi.basen.net>
- Name change from c-client to libc-client

* Sat Feb 14 2004 Kaj J. Niemi <kajtzu@fi.basen.net> 0:2002e-0.1
- c-client 2002e is based on imap-2002d
- Build shared version, build logic is copied from FreeBSD net/cclient

