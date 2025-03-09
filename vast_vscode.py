# create the sftp.json file for the vscode-sftp extension
# listing all the running instances in vast
# as well adding terminal profiles for connecting to those instances
# modified .vscode/settings.json (overwrite field terminal.integrated.profiles.linux) and .vscode/sftp.json (field profile)

# it should only affect entri with prefix 'v_'

# also do a few things like installing pixi (loading a custom docker image is slow)

# example of a sftp.template.json file
# {
#     "uploadOnSave": true,
#     "ignore": [
#         ".vscode",
#         ".git",
#         ".DS_Store",
#         ".pixi",
#         ".env"
#     ],
#     "agent": "$SSH_AUTH_SOCK"
# }
import subprocess

from vastai_sdk import VastAI
import argparse
import os
import json
import shlex


def get_ssh_port_ipaddr(raw_info, use_proxy=False):
    # copied from vast cli
    # why would they create a
    # file instead of just return it!

    ports = raw_info.get("ports", {})
    port_22d = ports.get("22/tcp", None)
    port = -1

    try:
        if port_22d is not None and not use_proxy:
            # direct ssh
            ipaddr = raw_info["public_ipaddr"]
            port = int(port_22d[0]["HostPort"])

        else:
            # proxy
            assert use_proxy, "only proxy port is available"

            ipaddr = raw_info["ssh_host"]
            port = (
                int(raw_info["ssh_port"]) + 1
                if "jupyter" in raw_info["image_runtype"]
                else int(raw_info["ssh_port"])
            )
    except:
        port = -1

    if port < 0:
        raise RuntimeError(f"error: ssh port not found for instance {raw_info["id"]}")
    return ipaddr, port


def get_ssh_url(ipaddr, port, user):
    assert isinstance(ipaddr, str)
    assert isinstance(port, int)
    assert isinstance(user, str)

    ipaddr = shlex.quote(ipaddr)
    user = shlex.quote(user)

    return shlex.quote(f"ssh://{user}@{ipaddr}:{port}")


def get_instances(vast_sdk, use_proxy=False):
    raw_infos = vast_sdk.show_instances()

    instances = {}

    for i in raw_infos:

        try:
            ipaddr, port = get_ssh_port_ipaddr(i, use_proxy=use_proxy)
        except:
            # skip instance if we can't connect to it
            print(f"can't connect to {i["id"]}, skip!")
            continue
        instances.update(
            {
                f"v_{i["gpu_name"].replace(" ", "_")}_{i["id"]}": {
                    "ipaddr": ipaddr,
                    "port": port,
                    "id": int(i["id"]),
                }
            }
        )

    return instances


# for ssh
def get_ssh_profile(ipaddr, port, user):
    ssh_url = get_ssh_url(ipaddr, port, user)
    return {
        "path": "ssh",
        "args": [ssh_url],
        "icon": "terminal-linux",
    }


def get_ssh_profile_list(instances, user):
    re = {}

    for k, i in instances.items():
        re.update({k: get_ssh_profile(i["ipaddr"], i["port"], user)})

    return re


# for sftp
def get_sftp_profile(ipaddr, port, user, remotePath):
    return {
        "host": ipaddr,
        "port": port,
        "username": user,
        "remotePath": remotePath,
    }


def get_sftp_profile_list(instances, user, remotePath):
    re = {}

    for k, i in instances.items():
        re.update({k: get_sftp_profile(i["ipaddr"], i["port"], user, remotePath)})

    return re


# patching the settings.json file
def rm_entries_settingsjson(settingsjson_path=".vscode/settings.json"):
    if not os.path.isfile(settingsjson_path):
        # print(f"{settingsjson_path} not found, skip!")
        return

    with open(settingsjson_path, "r") as file:
        data = json.load(file)

    # only linux is supported now
    terminal_entries = data["terminal.integrated.profiles.linux"]

    delete_entries = []
    for k in terminal_entries.keys():
        if k.startswith("v_"):
            delete_entries.append(k)

    for k in delete_entries:
        del terminal_entries[k]

    with open(settingsjson_path, "w") as file:
        json.dump(data, file, indent=4)


def add_entries_settingsjson(
    instances, user, settingsjson_path=".vscode/settings.json"
):
    if not os.path.isfile(settingsjson_path):
        print(f"{settingsjson_path} not found, create new")
        data = {"terminal.integrated.profiles.linux": {}}
    else:
        with open(settingsjson_path, "r") as file:
            data = json.load(file)

    # only linux is supported now
    terminal_entries = data["terminal.integrated.profiles.linux"]

    terminal_entries.update(get_ssh_profile_list(instances, user))

    os.makedirs(os.path.dirname(settingsjson_path), exist_ok=True)
    with open(settingsjson_path, "w") as file:
        json.dump(data, file, indent=4)


