import os
from pathlib import Path

import yaml
from dotenv import dotenv_values
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

BASE = Path(__file__).resolve().parent

DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def normalize_key(key):
    key = key.strip().lower()
    if key in ("num_workers", "app_num_workers"):
        return "workers"
    if key.startswith("app_"):
        key = key[4:]
    return key

def coerce(key, value):
    if key in ("port", "workers"):
        return int(value)
    if key == "debug":
        return str(value).strip().lower() in ("true", "1", "yes", "on")
    return str(value)

def merge_layer(config, values):
    for key, value in values.items():
        if value is None:
            continue
        key = normalize_key(key)
        config[key] = coerce(key, value)

@app.get("/effective-config")
def effective_config(set: list[str] = Query(default=[])):
    config = dict(DEFAULTS)

    env_name = os.environ.get("APP_ENV", "development")
    yaml_path = BASE / f"config.{env_name}.yaml"

    if yaml_path.is_file():
        merge_layer(config, yaml.safe_load(yaml_path.read_text()) or {})

    env_file = dotenv_values(BASE / ".env")
    merge_layer(config, env_file)

    os_layer = {
        key: value
        for key, value in os.environ.items()
        if key.startswith("APP_") and key != "APP_ENV"
    }
    merge_layer(config, os_layer)

    for item in set:
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        key = normalize_key(key)
        config[key] = coerce(key, value)

    config["api_key"] = "****"
    return config
