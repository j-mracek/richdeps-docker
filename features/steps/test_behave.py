#!/usr/bin/python -tt

from behave import *
import os, sys, subprocess, glob

DNF_FLAGS = ['-y', '--disablerepo=*', '--nogpgcheck']
RPM_INSTALL_FLAGS = ['-Uvh']
RPM_ERASE_FLAGS = ['-e']

def _left_decorator(item):
  " Removed packages "
  return u'-' + item

def _right_decorator(item):
  " Installed packages "
  return u'+' + item

def find_pkg(pkg):
  " Find the package file in the repository "
  candidates = glob.glob('/repo/'+pkg+'*.rpm')
  if len(candidates) == 0:
    print("No candidates for: '{0}'".format(pkg))
  assert len(candidates) == 1
  return candidates[0]

def decorate_rpm_packages(pkgs):
  " Converts package names like TestA, TestB into absolute paths "
  return [find_pkg(p) for p in pkgs]

def get_package_list():
  " Gets all installed packages in the system "
  pkgstr = subprocess.check_output(['rpm', '-qa', '--queryformat', '%{NAME}\n'])
  return pkgstr.splitlines()

def diff_package_lists(a, b):
  " Computes both left/right diff between lists `a` and `b` "
  sa, sb = set(a), set(b)
  return (map(_left_decorator, list(sa - sb)),
      map(_right_decorator, list(sb - sa)))

def execute_dnf_command(cmd, reponame):
  " Execute DNF command with default flags and the specified `reponame` enabled "
  flags = DNF_FLAGS + ['--enablerepo={0}'.format(reponame)]
  return subprocess.call(['dnf'] + flags + cmd, stdout=subprocess.PIPE)

def execute_rpm_command(pkg, action):
  " Execute given action over specified pkg(s) "
  if not isinstance(pkg, list):
    pkg = [pkg]
  if action == "remove":
    action = RPM_ERASE_FLAGS
  elif action == "install":
    action = RPM_INSTALL_FLAGS
    pkg = decorate_rpm_packages(pkg)
  return subprocess.call(['rpm'] + action + pkg, stdout=subprocess.PIPE)

def piecewise_compare(a, b):
  " Check if the two sequences are identical regardless of ordering "
  return sorted(a) == sorted(b)

def split(pkg):
  return [p.strip() for p in pkg.split(',')]

@given('I use the repository "{repo}"')
def given_repo_condition(context, repo):
  " :type context: behave.runner.Context "
  assert repo
  assert os.path.exists('/build/' + repo)
  a = [os.remove(p) for p in os.listdir('/repo')]
  subprocess.check_call(['cp -rs /build/' + repo + '/* /repo/'], shell=True)

@when('I "{action}" a package "{pkg}" with "{manager}"')
def when_action_package(context, action, pkg, manager):
  assert action in ["install", "remove"]
  assert manager in ["rpm", "dnf", "pkcon"]
  assert pkg
  context.pre_packages = get_package_list()
  assert context.pre_packages

  if manager == 'rpm':
    context.rc = execute_rpm_command(split(pkg), action)
  elif manager == 'dnf':
    context.rc = execute_dnf_command([action] + split(pkg), 'test')

def _handle_rc(context, rc, negate):
  if negate:
    return rc != context.rc
  return rc == context.rc

@then('the return code should be "{rc}"')
def then_rc_is(context, rc):
  assert _handle_rc(context, rc, False)

@then('the return code should not be "{rc}"')
def then_rc_is_not(context, rc):
  assert _handle_rc(context, rc, True)

@then('package "{pkg}" should be "{state}"')
def then_package_state(context, pkg, state):
  assert state in ["installed", "removed", "absent"]
  assert pkg
  assert context.rc == 0
  pkgs = get_package_list()
  assert pkgs
  removed, installed = diff_package_lists(context.pre_packages, pkgs)
  assert removed != None and installed != None
  
  for n in split(pkg):
    c = True
    if state == 'installed':
      c = ('+' + n) in installed
      installed.remove('+' + n)
    if state == 'removed':
      c = ('-' + n) in removed
      removed.remove('-' + n)
    if state == 'absent':
      c = ('+' + n) not in installed
      if c:
        c = ('-' + n) not in removed
    if not c:
      raise Exception("Error '{0}' NOT '{1}'".format(n, state))

  ''' This checks that installations/removals are always fully specified,
  so that we always cover the requirements/expecations entirely '''
  if state != 'absent':
    if installed:
      raise Exception("Error '{0}' NOT IN installed".format(', '.join(installed)))
    if removed:
      raise Exception("Error '{0}' NOT IN removed".format(', '.join(removed)))
