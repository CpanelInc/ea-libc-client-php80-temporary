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

