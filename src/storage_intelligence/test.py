from pathlib import Path

# Get the User's Home Directory
home_dir = Path.home()

# Define a specific path
example_path = home_dir / "Documents"

def print_tree(path: Path, indent: int = 0) -> None:
    prefix = "  " * indent
    for item in path.iterdir():
        if item.is_dir():
            print(f"{prefix}[DIR] {item.name}/")
            print_tree(item, indent + 1)
        else:
            print(f"{prefix}{item.name}")


print_tree(example_path)

