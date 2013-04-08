import_ok = True

try:
    import weechat as wee
except:
    print("No! Bad user!")
    import_ok = False

NAME = "buffer_priority"
AUTHOR = "numeral <numerical@gmail.com>"
VERSION = "0.05"
LICENSE = "GPL3"
DESCRIPTION = "This plugin attempts to be the end all of buffer placement."

conf_opt = "plist"

buffers = {} # Hold all the buffers in a dict

# Python2Weechat
def py2wee(dictionary):
    return ' '.join(list(map(lambda x: str(x) + " " + str(dictionary[x]), dictionary)))

# Weechat2Python
def wee2py(string):
    string = string.split()
    assert(len(string) % 2 == 0)
    d = {}
    for i in range(0, len(string), 2):
        try:
            d[string[i]] = int(string[i+1])
        except ValueError:
            pass

    return d

# Save
def save_state():
    global buffers
    if(len(buffers)):
        wee.config_set_plugin(conf_opt, py2wee(buffers))
    return

# Load
def load_state():
    global buffers
    if wee.config_is_set_plugin(conf_opt):
        buffers = wee2py(wee.config_get_plugin(conf_opt))
    else:
        buffers = {}
    return


def reorder_cb(data, signal, signal_data):
    reorder_buffers()
    return wee.WEECHAT_RC_OK

def reorder_buffers():
    global buffers
    if(len(buffers) == 0):
        return

    currents = {}
    # First pass over buffers to gather information
    infolist = wee.infolist_get("buffer", "", "")
    while wee.infolist_next(infolist):
        currents[wee.infolist_string(infolist, "name")] = wee.infolist_integer(infolist, "number")
        if(wee.infolist_string(infolist, "name") == 'weechat'): # I like the status buffer
            statusnumber = wee.infolist_integer(infolist, "number")
    wee.infolist_free(infolist)

    neworder = ['weechat']
    for buf in currents.keys():
        if currents[buf] == statusnumber: # merged with status buffer
            continue
        buf = buf.split('.', 1) # TODO Same as below, dot servers?
        try:
            buf = buf[1]
        except IndexError:
            buf = buf[0]
        if buf in buffers: # Has a priority
            foundplace = False
            for i in range(1, len(neworder)):
                if ((neworder[i] in buffers and buffers[neworder[i]] < buffers[buf])
                        or neworder[i] not in buffers):
                    foundplace = True
                    neworder.insert(i, buf)
                    break
            if not foundplace: # end of the line buddy
                neworder.append(buf)
            del foundplace
        else:                 # Doesn't have a priority
            neworder.append(buf)

    # Second pass to set all buffers to their correct values
    infolist = wee.infolist_get("buffer", "", "")
    while wee.infolist_next(infolist):
        name = wee.infolist_string(infolist, "name")
        if(wee.infolist_integer(infolist, "number") == 1):
            continue
        name = name.split('.', 1) # TODO Maybe servers with dots?
        try:
            name = name[1]
        except IndexError:
            name = name[0]
        wee.buffer_set(wee.infolist_pointer(infolist, "pointer"),
                "number", str((1+neworder.index(name))))

    return

def bpriority_add(dub):
    global buffers
    if(len(dub) != 2):
        return
    try:
        prio = int(dub[1])
    except ValueError:
        wee.prnt("", "Error: %s is not a number" % dub[1])
        return
    if(dub[0] in buffers):
        wee.prnt("", "Changing priority of %s to %d" % (dub[0], prio))
        buffers[dub[0]] = prio
    else:
        wee.prnt("", "Added %s with priority %d" % (dub[0], prio))
        buffers[dub[0]] =  prio
    reorder_buffers()
    save_state()
    return

def bpriority_del(dub):
    global buffers
    if(len(dub) != 1):
        wee.prnt("", "Incorrect number of arguments for delete command")
        return

    if dub[0].lower() == "all":
        buffers = {}
        wee.prnt("", "Cleared priority list")
        save_state()
        return

    if dub[0] not in buffers:
        wee.prnt("", "That buffer has no priority")
        return

    wee.prnt("", "Removed %s from the list of priorities" % (dub[0]))
    buffers.pop(dub[0])
    save_state()
    return

def bpriority_list():
    wee.prnt("", str(buffers))
    return

# Cmd
def bpriority_cmd(data, buffer, args):
    dub = args.split(' ')
    if(dub[0] == "add"):
        bpriority_add(dub[1:])
    elif(dub[0] == "del"):
        bpriority_del(dub[1:])
    elif(dub[0] == "list"):
        bpriority_list()
    else:
        return wee.WEECHAT_RC_ERROR

    return wee.WEECHAT_RC_OK

# Register
if __name__ == "__main__" and import_ok:
    if wee.register(NAME, AUTHOR, VERSION, LICENSE, DESCRIPTION, "", ""):
        wee.hook_command(
                "bpriority", # command
                "Change buffer priorities", # description
                "[list] || [add buffer priority] || [del buffer|all]", # args
                " add: adds a channel with a priority(0-999)\n"
                " del: deletes a buffer from the priority system\n", # arg desc
                "add del", # completions
                "bpriority_cmd", "")
        load_state()
        reorder_buffers()
        wee.hook_signal("buffer_opened", "reorder_cb", "")

