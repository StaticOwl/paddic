from controller import monitor
import platform


if __name__ == "__main__":
    monitor(platform.system())