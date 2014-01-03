import os
import sys
import json
import fnmatch

import sublime
import sublime_plugin

debug = lambda *args: sys.stdout.write("\n%s" % " ".join(map(str, args)))

COVERAGE_DIR_NAME = 'coverage'
REGION_KEY = 'SublimeMochaJSCoverage'


def find_project_root(file_path):
    """
        Project Root is defined as the parent directory 
        that contains a directory called 'coverage'
    """
    if os.access(os.path.join(file_path, COVERAGE_DIR_NAME), os.R_OK):
        return file_path
    parent, current = os.path.split(file_path)
    if current:
        return find_project_root(parent)


def find_coverage_filename(coverage_dir):
    """
        Returns latest coverage json for specifed file or None if cannot find it
        in specifed coverage direcotry
    """
    files = []
    for root, dirnames, filenames in os.walk(coverage_dir):
    	for filename in fnmatch.filter(filenames, '*.json'):
      		files.append(os.path.join(root, filename))
    debug("discovered files: " + ",".join(files or []))
    getmtime = lambda key: os.path.getmtime(os.path.join(coverage_dir, key))
    coverage_file_name = None
    if files:
        files.sort(key=getmtime, reverse=True)
        coverage_file_name = files.pop(0)

    return coverage_file_name


def read_coverage_report(file_path):
    with open(file_path, 'r') as coverage_file:
        try:
            coverage_json = json.load(coverage_file)
            return coverage_json
        except IOError:
            return None


class ShowJsCoverageCommand(sublime_plugin.TextCommand):

    """
        Highlight uncovered lines in the current file
        based on a previous coverage run.
    """

    def run(self, edit):
        view = self.view
        # get name of currently opened file
        filename = view.file_name()
        if not filename:
            return
        project_root = find_project_root(filename)

        if not project_root:
            if view.window():
                sublime.status_message("Could not find coverage directory.")
            return

        relative_filename = filename.replace(project_root + "/", "")
        coverage_dir = os.path.join(project_root, COVERAGE_DIR_NAME)
        coverage_filename = find_coverage_filename(coverage_dir)

        debug("Display js coverage report for file", filename)
        debug("project_root", project_root)
        debug("relative_filename", relative_filename)
        debug("coverage_dir", coverage_dir)
        debug("coverage_filename", coverage_filename)

        if not coverage_filename:
            if view.window():
                return sublime.status_message(
                    "Can't find the coverage file in project root: " + str(project_root))
            return

        # Clean up
        view.erase_status("SublimeMochaJSCoverage")
        view.erase_regions("SublimeMochaJSCoverage")

        outlines = []

        report = read_coverage_report(
            os.path.join(coverage_dir, coverage_filename))
        if report is None:
            if view.window():
                sublime.status_message(
                    "Can't read coverage report from file: " + str(coverage_filename))
            return
        debug("Found report for the following number of files: " + str(len(report)))

        if not report:
            view.set_status("SublimeMochaJSCoverage", "UNCOVERED!")
            if view.window():
                sublime.status_message(
                    "Can't find the coverage json file in project root: " + project_root)

        for tested_file_name in report:
            tested_file_name2 = tested_file_name.replace("./", "")
            if tested_file_name2 != relative_filename:
                continue
            debug("Found test report for file " + str(relative_filename))
            file_report = report.get(tested_file_name)
            lines = file_report.get("l")
            for num in lines:
                runs = int(lines.get(num))
                num = int(num) - 1
                if runs == 0:
                    region = view.full_line(view.text_point(num, 0))
                    outlines.append(region)

        # update highlighted regions
        if outlines:
            view.add_regions(REGION_KEY, outlines,
                             'markup.deleted.diff', 'bookmark', sublime.DRAW_OUTLINED)


class ClearMochaJsCoverageCommand(sublime_plugin.TextCommand):

    """
        Remove highlights created by plugin.
    """

    def run(self, edit):
        view = self.view
        view.erase_regions(REGION_KEY)
