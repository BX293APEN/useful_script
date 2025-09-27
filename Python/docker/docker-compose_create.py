import yaml, os

class Container:
    def __init__(
        self,
        name,
        image                   = None,
        envFile                 = None,
        container_name          = "Docker_Linux",
        hostName                = "Docker_Linux",
        dockerFilePath          = None,
        volumes                 = None,
        restart                 = "no",
        envvar                  = None,
        ports                   = None,
        command                 = None,
        networks                = None,
        depends_on              = None,
    ):
        self.name               = name
        self.image              = image
        self.env_file           = envFile
        self.container_name     = container_name
        self.hostname           = hostName
        self.dockerfile         = dockerFilePath
        self.volumes            = volumes or []
        self.restart            = restart
        self.environment        = envvar or []
        self.ports              = ports or []
        self.command            = command
        self.networks           = networks or []
        self.depends_on         = depends_on or []
        self.config             = dict()

    def to_dict(self):
        self.config = {
            "container_name"    : self.container_name,
            "hostname"          : self.hostname,
            "restart"           : self.restart,
        }

        if self.image and (self.dockerfile is None):
            self.config["image"]           = self.image

        if self.command:
            self.config["command"]         = self.command
        if self.env_file:
            self.config["env_file"]        = self.env_file
        if self.environment:
            self.config["environment"]     = self.environment
        if self.ports:
            self.config["ports"]           = self.ports
        if self.volumes:
            self.config["volumes"]         = self.volumes
        if self.dockerfile:
            dockerfilePath                  = os.path.abspath(self.dockerfile)
            context                         = os.path.dirname(dockerfilePath)
            dockerfile                      = os.path.basename(dockerfilePath)
            self.config["build"]           = {
                "context"                   : context,
                "dockerfile"                : dockerfile
            }
        if self.networks:
            self.config["networks"]        = self.networks
        
        if self.depends_on:
            self.config["depends_on"] = self.depends_on

        return self.name, self.config


class Network:
    def __init__(
        self, 
        name, 
        driver                              = "bridge", 
        subnet                              = "192.168.1.0", 
        prefix                              = 24, 
        gateway                             = "192.168.1.1"
    ):
        self.name                           = name
        self.driver                         = driver
        self.subnet                         = f"{subnet}/{prefix}"
        self.gateway                        = gateway
        self.config                         = dict()

    def to_dict(self):
        self.config                         = {
            "driver": self.driver
        }
        if self.subnet and self.gateway:
            ipam_config = {
                "config": [
                    {
                        "subnet"            : self.subnet,
                        "gateway"           : self.gateway
                    }
                ]
            }

            self.config["ipam"] = ipam_config
        return self.name, self.config


class Compose:
    def __init__(self):
        self.containers                         = []
        self.networks                           = []

    def add_container(self, container: Container):
        self.containers.append(container)

    def add_network(self, network: Network):
        self.networks.append(network)

    def to_dict(self):
        compose_dict                            = {
            "services": {},
        }

        for container in self.containers:
            name, conf                          = container.to_dict()
            compose_dict["services"][name]      = conf

        if self.networks:
            compose_dict["networks"]            = {}
            for network in self.networks:
                name, conf                      = network.to_dict()
                compose_dict["networks"][name]  = conf

        return compose_dict

    def to_yaml(self, filepath="docker-compose.yml"):
        with open(filepath, "w") as f:
            yaml.dump(self.to_dict(), f, sort_keys=False, indent=2)


if __name__ == "__main__":
    # ネットワーク作成
    net1                = Network(name="frontend_net")
    net2                = Network(name="backend_net")


    # コンテナ作成
    web                 = Container(
        name            = "web",
        image           = "nginx:alpine",
        ports           = ["80:80"],
        networks        = [net1.name]
    )

    app                 = Container(
        name            = "app",
        image           = "myapp:latest",
        dockerFilePath  = "Dockerfile.app",
        volumes         = ["./app:/app"],
        envvar          = ["ENV=production"],
        ports           = ["5000:5000"],
        networks        = [net1.name, net2.name]
    )

    db                  = Container(
        name            = "db",
        image           = "mysql:5.7",
        envvar          = ["MYSQL_ROOT_PASSWORD=root"],
        networks        = [net2.name]
    )

    # Composeに追加
    compose = Compose()
    compose.add_network(net1)
    compose.add_network(net2)
    compose.add_container(web)
    compose.add_container(app)
    compose.add_container(db)

    # YAML出力
    compose.to_yaml("docker-compose.yml")
    print("docker-compose.yml を生成しました。")