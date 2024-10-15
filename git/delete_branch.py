import subprocess


def run_command(command):
    """Run a shell command and return its output and error."""
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True)
    return result.stdout.strip(), result.stderr.strip()


def fetch_and_prune():
    """Fetch and prune remote branches."""
    print("Fetching and pruning remote branches...")
    stdout, stderr = run_command("git fetch -p")
    if stderr:
        print(f"Error during fetch: {stderr}")
    else:
        print(stdout)
    print("Fetch and prune completed.")


def list_local_branches():
    """List all local branches."""
    stdout, _ = run_command("git branch")
    branches = stdout.splitlines()
    branches = [branch.strip() for branch in branches]
    return branches


def delete_local_branches():
    """Delete local branches based on prefix."""
    while True:
        branches = list_local_branches()

        print("\nLocal branches:")
        for branch in branches:
            print(branch)

        print("\n1. Refresh branch list")
        print("2. Enter prefix to delete branches")
        print("0. Return to main menu")
        choice = input("Enter your choice: ")

        if choice == "0":
            return
        elif choice == "1":
            continue
        elif choice == "2":
            prefix = input(
                "Enter the prefix of branches you want to delete: ").strip()
            if not prefix:
                print("No prefix entered. Returning to main menu.")
                continue

            branches_to_delete = [
                branch for branch in branches if branch.startswith(prefix)]
            if not branches_to_delete:
                print(f"No branches found with prefix '{prefix}'.")
                continue

            successes, failures = [], []
            for branch in branches_to_delete:
                _, stderr = run_command(f"git branch -d {branch}")
                if stderr:
                    failures.append((branch, stderr))
                else:
                    successes.append(branch)

            print(f"Total branches to delete: {len(branches_to_delete)}")
            print(f"Successfully deleted: {len(successes)}")
            print(f"Failed to delete: {len(failures)}")

            if failures:
                print("Failed branches:")
                for branch, error in failures:
                    print(f"{branch}: {error}")

                retry = input(
                    "Do you want to force delete the failed branches? (Y/N): ").strip().lower()
                if retry == "y":
                    for branch, _ in failures:
                        _, stderr = run_command(f"git branch -D {branch}")
                        if stderr:
                            print(f"Failed to force delete {branch}: {stderr}")
                        else:
                            print(f"Successfully force deleted {branch}")


def list_remote_branches():
    """List all remote branches."""
    stdout, _ = run_command("git branch -r")
    branches = stdout.splitlines()
    branches = [branch.strip() for branch in branches]
    return branches


def delete_remote_branches():
    """Delete remote branches based on prefix."""
    while True:
        branches = list_remote_branches()

        print("\nRemote branches:")
        for branch in branches:
            print(branch)

        print("\n1. Refresh branch list")
        print("2. Enter prefix to delete remote branches")
        print("0. Return to main menu")
        choice = input("Enter your choice: ")

        if choice == "0":
            return
        elif choice == "1":
            continue
        elif choice == "2":
            prefix = input(
                "Enter the prefix of remote branches you want to delete: ").strip()
            if not prefix:
                print("No prefix entered. Returning to main menu.")
                continue

            branches_to_delete = [
                branch for branch in branches if branch.startswith(prefix)]
            if not branches_to_delete:
                print(f"No remote branches found with prefix '{prefix}'.")
                continue

            successes, failures = [], []
            for branch in branches_to_delete:
                _, stderr = run_command(
                    f"git push --delete origin {branch.split('/')[-1]}")
                if stderr:
                    failures.append((branch, stderr))
                else:
                    successes.append(branch)

            print(
                f"""Total remote branches to delete: {
                    len(branches_to_delete)}""")
            print(f"Successfully deleted: {len(successes)}")
            print(f"Failed to delete: {len(failures)}")

            if failures:
                print("Failed remote branches:")
                for branch, error in failures:
                    print(f"{branch}: {error}")


def main_menu():
    """Display the main menu and handle user input."""
    while True:
        print("\nGit Branch Manager")
        print("1. Fetch and prune remote branches")
        print("2. Delete local branches by prefix")
        print("3. Delete remote branches by prefix")
        print("0. Exit")
        choice = input("Enter your choice: ")

        if choice == "1":
            fetch_and_prune()
        elif choice == "2":
            delete_local_branches()
        elif choice == "3":
            delete_remote_branches()
        elif choice == "0":
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    main_menu()
