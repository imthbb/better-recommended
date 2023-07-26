<p><img align="center" src="https://github.com/imthbb/better-recommended/blob/main/preview.gif"></p>

# How to setup on Linux:  
#1  
Install the Deb package.  
#2  
`pip install stem`  
`pip install pysocks`  
#3  
Tor must be installed.  
  
Tor path is `.../tor-browser_en-US/Browser/TorBrowser/Tor/tor`.  
In `settings.py` set it as the value of `TOR_PATH`.  
  
In terminal:  
`THE_TOR_PATH --hash-password YOUR_NEWLY_CREATED_PASSWORD`  
  
The whole returned string is the hashed password.  
(Might be good if the original password is saved somewhere.)  
  
In `.../tor-browser_en-US/Browser/TorBrowser/Data/Tor/torrc` add:  
`HashedControlPassword THE_HASHED_PASSWORD`  
`ControlPort 9051`  
  
If you want to use another port, you'll also have to change the value  
of `CONTROL_PORT` in `settings.py`.  
# How to use:  
Enter Youtube/Twitch/Bitchute URLs of EXISTING channels in `channel URLs`.  
Those are the "subscriptions".  
Other things that aren't Youtube/Twitch/Bitchute URLs could be written as well.  
  
Run `scrape.py` to get results.  
  
Open `vids.html`.  
Clicking tall space in sidebar changes between subscriptions and recommendations.  
Scrolling changes pages.  
  
If the script raises an error, Tor has to be killed manually.  
That could be done through a terminal or a system monitor.  
  
Other Tor processes, such as the Tor browser, can't run while the script is running.
