%define archiversion %(echo %{version} | tr . _ )

Name:		log4j12
Version:	1.2.17
Release:	8
Summary:	Java logging package
Group:		Development/Java
License:	ASL 2.0
URL:		http://logging.apache.org/log4j/1.2/
Source0:	https://github.com/apache/log4j/archive/v%{archiversion}.tar.gz

Source1:	log4j.catalog

Patch0:		0001-logfactor5-changed-userdir.patch
Patch1:		0009-Fix-tests.patch
Patch2:		0010-Fix-javadoc-link.patch

BuildRequires:	jdk-current
BuildRequires:	jmod(java.mail)
BuildRequires:	jmod(java.jms)
BuildRequires:	jmod(java.activation)

BuildArch:     noarch

%description
Log4j is a tool to help the programmer output log statements to a
variety of output targets.

%package javadoc
Summary:       Javadoc for %{name}

%description javadoc
This package contains javadoc for %{name}.

%prep
%setup -q -n log4j-%{archiversion}
# Cleanup
find . -name "*.jar" -print -delete
find . -name "*.class" -print -delete
find . -name "*.dll" -print -delete
rm -rf docs/api

%patch0 -p1 -b .logfactor-home
%patch1 -p1 -b .fix-tests
%patch2 -p1 -b .xlink-javadoc

# Fix OSGi manifest
sed -i.javax.jmdns "s|javax.jmdns.*;resolution:=optional,|!javax.jmdns.*,|g" pom.xml
# Add proper bundle symbolicname
%pom_xpath_inject "pom:build/pom:plugins/pom:plugin[pom:artifactId = 'maven-bundle-plugin']/pom:configuration/pom:instructions" "
  <Bundle-SymbolicName>org.apache.log4j</Bundle-SymbolicName>
  <_nouses>true</_nouses>"

sed -i 's/\r//g' LICENSE NOTICE src/site/resources/css/*.css

# fix encoding of mailbox files
for i in contribs/JimMoore/mail*;do
    iconv --from=ISO-8859-1 --to=UTF-8 "$i" > new
    mv new "$i"
done

%mvn_compat_version log4j:log4j 1.2.17 1.2.12 12
# Remove Microsoft Windows platform specific files
rm -r src/main/java/org/apache/log4j/nt/NTEventLogAppender.java \
 tests/src/java/org/apache/log4j/nt/NTEventLogAppenderTest.java

cat >src/main/java/module-info.java <<'EOF'
module org.apache.log4j.v12 {
	exports org.apache.log4j;
	exports org.apache.log4j.chainsaw;
	exports org.apache.log4j.config;
	exports org.apache.log4j.helpers;
	exports org.apache.log4j.jdbc;
	exports org.apache.log4j.jmx;
	exports org.apache.log4j.lf5;
	exports org.apache.log4j.lf5.util;
	exports org.apache.log4j.lf5.viewer;
	exports org.apache.log4j.lf5.viewer.categoryexplorer;
	exports org.apache.log4j.lf5.viewer.configure;
	exports org.apache.log4j.net;
	exports org.apache.log4j.or;
	exports org.apache.log4j.or.jms;
	exports org.apache.log4j.or.sax;
	exports org.apache.log4j.pattern;
	exports org.apache.log4j.rewrite;
	exports org.apache.log4j.spi;
	exports org.apache.log4j.varia;
	exports org.apache.log4j.xml;

	requires java.jms;
	requires java.mail;
	requires java.activation;
	requires java.xml;
	requires java.management;
	requires java.naming;
	requires java.desktop;
	requires java.sql;
}
EOF

%build
cd src/main/java
find . -name "*.java" |xargs javac -p %{_javadir}/modules -d ../classes
# Javadoc docs are too outdated to be even close to working
#javadoc -html4 -p %{_datadir}/modules org.apache.log4j org.apache.log4j.xml
cd ../classes
find . |xargs jar cf org.apache.log4j-%{version}.jar
jar i org.apache.log4j-%{version}.jar

%install
mkdir -p %{buildroot}%{_javadir}/modules %{buildroot}%{_mavenpomdir}
cp src/main/classes/org.apache.log4j-%{version}.jar %{buildroot}%{_javadir}/modules

ln -s modules/org.apache.log4j-%{version}.jar %{buildroot}%{_javadir}
ln -s modules/org.apache.log4j-%{version}.jar %{buildroot}%{_javadir}/log4j-%{version}.jar
ln -s modules/org.apache.log4j-%{version}.jar %{buildroot}%{_javadir}/log4j12-%{version}.jar

cp pom.xml %{buildroot}%{_mavenpomdir}/log4j-%{version}.pom
cp pom.xml %{buildroot}%{_mavenpomdir}/log4j12-%{version}.pom

%add_maven_depmap log4j-%{version}.pom org.apache.log4j-%{version}.jar
%add_maven_depmap log4j12-%{version}.pom org.apache.log4j-%{version}.jar

# DTD and the SGML catalog (XML catalog handled in scriptlets)
install -pD -T -m 644 src/main/javadoc/org/apache/log4j/xml/doc-files/log4j.dtd \
  %{buildroot}%{_datadir}/sgml/log4j/log4j.dtd
install -pD -T -m 644 %{SOURCE1} \
  %{buildroot}%{_datadir}/sgml/log4j/catalog

%post
# Note that we're using versioned catalog, so this is always ok.
if [ -x %{_bindir}/install-catalog -a -d %{_sysconfdir}/sgml ]; then
  %{_bindir}/install-catalog --add \
    %{_sysconfdir}/sgml/log4j-%{version}-%{release}.cat \
    %{_datadir}/sgml/log4j/catalog > /dev/null || :
fi
if [ -x %{_bindir}/xmlcatalog -a -w %{_sysconfdir}/xml/catalog ]; then
  %{_bindir}/xmlcatalog --noout --add public "-//APACHE//DTD LOG4J 1.2//EN" \
    file://%{_datadir}/sgml/log4j/log4j.dtd %{_sysconfdir}/xml/catalog \
    > /dev/null
  %{_bindir}/xmlcatalog --noout --add system log4j.dtd \
    file://%{_datadir}/sgml/log4j/log4j.dtd %{_sysconfdir}/xml/catalog \
    > /dev/null || :
fi

%preun
if [ $1 -eq 0 ]; then
  if [ -x %{_bindir}/xmlcatalog -a -w %{_sysconfdir}/xml/catalog ]; then
    %{_bindir}/xmlcatalog --noout --del \
      file://%{_datadir}/sgml/log4j/log4j.dtd \
      %{_sysconfdir}/xml/catalog > /dev/null || :
  fi
fi

%postun
# Note that we're using versioned catalog, so this is always ok.
if [ -x %{_bindir}/install-catalog -a -d %{_sysconfdir}/sgml ]; then
  %{_bindir}/install-catalog --remove \
    %{_sysconfdir}/sgml/log4j-%{version}-%{release}.cat \
    %{_datadir}/sgml/log4j/catalog > /dev/null || :
fi

%files -f .mfiles
%{_datadir}/sgml/log4j
%{_javadir}/*.jar
%{_javadir}/modules/*.jar
%doc LICENSE NOTICE

#files javadoc
