%define archiversion %(echo %{version} | tr . _ )

Name:		log4j12
Version:	1.2.17
Release:	9
Summary:	Java logging package
Group:		Development/Java
License:	ASL 2.0
URL:		https://logging.apache.org/log4j/1.2/
Source0:	https://github.com/apache/log4j/archive/v%{archiversion}.tar.gz
Source1:	log4j.catalog
# Chainsaw's LogFactor5 config moves from ~/lf5 to ~/.logfactor5.
Patch0:		0001-logfactor5-changed-userdir.patch

BuildRequires:	java-current-devel
BuildRequires:	sysjar
BuildRequires:	jmod(java.mail)
BuildRequires:	jmod(java.jms)
BuildRequires:	jmod(java.activation)

BuildArch:	noarch

%description
Log4j 1.2 sends log statements to files, the console, syslog, JDBC,
JavaMail and JMS. This is the log4j:log4j 1.2.17 jar. It is not the
Log4j 2 bridge.

%prep
%autosetup -n log4j-%{archiversion} -p1
find . -name '*.jar' -delete
find . -name '*.class' -delete
find . -name '*.dll' -delete
rm -rf docs/api
# Windows-only appender. The published jar does not ship it.
rm -f src/main/java/org/apache/log4j/nt/NTEventLogAppender.java \
	tests/src/java/org/apache/log4j/nt/NTEventLogAppenderTest.java
cat > src/main/java/module-info.java <<'EOF'
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
# No -u: rpm's script trailer reads DONT_CLEANUP, which is unset.
set -eo pipefail
export JAVA_HOME=%{_jvmdir}/java-openjdk
export PATH=$JAVA_HOME/bin:$PATH

rm -rf modpath classes
mkdir -p modpath classes
# Named modules keep the name from module-info. java.activation is
# automatic, so the symlink has to carry that name: the installed
# file is javax.activation.jar.
ln -s /usr/share/java/javax.activation.jar modpath/java.activation.jar
ln -s /usr/share/java/java.mail.jar modpath/java.mail.jar
ln -s /usr/share/java/javax.jms-api.jar modpath/javax.jms-api.jar

cd src/main/java
# The 1.2 sources are ISO-8859-1. UTF-8 rejects bytes in the comments.
mapfile -t sources < <(find . -name '*.java')
javac --release 11 -encoding ISO-8859-1 -d "$OLDPWD/classes" -p "$OLDPWD/modpath" "${sources[@]}"
cd "$OLDPWD"
cp -a src/main/resources/. classes/
jar --create --file log4j-%{version}.jar -C classes .

cat > log4j-%{version}.pom <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>log4j</groupId>
  <artifactId>log4j</artifactId>
  <version>%{version}</version>
  <name>log4j</name>
  <description>Log4j %{version}, built from source.</description>
  <url>https://logging.apache.org/log4j/1.2/</url>
  <licenses>
    <license>
      <name>Apache License, Version 2.0</name>
      <url>https://www.apache.org/licenses/LICENSE-2.0.txt</url>
    </license>
  </licenses>
</project>
EOF

%check
set -eo pipefail
export JAVA_HOME=%{_jvmdir}/java-openjdk
export PATH=$JAVA_HOME/bin:$PATH
jar --describe-module -f log4j-%{version}.jar > module.txt
grep -q '^org.apache.log4j.v12 ' module.txt
jar tf log4j-%{version}.jar > jar.txt
grep -q 'org/apache/log4j/net/SMTPAppender.class' jar.txt
grep -q 'org/apache/log4j/xml/log4j.dtd' jar.txt
grep -q 'org/apache/log4j/lf5/config/defaultconfig.properties' jar.txt
if grep -q NTEventLogAppender jar.txt; then
	echo "Windows appender leaked into the jar"
	exit 1
fi
mkdir -p check
cat > check/Check.java <<'EOF'
public class Check {
	public static void main(String[] args) {
		org.apache.log4j.BasicConfigurator.configure();
		org.apache.log4j.Logger log = org.apache.log4j.Logger.getLogger("check");
		log.info("log4j_ok");
		new org.apache.log4j.net.SMTPAppender();
		System.out.println("log4j_ok");
	}
}
EOF
CP="log4j-%{version}.jar:/usr/share/java/java.mail.jar:/usr/share/java/javax.activation.jar:/usr/share/java/javax.jms-api.jar"
javac --release 11 -encoding UTF-8 -cp "$CP" -d check check/Check.java
java -cp "check:$CP" Check > check.txt
grep -q '^log4j_ok$' check.txt

%install
# No -u: rpm's script trailer reads DONT_CLEANUP, which is unset.
set -eo pipefail
sysjar install --buildroot %{buildroot} \
	--artifact log4j-%{version}.pom:log4j-%{version}.jar \
	--file-name log4j-%{version} \
	--link log4j \
	--link log4j12-%{version} \
	--link org.apache.log4j-%{version} \
	--filelist .mfiles
mkdir -p %{buildroot}%{_javadir}/modules
ln -s "../log4j-%{version}.jar" "%{buildroot}%{_javadir}/modules/org.apache.log4j-%{version}.jar"
echo "%{_javadir}/modules/org.apache.log4j-%{version}.jar" >> .mfiles
echo "%%dir %{_javadir}/modules" >> .mfiles
install -pD -m 644 src/main/javadoc/org/apache/log4j/xml/doc-files/log4j.dtd \
	%{buildroot}%{_datadir}/sgml/log4j/log4j.dtd
install -pD -m 644 %{SOURCE1} \
	%{buildroot}%{_datadir}/sgml/log4j/catalog

%post
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
if [ -x %{_bindir}/install-catalog -a -d %{_sysconfdir}/sgml ]; then
	%{_bindir}/install-catalog --remove \
		%{_sysconfdir}/sgml/log4j-%{version}-%{release}.cat \
		%{_datadir}/sgml/log4j/catalog > /dev/null || :
fi

%files -f .mfiles
%{_datadir}/sgml/log4j
%doc LICENSE NOTICE
