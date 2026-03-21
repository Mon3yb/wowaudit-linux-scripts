# wowaudit-linux-scripts
Helper scripts to run WoWAudit client operations on Linux
Basically does the same as the WoWAudit client on Windows. You will need to configure your api token and your installation path in the script files.

You can either run them manually with `python <script>` or add them as a systemd service

## Adding the scripts to systemd
https://wiki.archlinux.org/title/Systemd/User  
This is how I did it. If you want to adjust stuff, do it ;)  

I created the files in the user systemd at `~/.config/systemd/user/`

Create a .service file and a .timer file.  
e.g. wowaudit-update-wishlist.service and wowaudit-upload-wishlist.timer  

For the .service file I added the following:  
```
[Unit]
Description=Update WoWAudit wishlist for RCLootCouncil

[Service]
Type=oneshot
ExecStart=python "<PATH_TO_YOUR_SCRIPT_FILE>"
```  

For the .timer file I added this:  
```
[Unit]
Description=Run WoWAudit update Wed/Thu 19:00-22:15 every 15 min

[Timer]
# Wed/Thu, every 15 minutes between 19:00 and 22:45
# DayOfWeek, Year-Month-Day Hour:Minute:Second
OnCalendar=Wed,Thu *-*-* 19..22:00,15,30,45:00

#true = triggers the service immediately if it missed the last start time
#Persistent=true
Unit=wowaudit-update-wishlist.service

[Install]
WantedBy=timers.target
```  

You can adjust the timings in the timer. It uses the same syntax as cron https://wiki.archlinux.org/title/Systemd/Timers  
Activate the systemd timers with `systemctl --user enable <timer-name.timer>`  

You can also manually toggle the services with `systemctl --user start <servicename.service>`  
I'm using that to trigger it with a hotkey in my system.