# patching the sftp.json file


def rm_entries_sftpjson(sftpjson_path=".vscode/sftp.json"):
    if not os.path.isfile(sftpjson_path):
        # print(f"{sftpjson_path} not found, skip!")
        return

    with open(sftpjson_path, "r") as file:
        data = json.load(file)

    # only linux is supported now
    profiles_entries = data["profiles"]

    delete_entries = []
    for k in profiles_entries.keys():
        if k.startswith("v_"):
            delete_entries.append(k)

    for k in delete_entries:
        del profiles_entries[k]

    with open(sftpjson_path, "w") as file:
        json.dump(data, file, indent=4)


def add_entries_sftpjson(
    instances, user, remotePath, sftpjson_path=".vscode/sftp.json"
):
    if not os.path.isfile(sftpjson_path):
        print(f"{sftpjson_path} not found, create new")

        if os.path.isfile("sftp.template.json"):
            print("use sftp template at sftp.template.json")
            with open("sftp.template.json", "r") as file:
                data = json.load(file)

                if "profiles" not in data:
                    data["profiles"] = {}
        else:
            data = {"profiles": {}}
    else:
        with open(sftpjson_path, "r") as file:
            data = json.load(file)

    # only linux is supported now
    profiles_entries = data["profiles"]

    profiles_entries.update(get_sftp_profile_list(instances, user, remotePath))

    os.makedirs(os.path.dirname(sftpjson_path), exist_ok=True)
    with open(sftpjson_path, "w") as file:
        json.dump(data, file, indent=4)


# pull infos and path all, removing old instances
def patch_all(user, remotePath, instances):

    # remove old entries
    rm_entries_settingsjson()
    rm_entries_sftpjson()

    # add new entries
    add_entries_settingsjson(instances, user)
    add_entries_sftpjson(instances, user, remotePath)


# install pixi
def install_pixi(vast_sdk, instance, user):
    ssh_str = get_ssh_url(ipaddr=instance["ipaddr"], port=instance["port"], user=user)

    cmd = f'ssh -o StrictHostKeyChecking=no {ssh_str} "curl -fsSL https://pixi.sh/install.sh | bash"'

    subprocess.run(cmd, shell=True)


def pick_instances(instances):
    # allow user to pick instances
    choices = list(instances.keys())
    for index, choice in enumerate(choices, start=1):
        print(f"{index}. {choice}")

    while True:
        selection = input("pick one or enter to pick all: ")

        if selection.strip() == "":
            return instances

        try:
            selection = int(selection)
        except:
            continue

        if 1 <= selection <= len(choices):

            return {choices[selection]: instances[choices[selection]]}


def main(args):

    vast_sdk = None
    instances = []
    # pull the instance infos
    # we don't need it for rm_instances
    if args.add_instances or args.install_pixi:
        vast_sdk = VastAI()
        instances = get_instances(vast_sdk, use_proxy=args.use_proxy)

        if len(instances) == 0:
            return

    if args.install_pixi:
        picked_instances = instances
        if len(instances) > 1:
            print("pick instance")
            picked_instances = pick_instances(instances)

        for k, v in picked_instances.items():
            print(f"install pixi to {k}")
            install_pixi(vast_sdk, v, args.user)

    if args.add_instances:
        print("add instances to vscode")
        patch_all(user=args.user, remotePath=args.remotePath, instances=instances)

    elif args.rm_instances:
        print("rm all instances from vscode")
        rm_entries_settingsjson()
        rm_entries_sftpjson()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-a",
        "--add_instances",
        action="store_true",
        help="add instances to vscode settings.json (ssh terminal profiles) and sftp.json",
    )
    parser.add_argument(
        "-r",
        "--rm_instances",
        action="store_true",
        help="remove all instances from vscode settings.json (ssh terminal profiles) and sftp.json",
    )

    parser.add_argument(
        "-i",
        "--install_pixi",
        action="store_true",
        help="install pixi to instance(s)",
    )

    parser.add_argument(
        "-p",
        "--use-proxy",
        action="store_true",
        help="use the the proxy ssh port",
    )

    parser.add_argument(
        "-rp",
        "--remotePath",
        type=str,
        help="sftp remotePath for the instance profiles, default to /workspace/project",
        default="/workspace/project",
    )

    parser.add_argument(
        "-u",
        "--user",
        type=str,
        help="sftp user for the instance profiles, it is ussually root anyways",
        default="root",
    )

    args = parser.parse_args()

    assert not (args.add_instances and args.rm_instances)

    main(args)
