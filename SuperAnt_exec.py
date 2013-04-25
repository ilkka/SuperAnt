import sublime, sublime_plugin, sys, os, re
from xml.dom.minidom import parseString
from subprocess import Popen, PIPE

DEFAULT_BUILD_CMD = "exec"
DEFAULT_BUILD_TASK = "build"


class SuperAntExecCommand(sublime_plugin.WindowCommand):
    def run(self, **kwargs):
        package_dir = os.path.join(sublime.packages_path(), "Super Ant");
        
        self.working_dir = kwargs['working_dir'];
        self.build = None;

        s = sublime.load_settings("SuperAnt.sublime-settings");
        build_file = s.get("build_file", "build.xml");
        use_sorting = s.get("use_sorting", "true") == "true";

        # buildfile by selection: search build file in project folder that file from active view is in  
        try:
            active_file = self.window.active_view().file_name();
            active_folder = os.path.dirname(active_file);
            if os.path.exists(active_folder + os.sep + build_file):
                self.build = active_folder + os.sep + build_file;
                self.working_dir = active_folder
            else:
                raise Exception('not a build file');
        except Exception as ex:
            print 'No build file in base folder of currently viewed file';

        # buildfile by default: build.xml found in first project folder
        if self.build == None and os.path.exists(self.working_dir + os.sep + build_file):
            self.build = self.working_dir + os.sep + build_file;

        try:
            f = open(self.build);
        except Exception as ex:
            print ex;
            self.window.open_file(os.path.join(package_dir, 'SuperAnt.sublime-settings'));
            return 'The file could not be opened';

        self.working_dir = os.path.dirname(self.build);

        data = f.read();
        dom = parseString(data);

        # get project name for target prefixing in quick panel
        project_name = None;
        try:
            project_name = dom.firstChild.getAttributeNode('name').nodeValue;
        except Exception, e:
            # default to folder name if name attribute is not given in project tag
            project_name = os.path.basename(self.working_dir);

        output = Popen(self._ant() + " -p", stdout=PIPE, shell=True, cwd=self.working_dir).stdout.read()
        list_prefix = project_name + ': ';
        self.targetsList = [list_prefix + re.sub(r'^\s(\S+)\s.*', r'\1', l) for l in output.split('\n') if l.startswith(' ') and not l.startswith(' _')];

        if use_sorting:
            self.targetsList = sorted(self.targetsList);

        def cleanName(n):
            return n.replace(list_prefix, "");
        
        self.targetLookup = map(cleanName, self.targetsList)

        self.window.show_quick_panel(self.targetsList, self._quick_panel_callback);

    def _ant(self):
        # Check for Windows Overrides and Merge
        if sys.platform.startswith('win32'):
            return "ant.bat"
        return "ant"

    def _quick_panel_callback(self, index):

        if (index > -1):
            targetName = self.targetLookup[index];
            
            cmd = {
                'cmd': [self._ant(), "-f", self.build, targetName],
                'working_dir': self.working_dir
            }

            # run build
            self.window.run_command("exec", cmd);
