#!/usr/bin/python -tt

import subprocess
from sys import argv
import dnf


class DnfUpgrageTo():
    def create_repo(self):
        with open('/etc/yum.repos.d/dnf-pull-requests.repo', 'w') as f:
            f.write('[dnf-pull-requests]\nname=dnf-pull-requests\nbaseurl=https://copr-be.cloud.fedoraproject.org'
                    '/results/rpmsoftwaremanagement/dnf-pull-requests/fedora-rawhide-x86_64/\nenabled=1\ngpgcheck=0')

    def dnf_version(self):
        with dnf.Base() as base:
            base.read_all_repos()
            base.fill_sack()
            query = base.sack.query().filter(nevra__glob='dnf-' + argv[1] + '*').filter(arch__neq="src")
            assert len(query) == 1
            return str(query[0])

    def upgrade_nightly(self):
        with open('/etc/yum.repos.d/dnf-nightly.repo', 'w') as f:
            f.write('[dnf-nightly]\nname=dnf-nightly\nbaseurl=https://copr-be.cloud.fedoraproject.org/results/'
                    'rpmsoftwaremanagement/dnf-nightly/fedora-rawhide-x86_64/\nenabled=1\ngpgcheck=0')
        return subprocess.check_call(['dnf', 'upgrade', '-y', '--disablerepo=*', '--enablerepo=dnf-nightly'])

    def upgrade(self, pkg):
        return subprocess.check_call(['dnf', 'upgrade-to', '-y', '--disablerepo=*',
                                      '--enablerepo=dnf-pull-requests', pkg])

installer = DnfUpgrageTo()
installer.upgrade_nightly()
installer.create_repo()
installer.upgrade(installer.dnf_version())
