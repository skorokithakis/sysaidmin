# Sysaidmin

Sysaidmin is a GPT-powered sysadmin for your machine. You can ask it to solve a problem,
and it will run commands on your system (with your permission) to debug what's going on.

![](misc/demo.gif)


## Installation

Using `pipx` (recommended):

```bash session
$ pipx install sysaidmin
```

Using `pip` (less recommended, but still good):

```bash session
$ pip install sysaidmin
```

Specify your OpenAI API key:

```bash session
$ export OPENAI_API_KEY=sk-youropenaiapikeygoeshere
```

Then run Sysaidmin with your issue:

```bash session
$ sysaidmin "The foo process is emailing me and I don't know why."
```


## Sample run:

    $ sysaidmin "Whenever I try to SSH to localhost on port 22, it doesn't work. Can you fix it?"

    ==============================
    Running command: ssh localhost
    ==============================
    Press any key to continue, Ctrl-C to terminate...

    ssh: connect to host localhost port 22: Connection refused


    ==============================
    Running command: systemctl status sshd
    ==============================
    Press any key to continue, Ctrl-C to terminate...

    ● ssh.service - OpenBSD Secure Shell server
         Loaded: loaded (/lib/systemd/system/ssh.service; enabled; vendor preset: enabled)
         Active: active (running) since Sun 2023-11-26 18:40:45 EET; 25s ago
           Docs: man:sshd(8)
                 man:sshd_config(5)
        Process: 92469 ExecStartPre=/usr/sbin/sshd -t (code=exited, status=0/SUCCESS)
       Main PID: 92471 (sshd)
          Tasks: 1 (limit: 18824)
         Memory: 1.7M
            CPU: 9ms
         CGroup: /system.slice/ssh.service
                 └─92471 "sshd: /usr/sbin/sshd -D [listener] 0 of 10-100 startups"

    Νοε 26 18:40:45 zeus systemd[1]: Starting OpenBSD Secure Shell server...
    Νοε 26 18:40:45 zeus sshd[92471]: Server listening on 0.0.0.0 port 8122.
    Νοε 26 18:40:45 zeus sshd[92471]: Server listening on :: port 8122.
    Νοε 26 18:40:45 zeus systemd[1]: Started OpenBSD Secure Shell server.


    ==============================
    It appears that your SSH server is running, but it is not listening on the default SSH
    port 22. Instead, it is listening on port 8122 for both IPv4 and IPv6 connections, as
    indicated by the line "Server listening on 0.0.0.0 port 8122" and "Server listening on
    :: port 8122."

    To connect via SSH to localhost, you need to specify port 8122. You can do that by using
    the following command:

    ```bash
    ssh -p 8122 localhost
    ```

    Try running this command, and it should allow you to connect to the SSH server running
    on your local machine.
    ==============================

    Your response: No, please change the port

    ==============================
    Running command: sudo sed -i 's/#Port 22/Port 22/' /etc/ssh/sshd_config && sudo systemctl restart ssh
    ==============================
    Press any key to continue, Ctrl-C to terminate...
    ^C
