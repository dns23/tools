import json
import argparse
import os
import Queue
import threading
import subprocess
import re

def GetImmediateSubdirectories(path):
    return [name for name in os.listdir(path)
            if os.path.isdir(os.path.join(path, name)) and name[0] != "."]

def GetRawPMCCabeResults(path, timeout):
    q = Queue.Queue()
    process = None

    def target():
        file_exts = [".c", ".h", ".cpp", ".hpp", ".cc"]
        for file_ext in file_exts:
            process = subprocess.Popen("pmccabe *{0}".format(file_ext), shell=True,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            q.put(stdout, 0.1)

    os.chdir(path)
    thread = threading.Thread(target=target)
    thread.start()
    thread.join(timeout)

    if thread.is_alive():
        process.terminate()
        thread.join()

    os.chdir(os.path.dirname(os.path.realpath(__file__)))

    stdout = ""
    while not q.empty():
        stdout += q.get(0.1)
    return stdout

def PopulateFilesData(path):
    raw_data = GetRawPMCCabeResults(path, 1)

    regex = re.compile("(\d+)\s*(\d+)\s*(\d+)\s*(\d+)\s*(\d+)\s*([A-Z,a-z,\_,.,/]*.[c|h])\s*\(\d+\):\s*([A-Z,a-z,\_]*)")
    matches = regex.findall(raw_data)
    files = dict()

    for match in matches:
        file_name = match[5]
        func_name = match[6]

        if not file_name in files:
            files[file_name] = dict()

        if not func_name in files[file_name]:
            files[file_name][func_name] = dict()

        files[file_name][func_name]["mod_cyc_comp"] = int(match[0])
        files[file_name][func_name]["trad_cyc_comp"] = int(match[1])
        files[file_name][func_name]["statements_in_func"] = int(match[2])
        files[file_name][func_name]["first_line_in_func"] = int(match[3])
        files[file_name][func_name]["lines_in_func"] = int(match[4])

    return files

def PopulateFolderData(path, max_depth=0, ignore_max_depth=False):
    data = dict()
    data["folder_name"] = os.path.basename(os.path.normpath(path))
    data["sub_folders"] = []
    data["files"] = PopulateFilesData(path)

    if (max_depth > 0 or ignore_max_depth):
        sub_folders = GetImmediateSubdirectories(path)
        for sub_folder in sub_folders:
            data["sub_folders"].append(PopulateFolderData("{0}{1}/".format(path, sub_folder), max_depth - 1, ignore_max_depth))

    return data

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("root_folder", 
                        help="""Absolute path to root folder of your C/C++ project.""", nargs=1)
    parser.add_argument("-d", "--folder_depth",
                        help="""How deep you want to gather data for you C/C++ project. By default it walks the complete directory tree.""", type=int, nargs='?')
    parser.add_argument("-p", "--pretty_json", 
                        help="""Display the JSON data with indents.""", action="store_true")
    args = parser.parse_args()

    json_indent = None
    if args.pretty_json:
        json_indent = 3

    if args.folder_depth != None:
        print json.dumps(PopulateFolderData(args.root_folder[0], max_depth=args.folder_depth), sort_keys=True,
                         indent=json_indent, separators=(',', ': '))
    else:
        print json.dumps(PopulateFolderData(args.root_folder[0], ignore_max_depth=True), sort_keys=True,
                         indent=json_indent, separators=(',', ': '))
