from dataclasses import dataclass
import docker

@dataclass
class OpsResult:
    ok: bool
    exit_code: int
    output: bytes | None
    paths: list[str]


from abc import ABC, abstractmethod

class Ops(ABC):
    @abstractmethod
    def schema(self) -> list[dict]:
        """
        Returns the JSON schema for OpenAI function calls.
        """
        pass


class TerminalOps(Ops):
    def __init__(self, container_name: str):
        self.client = docker.from_env()
        self.container = self.client.containers.get(container_name)

    def send_command(self, command: str) -> OpsResult:
        """
        Run command in the terminal and wait for the result
        """
        result = self.container.exec_run(command)
        return OpsResult(
            ok=(result.exit_code == 0),
            output=result.output,
            exit_code=result.exit_code,
            paths=[]
        )

    @staticmethod
    def schema() -> list[dict]:
        """
        Returns the JSON schema for OpenAI function calls.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": TerminalOps.send_command.__name__,
                    "description": TerminalOps.send_command.__doc__,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "The command to be executed in the terminal.",
                            }
                        },
                        "required": ["command"],
                    },
                }
            }
        ]


class RetrievalOps(Ops):
    def __init__(self, container_name: str):
        self.client = docker.from_env()
        self.container = self.client.containers.get(container_name)

    def get_file_tree(self, path: str, depth: int=1) -> OpsResult:
        """
        List path recursively with limited depth. Path is relative to current dir.
        """
        command = f"find '{path}' -type f -maxdepth {depth} -print0"
        result = self.container.exec_run(command)
        listed_paths = result.output.decode('utf-8').split('\0')
        if result.exit_code == 0:
            return OpsResult(
                ok=True,
                output=None,
                paths=listed_paths,
                exit_code=result.exit_code
            )
        else:
            return OpsResult(
                ok=False, output=result.output, exit_code=result.exit_code, paths=[]
            )

    
    @staticmethod
    def schema() -> list[dict]:
        """
        Returns the JSON schema for OpenAI function calls.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": RetrievalOps.get_file_tree.__name__,
                    "description": RetrievalOps.get_file_tree.__doc__,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Directory to list relative to current",
                            },
                            "depth": {
                                "type": "number",
                                "description": "Depth limit, default 1",
                            }
                        },
                        "required": ["path"],
                    },
                }
            }
        ]
