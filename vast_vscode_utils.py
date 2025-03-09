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


from vastai_sdk import VastAI
import argparse
import os
import json


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
    return f"ssh://{user}@{ipaddr}:{port}"


def get_instances(vast_sdk, use_proxy=False):
    raw_infos = vast_sdk.show_instances()

    instances = {}

    for i in raw_infos:

        ipaddr, port = get_ssh_port_ipaddr(i, use_proxy=use_proxy)

        instances.update(
            {
                f"v_{i["gpu_name"].replace(" ", "_")}_{i["id"]}": {
                    "ipaddr": ipaddr,
                    "port": port,
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
def patch_all(user, remotePath, use_proxy=False):
    vast_sdk = VastAI()

    instances = get_instances(vast_sdk, use_proxy=use_proxy)

    # remove old entries
    rm_entries_settingsjson()
    rm_entries_sftpjson()

    # add new entries
    add_entries_settingsjson(instances, user)
    add_entries_sftpjson(instances, user, remotePath)


def main(args):
    print(args)
    match args.action:
        case "add":
            patch_all(
                user=args.user, remotePath=args.remotePath, use_proxy=args.use_proxy
            )
        case "rm":
            rm_entries_settingsjson()
            rm_entries_sftpjson()
        case "install_pixi":
            raise NotImplementedError()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("action", type=str, help="add|rm|install_pixi")

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

    parser.add_argument(
        "-p",
        "--use-proxy",
        action="store_true",
        help="use the the proxy ssh port",
    )

    args = parser.parse_args()

    main(args)
