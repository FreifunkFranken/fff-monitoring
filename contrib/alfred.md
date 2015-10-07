# Start Master Server
```bash
alfred -i wlan0 -b none -m
# -b batmanif to be used on router
```

# Save Data
```bash
# Note that 0 - 63 are reserved (please send an e-mail to the
# authors if you want to register a datatype), and can not be used
# on the commandline. Information must be periodically written
# again to alfred, otherwise it will timeout and alfred will for-
# get about it (after 10 minutes).
cat r.xml | gzip | alfred -s 64
```

# Load Data
```bash
# 00:16:ea:c3:b8:26 is the mac of the sender
alfred-json -z -f string -r 64 | python -c 'import sys,json;print(json.load(sys.stdin)["00:16:ea:c3:b8:26"])'
```

# Slave Config
```
config 'alfred' 'alfred'
        option interface 'br-mesh'
        option mode 'slave'
        option batmanif 'bat0'
        option start_vis '0'
        option run_facters '1'
# REMOVE THIS LINE TO ENABLE ALFRED
#       option disabled '1'
```


## Install ALFRED on the Router
If the router has no IP, you will need to scp:
```
scp data.tar.gz root@[fe80::fad1:11ff:fe30:0abc%wlan0]:/tmp/
```

```
cd /tmp/
wget http://upload.kruton.de/files/1444228240/data.tar.gz
cd /
tar xzvf /tmp/data.tar.gz
uci set alfred.alfred.interface=br-mesh
uci set alfred.alfred.mode=slave
uci set alfred.alfred.start_vis=0
uci set alfred.alfred.run_facters=1
uci set alfred.alfred.batmanif=bat0
uci set alfred.alfred.disabled=0
uci commit
echo -e "#!/bin/sh\n\ncat /tmp/crawldata/node.data | alfred -s 64" > /etc/alfred/send_xml.sh
chmod +x /etc/alfred/send_xml.sh
/etc/init.d/alfred enable
/etc/init.d/alfred start
```
