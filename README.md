# How to Start the Divergent Discourses Application

This guide explains how to start the application on your computer and access it via your web browser. No technical knowledge is required.

---

## What You Need

Before you start, make sure the following are installed on your computer:

- **Docker** — the software that runs the application
- **Docker Compose** — the tool that manages the application's services (included with Docker Desktop)

---

## Installing Docker and Docker Compose

### On Windows

1. Download **Docker Desktop** from the official website:
   👉 https://docs.docker.com/desktop/install/windows-install/
2. Run the installer and follow the on-screen instructions
3. Restart your computer when prompted
4. Open Docker Desktop and wait until it shows **"Engine running"**

> Docker Compose is included with Docker Desktop — no separate installation needed.

---

### On Mac

1. Download **Docker Desktop** for Mac from:
   👉 https://docs.docker.com/desktop/install/mac-install/
   - Choose **Apple Silicon** if you have an M1/M2/M3 Mac
   - Choose **Intel Chip** if you have an older Mac
2. Open the downloaded `.dmg` file and drag Docker to your Applications folder
3. Open Docker from Applications and wait until it shows **"Engine running"**

> Docker Compose is included with Docker Desktop — no separate installation needed.

---

### On Linux (Ubuntu/Debian)

Open a terminal and run the following commands one by one:

```bash
# Install Docker
sudo apt update
sudo apt install -y docker.io

# Install Docker Compose
sudo apt install -y docker-compose-plugin

# Add your user to the docker group (so you don't need sudo)
sudo usermod -aG docker $USER

# Apply the group change
newgrp docker
```

For other Linux distributions, see the official guide:
👉 https://docs.docker.com/engine/install/

---

### Verify Installation

After installing, open a terminal and type:

```
docker --version
docker compose version
```

You should see version numbers printed. If so, Docker is ready to use.

---

---

## Step 1 — Open a Terminal

### On Windows
1. Press `Windows key + R`
2. Type `cmd` and press Enter

### On Mac
1. Press `Command + Space`
2. Type `Terminal` and press Enter

### On Linux
1. Press `Ctrl + Alt + T`

---

## Step 2 — Download the Application from GitHub

If you haven't already downloaded the application, clone the GitHub repository by typing the following command in the terminal and pressing Enter:

```
git clone https://github.com/kyogoku11/docker-setup.git
```

> **Note:** If `git` is not installed, download it from 👉 https://git-scm.com/downloads

This creates a folder called `docker-setup` in your current directory containing all necessary files.

---

## Step 3 — Navigate to the Application Folder

In the terminal, type the following command and press Enter:

```
cd /path/to/docker
```

> Replace `/path/to/docker` with the folder where you cloned or downloaded the GitHub repository `docker-setup`. For example, if you downloaded it to your home folder, the path would be `~/docker-setup`.

---

## Step 4 — Log In to Docker Hub and Pull the Application

The application image is stored on Docker Hub. You need to log in first to download it.

Type the following command and press Enter:

```
docker login
```

Enter your Docker Hub username and password when prompted.

Then pull the application image:

```
docker pull kyogoku11/divergent_discourses:nginx
```

Wait until the download is complete.

> **Note:** You need a Docker Hub account with access to the private repository. To get access:
> 1. Create a free account at 👉 https://hub.docker.com
> 2. Send your Docker Hub username to the administrator
> 3. The administrator will add you as a collaborator to the private repository via Docker Hub → Repository Settings → Collaborators
> 4. Once added, you can log in and pull the image as described above

---

## Step 5 — Start the Application

Type the following command and press Enter:

```
docker compose up -d
```

Wait until you see a message like:

```
✔ Container nginx-dd     Started
✔ Container search-app   Started
✔ Container corpus-app   Started
✔ Container corpus-api   Started
```

This means all parts of the application are running.

> **Note:** The first time you run this command, it may take a few minutes to download the necessary files.

---

## Step 6 — Open the Application in Your Browser

Open your web browser (Chrome, Firefox, Safari, etc.) and type the following address in the address bar:

```
http://localhost:81
```

Press Enter. You should see the application's entry page.

---

## Step 7 — Using the Application

From the entry page you can access the following features:

| Button | Description |
|---|---|
| 🔎 **Search Interface** | Search through the corpus ⚠️ *Requires API keys — contact the administrator to obtain them before use* |
| 📊 **Corpus Analysis Tool** | Analyse and explore the corpus |
| 🖼️ **Newspaper Images** | Browse newspaper image archives |

Simply click on the button for the feature you want to use.

---

## Step 8 — Stopping the Application

When you are finished, you can stop the application by opening the terminal again and typing:

```
docker compose down
```

This safely stops all running services.

---

## Troubleshooting

### The page does not load
- Make sure you ran `docker compose up -d` in Step 3
- Check that Docker is running on your computer
- Try refreshing the browser page

### The application is slow to start
- Wait 1–2 minutes after running `docker compose up -d` before opening the browser
- The services need a short time to fully start up

### I see "502 Bad Gateway"
- Wait a moment and refresh the page — the backend services may still be starting up

### I see "404 Not Found"
- Make sure you are using the correct address: `http://localhost`
- Check that all containers are running by typing `docker ps` in the terminal

### How to check if containers are running
Type the following in the terminal:

```
docker ps
```

You should see four containers listed with status `Up`:

```
CONTAINER ID   IMAGE    ...   STATUS       NAMES
xxxx           ...      ...   Up 2 mins    nginx-dd
xxxx           ...      ...   Up 2 mins    search-app
xxxx           ...      ...   Up 2 mins    corpus-app
xxxx           ...      ...   Up 2 mins    corpus-api
```

If any container shows `Restarting` instead of `Up`, contact your system administrator.

---

## Quick Reference

| Task | Command |
|---|---|
| Start the application | `docker compose up -d` |
| Stop the application | `docker compose down` |
| Check if running | `docker ps` |
| View error logs | `docker logs nginx-dd` |
