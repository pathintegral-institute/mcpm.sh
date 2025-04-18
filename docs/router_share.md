
# MCPM Router Share

## Introduction
Your local MCPM Router can be shared in public network and others can connect to your router by the share link and use your configured MCPM Profile. In this document, we will explain how to use it and how it works.

## Create a share link

```bash
mcpm router share
mcpm router share --profile <PROFILE_NAME> --address <ADDRESS>
```
There will be a share link and a secret. The final share link will be `http://<ADDRESS>?s=<SECRET>&profile=<PROFILE_NAME>`. You can share this link with others and by adding this share link to mcpm client, they can connect to your router.

If address is not specified, the share link will be proxied by our server `share.mcpm.sh`. You can also specify a custom address to share.

If profile is not specified, the share link will use the current active profile. If no active profile found, the user need to specify the profile manually.

To be noted that if your router is not on or your system sleeps, the shared link will not be accessible.

## How it works

We use a fork version of frp from [huggingface/frp](https://github.com/huggingface/frp) to create a tunnel to your local MCPM Router. You can also check the [original frp](https://github.com/fatedier/frp) for more details about frp.

If you want to set up your own frp tunnel, you can either build our docker image from scratch or use our published docker images for frps(server) and frpc(client) by following the instructions below.

In your public server, you can create a frps config following the guide [here](https://github.com/huggingface/frp?tab=readme-ov-file#setting-up-a-share-server). Then start the frps container by:
```bash
docker run -d --name frps -p 7000:7000 -p 7001:7001 -v /path/to/frps.ini:/frp/frps.ini ghcr.io/pathintegral-institute/frps:latest
```

Then you can share the router with your own frp server by specifying the address:
```bash
mcpm router share --address <YOUR_ADDRESS>
```

## Authentication
There will be a secret token generated for authentication. The user MUST specify the secret token as a query parameter `s=<SECRET>` when connecting to your router. Make sure to keep the secret token secure and only share it with trusted users.

## Unshare

```bash
mcpm router unshare
```

This will stop the tunnel and remove the share link.
