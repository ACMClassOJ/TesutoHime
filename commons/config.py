import yaml

def load_config (name: str, program_version: str) -> dict:
    filename = f'{name}_config.yml'
    with open(filename) as f:
        config = yaml.load(f, yaml.Loader)

    if not f'{name}_config' in config:
        raise Exception(f'Config file is not valid {name} config. Check your {filename}.')

    config_version = config[f'{name}_config']

    if config_version != program_version:
        raise Exception(f'{filename} has wrong version, has {config_version}, expecting {program_version}.')

    return config
