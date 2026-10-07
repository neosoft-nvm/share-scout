"""GVfs mount helper. Credentials arrive through stdin, never command arguments."""
import json
import sys
from gi.repository import Gio, GLib

credentials = json.load(sys.stdin)
loop = GLib.MainLoop()
operation = Gio.MountOperation()
response = {'ok': False}
asked = False


def password(op, message, default_user, default_domain, flags):
    global asked
    if asked:
        response.update(auth=True, error='The computer did not accept those sign-in details.')
        op.reply(Gio.MountOperationResult.ABORTED)
        return
    asked = True
    if not credentials:
        if flags & Gio.AskPasswordFlags.ANONYMOUS_SUPPORTED:
            op.set_anonymous(True)
        else:
            response.update(auth=True)
            op.reply(Gio.MountOperationResult.ABORTED)
            return
    else:
        op.set_anonymous(False)
        op.set_username(credentials.get('username', default_user))
        op.set_domain(credentials.get('domain') or default_domain or '')
        op.set_password(credentials.get('password', ''))
        op.set_password_save(Gio.PasswordSave.NEVER)
    op.reply(Gio.MountOperationResult.HANDLED)


def question(op, message, choices):
    response.update(error=message)
    op.reply(Gio.MountOperationResult.ABORTED)


def finished(file, result):
    try:
        file.mount_enclosing_volume_finish(result)
        response.update(ok=True)
    except GLib.Error as exc:
        if exc.matches(Gio.io_error_quark(), Gio.IOErrorEnum.ALREADY_MOUNTED): response.update(ok=True)
        else:
            response.update(error=exc.message)
            if exc.matches(Gio.io_error_quark(), Gio.IOErrorEnum.PERMISSION_DENIED): response.update(auth=True)
    loop.quit()

operation.connect('ask-password', password)
operation.connect('ask-question', question)
Gio.File.new_for_uri(sys.argv[1]).mount_enclosing_volume(Gio.MountMountFlags.NONE, operation, None, finished)
loop.run()
print(json.dumps(response))
