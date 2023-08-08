# 1. Development Setup
## 1.1. Dependencies

### 1.1.1. OS-Level Dependencies
The project requires Python 3.10 or newer which needs to be installed before installing other dependencies. It requires following OS-level packages:
* `build-essential`
* `python3-dev`
* `gcc`
* `libgdal-dev`
* `libspatialindex-dev`

On Ubuntu 18.04+, simply running following command should be sufficient:


```
sudo apt update
sudo apt install build-essential python3-dev gcc libgdal-dev libspatialindex-dev
```
After installation running `python --version` will confirm if we have right Python version installed.

For other operating systems, please refer to OS-specific documentation for equivalent packages/tools.

### 1.1.2. Installing Remaining Python Packages
It is recommended to use Python virtual environment to isolate the packages required for this repository, thus, avoiding any dependency issues. Plus it keeps the system packages clean. Use the following command to create a new virtual environment (here we're calling it venv).
```
python -m venv venv
```
This will create a new directory named `venv`. This directory is already included in `.gitignore`. If you mean to use some other name for your virtual environment, please don't forget to add it to `.gitignore` otherwise the whole junk in that folder will be added to git. We now need to activate the environment.
```
source venv/bin/activate
```
If everything done correctly, we will see `(venv)` on the left side of terminal prompt. This indicates that our virtual environment is now activated. We can proceed with installation of required packages. Also keep in mind that trying to install packages without activating virtual environment will add packages to system Python, which certainly kills the purpose of virtual environment.

### 1.1.3. Installing Remaining Python Packages

Finally, remaining Python packages can be installed from `requirements.txt` file like this:

```
pip install -r requirements.txt
```
If you have to install more packages, you should update `requirements.txt` file using following command.
```
pip freeze > requirements.txt
```

### 1.1.4. Running the Code
For the development, code can be run by executing `main.py` file present in root directory like this:
```
python main.py
```

#### Optional: Enabling Hot Reload
To enable hot reloading during development, simply change from `reload=False` to `reload=True` in following code inside the file `main.py`.
```
uvicorn.run("app.api:app", host="0.0.0.0", port=8000, reload=False)
```

# 2. Docker Deployment
A `Dockerfile` is present in root directory of `wolfpack-api` repository which can be used to create docker images and build containers. In order to deploy, simply go to root directory of the project and run following command to build a container image. Docker needs to be installed and running on the system (don't forget dot at the end).

```
docker build -t aqms-api .
```

Now the container can be started from the generated image using following command. By default the API exposes port 8000 internally which can be mapped to any vacant port on the system.

```
docker run -d -p 8000:8000 aqms-api
```
