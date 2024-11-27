# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.

# No build, no debuginfo
%define debug_package %{nil}

# Disable brp-java-repack-jars, so jars will not be decompressed and repackaged
%define __jar_repack 0

# Generate digests, 8 means algorithm of sha256
# This is different from rpm sig algorithm
# Requires rpm version 4.12 + to generate but b/c run on older versions
%define _source_filedigest_algorithm 8
%define _binary_filedigest_algorithm 8

# Fixed in Fedora:
# https://www.endpointdev.com/blog/2011/10/rpm-building-fedoras-sharedstatedir/
%define _sharedstatedir /var/lib

# User Define Variables
%define product_dir %{_datadir}/%{name}
%define config_dir %{_sysconfdir}/%{name}
%define data_dir %{_sharedstatedir}/%{name}
%define log_dir %{_localstatedir}/log/%{name}
%define pid_dir %{_localstatedir}/run/%{name}
%define tmp_dir %{log_dir}/tmp
%{!?_version: %define _version 0.0.0 }
%{!?_architecture: %define _architecture x86_64 }

Name: wazuh-indexer
Version: %{_version}
Release: %{_release}
License: Apache-2.0
Summary: An open source distributed and RESTful search engine
URL: https://www.wazuh.com/
Vendor:      Wazuh, Inc <info@wazuh.com>
Packager:    Wazuh, Inc <info@wazuh.com>
Group: Application/Internet
ExclusiveArch: %{_architecture}
AutoReqProv: no

%description
Wazuh indexer is a near real-time full-text search and analytics engine that
gathers security-related data into one platform. This Wazuh central component
indexes and stores alerts generated by the Wazuh server. Wazuh indexer can be
configured as a single-node or multi-node cluster, providing scalability and
high availability.
For more information, see: https://www.wazuh.com/

%prep
# No-op. We are using dir so no need to setup.

%build

%define observability_plugin %( if [ -f %{_topdir}/etc/wazuh-indexer/opensearch-observability/observability.yml ]; then echo "1" ; else echo "0"; fi )
%define reportsscheduler_plugin %( if [ -f %{_topdir}/etc/wazuh-indexer/wazuh-indexer-reports-scheduler/reports-scheduler.yml ]; then echo "1" ; else echo "0"; fi )

%install
set -e
cd %{_topdir} && pwd

# Create necessary directories
mkdir -p %{buildroot}%{pid_dir}
mkdir -p %{buildroot}%{product_dir}/plugins
mkdir -p %{buildroot}%{tmp_dir}

