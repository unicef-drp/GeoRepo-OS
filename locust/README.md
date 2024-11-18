# GeoRepo Load Testing Using Locust

## Description

Load test using Locust.

- Python based class
- Easy to generate scenario test using python
- Nice UI and charts that updates in real time


## Authentication Config

Create a json file under locust directory called `locust_auth.json`.
Below is the sample:

```
[
    {
        "username": "YOUR_USERNAME",
        "api_key": "YOUR_PASSWORD",
        "wait_time_start": null,
        "wait_time_end": null
    }
]
```

We can configure `wait_time_start` and `wait_time_end` for each user. If it is null, then the wait_time by default is a constant 1 second. 


## Usage: Virtual env

1. Create virtual environment
```
mkvirtualenv geo_locust
```

Or activate existing virtual environment
```
workon geo_locust
```

2. Install locust
```
pip3 install locust
```

3. Run locust master
```
locust -f locustfiles --class-picker
```

Web UI is available on http://localhost:8089/


## Usage: Docker Compose

TODO: docker compose for running locust


## Using Locust Web UI

TODO: add screenshots.

To start a new test:
1. Pick one or more the User class
2. (Optional) Configure tags in User class 
3. Set number of users
4. Set ramp up
5. Set the host
6. (Advanced Options) Set maximum run time
7. Click Start