# Install directories/files
cp -a etc usr var %{buildroot}
chmod 0755 %{buildroot}%{product_dir}/bin/*
if [ -d %{buildroot}%{product_dir}/plugins/opensearch-security ]; then
    chmod 0755 %{buildroot}%{product_dir}/plugins/opensearch-security/tools/*
fi

# Pre-populate the folders to ensure rpm build success even without all plugins
mkdir -p %{buildroot}%{config_dir}/opensearch-observability
mkdir -p %{buildroot}%{config_dir}/wazuh-indexer-reports-scheduler
mkdir -p %{buildroot}%{product_dir}/performance-analyzer-rca

# Pre-populate PA configs if not present
if [ ! -f %{buildroot}%{data_dir}/rca_enabled.conf ]; then
    echo 'true' > %{buildroot}%{data_dir}/rca_enabled.conf
fi
if [ ! -f %{buildroot}%{data_dir}/performance_analyzer_enabled.conf ]; then
    echo 'true' > %{buildroot}%{data_dir}/performance_analyzer_enabled.conf
fi

# Build a filelist to be included in the %files section
echo '%defattr(640, %{name}, %{name}, 750)' > filelist.txt
find %{buildroot} -type d >> filelist.txt
sed -i 's|%{buildroot}|%%dir |' filelist.txt
find %{buildroot} -type f >> filelist.txt
sed -i 's|%{buildroot}||' filelist.txt

# The %install section gets executed under a dash shell,
# which doesn't have array structures.
# Below, we are building a list of directories
# which will later be excluded from filelist.txt
set -- "%%dir %{_sysconfdir}"
set -- "$@" "%%dir %{_sysconfdir}/sysconfig"
set -- "$@" "%%dir %{_sysconfdir}/init.d"
set -- "$@" "%%dir /usr"
set -- "$@" "%%dir /usr/lib"
set -- "$@" "%%dir /usr/lib/systemd/system"
set -- "$@" "%%dir /usr/lib/tmpfiles.d"
set -- "$@" "%%dir /usr/share"
set -- "$@" "%%dir /var"
set -- "$@" "%%dir /var/run"
set -- "$@" "%%dir /var/run/%{name}"
set -- "$@" "%%dir /run"
set -- "$@" "%%dir /var/lib"
set -- "$@" "%%dir /var/log"
set -- "$@" "%%dir /usr/lib/sysctl.d"
set -- "$@" "%%dir /usr/lib/systemd"
set -- "$@" "%{_sysconfdir}/sysconfig/%{name}"
set -- "$@" "%{config_dir}/log4j2.properties"
set -- "$@" "%{config_dir}/jvm.options"
set -- "$@" "%{config_dir}/opensearch.yml"
set -- "$@" "%{product_dir}/VERSION"
set -- "$@" "%{product_dir}/plugins/opensearch-security/tools/.*\.sh"
set -- "$@" "%{product_dir}/bin/.*"
set -- "$@" "%{product_dir}/jdk/bin/.*"
set -- "$@" "%{product_dir}/jdk/lib/jspawnhelper"
set -- "$@" "%{product_dir}/jdk/lib/modules"
set -- "$@" "%{product_dir}/performance-analyzer-rca/bin/.*"
set -- "$@" "%{product_dir}/NOTICE.txt"
set -- "$@" "%{product_dir}/README.md"
set -- "$@" "%{product_dir}/LICENSE.txt"
set -- "$@" "%{_prefix}/lib/systemd/system/%{name}.service"
set -- "$@" "%{_prefix}/lib/systemd/system/%{name}-performance-analyzer.service"
set -- "$@" "%{_sysconfdir}/init.d/%{name}"
set -- "$@" "%{_sysconfdir}/sysconfig/%{name}"
set -- "$@" "%{_prefix}/lib/sysctl.d/%{name}.conf"
set -- "$@" "%{_prefix}/lib/tmpfiles.d/%{name}.conf"
set -- "$@" "%%dir %{product_dir}/bin/opensearch-performance-analyzer"

# Check if we are including the observability and reports scheduler
# plugins
if [ %observability_plugin -eq 1 ]; then
    set -- "$@" "%{config_dir}/opensearch-observability/observability.yml"
fi

if [ %reportsscheduler_plugin -eq 1 ]; then
    set -- "$@" "%{config_dir}/wazuh-indexer-reports-scheduler/reports-scheduler.yml"
fi

for i in "$@"
do
	sed -ri "\|^$i$|d" filelist.txt
done

# Change Permissions
chmod -Rf a+rX,u+w,g-w,o-w %{buildroot}/*
exit 0

%pre
set -e
# Stop existing service
if command -v systemctl >/dev/null && systemctl is-active %{name}.service >/dev/null; then
    echo "Stop existing %{name}.service"
    systemctl --no-reload stop %{name}.service
    touch %{tmp_dir}/wazuh-indexer.restart
fi
if command -v systemctl >/dev/null && systemctl is-active %{name}-performance-analyzer.service >/dev/null; then
    echo "Stop existing %{name}-performance-analyzer.service"
    systemctl --no-reload stop %{name}-performance-analyzer.service
fi
# Create user and group if they do not already exist.
getent group %{name} > /dev/null 2>&1 || groupadd -r %{name}
getent passwd %{name} > /dev/null 2>&1 || \
    useradd -r -g %{name} -M -s /sbin/nologin \
        -c "%{name} user/group" %{name}
exit 0

%post
set -e
chown -R %{name}:%{name} %{config_dir}
chown -R %{name}:%{name} %{log_dir}

export OPENSEARCH_PATH_CONF=${OPENSEARCH_PATH_CONF:-%{config_dir}}
# Apply Performance Analyzer settings, as per https://github.com/opensearch-project/opensearch-build/blob/2.18.0/scripts/pkg/build_templates/current/opensearch/deb/debian/postinst#L28-L37
if ! grep -q '## OpenSearch Performance Analyzer' "$OPENSEARCH_PATH_CONF/jvm.options"; then
    CLK_TCK=$(/usr/bin/getconf CLK_TCK)
    {
        echo
        echo "## OpenSearch Performance Analyzer"
        echo "-Dclk.tck=$CLK_TCK"
        echo "-Djdk.attach.allowAttachSelf=true"
        echo "-Djava.security.policy=file://$OPENSEARCH_PATH_CONF/opensearch-performance-analyzer/opensearch_security.policy"
        echo "--add-opens=jdk.attach/sun.tools.attach=ALL-UNNAMED"
    } >> "$OPENSEARCH_PATH_CONF/jvm.options"
fi

# Reload systemctl daemon
if command -v systemctl > /dev/null; then
    systemctl daemon-reload
fi
# Reload other configs
if command -v systemctl > /dev/null; then
    systemctl restart systemd-sysctl.service || true
fi

if command -v systemd-tmpfiles > /dev/null; then
    systemd-tmpfiles --create %{name}.conf
fi

if ! [ -d %{config_dir}/certs ] && [ -f %{product_dir}/plugins/opensearch-security/tools/install-demo-certificates.sh ]; then
    echo "No certificates detected in %{config_dir}, installing demo certificates..."
    echo "### If you are using a custom certificates path, ignore this message."
    bash %{product_dir}/plugins/opensearch-security/tools/install-demo-certificates.sh > %{log_dir}/install_demo_certificates.log 2>&1
fi

if [ -f %{tmp_dir}/wazuh-indexer.restart ]; then
    rm -f %{tmp_dir}/wazuh-indexer.restart
    if command -v systemctl > /dev/null; then
        echo "Restarting wazuh-indexer service..."
        systemctl restart wazuh-indexer.service > /dev/null 2>&1
        exit 0
    fi
fi

# Messages
echo "### NOT starting on installation, please execute the following statements to configure wazuh-indexer service to start automatically using systemd"
echo " sudo systemctl daemon-reload"
echo " sudo systemctl enable wazuh-indexer.service"
echo "### You can start wazuh-indexer service by executing"
echo " sudo systemctl start wazuh-indexer.service"
exit 0

%preun
set -e
if command -v systemctl >/dev/null && systemctl is-active %{name}.service >/dev/null; then
    echo "Stop existing %{name}.service"
    systemctl --no-reload stop %{name}.service
fi
if command -v systemctl >/dev/null && systemctl is-active %{name}-performance-analyzer.service >/dev/null; then
    echo "Stop existing %{name}-performance-analyzer.service"
    systemctl --no-reload stop %{name}-performance-analyzer.service
fi
exit 0

%files -f %{_topdir}/filelist.txt
%defattr(640, %{name}, %{name}, 750)

%doc %{product_dir}/NOTICE.txt
%doc %{product_dir}/README.md
%license %{product_dir}/LICENSE.txt

# Service files
%attr(0644, root, root) %{_prefix}/lib/systemd/system/%{name}.service
%attr(0644, root, root) %{_prefix}/lib/systemd/system/%{name}-performance-analyzer.service
%attr(0750, root, root) %{_sysconfdir}/init.d/%{name}
%attr(0644, root, root) %config(noreplace) %{_prefix}/lib/sysctl.d/%{name}.conf
%attr(0644, root, root) %config(noreplace) %{_prefix}/lib/tmpfiles.d/%{name}.conf


# Configuration files
%config(noreplace) %attr(0660, root, %{name}) "%{_sysconfdir}/sysconfig/%{name}"
%config(noreplace) %attr(660, %{name}, %{name}) %{config_dir}/log4j2.properties
%config(noreplace) %attr(660, %{name}, %{name}) %{config_dir}/jvm.options
%config(noreplace) %attr(660, %{name}, %{name}) %{config_dir}/opensearch.yml
%config(noreplace) %attr(640, %{name}, %{name}) %{config_dir}/opensearch-security/*


%if %observability_plugin
%config(noreplace) %attr(660, %{name}, %{name}) %{config_dir}/opensearch-observability/observability.yml
%endif

%if %reportsscheduler_plugin
%config(noreplace) %attr(660, %{name}, %{name}) %{config_dir}/wazuh-indexer-reports-scheduler/reports-scheduler.yml
%endif


# Files that need other permissions
%attr(440, %{name}, %{name}) %{product_dir}/VERSION
%attr(740, %{name}, %{name}) %{product_dir}/plugins/opensearch-security/tools/*.sh
%attr(750, %{name}, %{name}) %{product_dir}/bin/*
%attr(750, %{name}, %{name}) %{product_dir}/jdk/bin/*
%attr(750, %{name}, %{name}) %{product_dir}/jdk/lib/jspawnhelper
%attr(750, %{name}, %{name}) %{product_dir}/jdk/lib/modules
%attr(750, %{name}, %{name}) %{product_dir}/performance-analyzer-rca/bin/*

%changelog
* Mon Jun 23 2025 support <info@wazuh.com> - 5.0.0
- More info: https://documentation.wazuh.com/current/release-notes/release-5.0.0-0.html
* Tue Feb 20 2025 support <info@wazuh.com> - 4.10.2
- More info: https://documentation.wazuh.com/current/release-notes/release-4-10-2.html
* Tue Jan 28 2025 support <info@wazuh.com> - 4.10.1
- More info: https://documentation.wazuh.com/current/release-notes/release-4-10-1.html
* Thu Nov 28 2024 support <info@wazuh.com> - 4.10.0
- More info: https://documentation.wazuh.com/current/release-notes/release-4-10-0.html
* Mon Nov 04 2024 support <info@wazuh.com> - 4.9.2
- More info: https://documentation.wazuh.com/current/release-notes/release-4-9-2.html
* Tue Oct 15 2024 support <info@wazuh.com> - 4.9.1
- More info: https://documentation.wazuh.com/current/release-notes/release-4-9-1.html
* Thu Aug 15 2024 support <info@wazuh.com> - 4.9.0
- More info: https://documentation.wazuh.com/current/release-notes/release-4-9-0.html
* Tue Jan 30 2024 support <info@wazuh.com> - 4.8.1
- More info: https://documentation.wazuh.com/current/release-notes/release-4-8-1.html
* Fri Dec 15 2023 support <info@wazuh.com> - 4.8.0
- More info: https://documentation.wazuh.com/current/release-notes/release-4-8-0.html
* Tue Dec 05 2023 support <info@wazuh.com> - 4.7.1
- More info: https://documentation.wazuh.com/current/release-notes/release-4-7-1.html
* Tue Nov 21 2023 support <info@wazuh.com> - 4.7.0
- More info: https://documentation.wazuh.com/current/release-notes/release-4-7-0.html
* Tue Oct 31 2023 support <info@wazuh.com> - 4.6.0
- More info: https://documentation.wazuh.com/current/release-notes/release-4-6-0.html
* Tue Oct 24 2023 support <info@wazuh.com> - 4.5.4
- More info: https://documentation.wazuh.com/current/release-notes/release-4-5-4.html
* Tue Oct 10 2023 support <info@wazuh.com> - 4.5.3
- More info: https://documentation.wazuh.com/current/release-notes/release-4-5-3.html
* Thu Aug 31 2023 support <info@wazuh.com> - 4.5.2
- More info: https://documentation.wazuh.com/current/release-notes/release-4-5-2.html
* Thu Aug 24 2023 support <info@wazuh.com> - 4.5.1
- More info: https://documentation.wazuh.com/current/release-notes/release-4-5.1.html
* Thu Aug 10 2023 support <info@wazuh.com> - 4.5.0
- More info: https://documentation.wazuh.com/current/release-notes/release-4-5-0.html
* Mon Jul 10 2023 support <info@wazuh.com> - 4.4.5
- More info: https://documentation.wazuh.com/current/release-notes/release-4-4-5.html
* Tue Jun 13 2023 support <info@wazuh.com> - 4.4.4
- More info: https://documentation.wazuh.com/current/release-notes/release-4-4-4.html
* Thu May 25 2023 support <info@wazuh.com> - 4.4.3
- More info: https://documentation.wazuh.com/current/release-notes/release-4-4-3.html
* Mon May 08 2023 support <info@wazuh.com> - 4.4.2
- More info: https://documentation.wazuh.com/current/release-notes/release-4-4-2.html
* Mon Apr 17 2023 support <info@wazuh.com> - 4.4.1
- More info: https://documentation.wazuh.com/current/release-notes/release-4-4-1.html
* Wed Jan 18 2023 support <info@wazuh.com> - 4.4.0
- More info: https://documentation.wazuh.com/current/release-notes/release-4-4-0.html
* Thu Nov 10 2022 support <info@wazuh.com> - 4.3.10
- More info: https://documentation.wazuh.com/current/release-notes/release-4-3-10.html
* Mon Oct 03 2022 support <info@wazuh.com> - 4.3.9
- More info: https://documentation.wazuh.com/current/release-notes/release-4-3-9.html
* Mon Sep 19 2022 support <info@wazuh.com> - 4.3.8
- More info: https://documentation.wazuh.com/current/release-notes/release-4-3-8.html
* Mon Aug 08 2022 support <info@wazuh.com> - 4.3.7
- More info: https://documentation.wazuh.com/current/release-notes/release-4-3-7.html
* Thu Jul 07 2022 support <info@wazuh.com> - 4.3.6
- More info: https://documentation.wazuh.com/current/release-notes/release-4-3-6.html
* Wed Jun 29 2022 support <info@wazuh.com> - 4.3.5
- More info: https://documentation.wazuh.com/current/release-notes/release-4-3-5.html
* Tue Jun 07 2022 support <info@wazuh.com> - 4.3.4
- More info: https://documentation.wazuh.com/current/release-notes/release-4-3-4.html
* Tue May 31 2022 support <info@wazuh.com> - 4.3.3
- More info: https://documentation.wazuh.com/current/release-notes/release-4-3-3.html
* Mon May 30 2022 support <info@wazuh.com> - 4.3.2
- More info: https://documentation.wazuh.com/current/release-notes/release-4-3-2.html
* Wed May 18 2022 support <info@wazuh.com> - 4.3.1
- More info: https://documentation.wazuh.com/current/release-notes/release-4-3-1.html
* Thu May 05 2022 support <info@wazuh.com> - 4.3.0
- More info: https://documentation.wazuh.com/current/release-notes/release-4-3-0.html
- Initial package
