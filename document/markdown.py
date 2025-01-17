import pyperclip


def main():
    while True:
        # Display the main menu
        print("Select an option:")
        print("1. Table")
        print("2. Task List")
        print("3. Mermaid Diagram")
        print("0. Exit")
        choice = input("Enter your choice: ")

        if choice == '1':
            create_table()
        elif choice == '2':
            create_task_list()
        elif choice == '3':
            create_mermaid()
        elif choice == '0':
            print("Exiting the program. Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")


def create_table():
    # Prompt user for table dimensions
    dimensions = input("Enter table dimensions (e.g., 3x5): ")
    try:
        rows, cols = map(int, dimensions.split('x'))
        table = generate_table(rows, cols)
        print("\nGenerated Table:\n")
        print(table)
        pyperclip.copy(table)
        print("Table copied to clipboard!\n")
    except ValueError:
        print("Invalid format. Please enter dimensions as NxM (e.g., 3x5).\n")


def generate_table(rows, cols):
    # Generate a markdown table with the specified rows and columns
    header = "| " + " | ".join(f"Header{i+1}" for i in range(cols)) + " |"
    separator = "| " + " | ".join("---" for _ in range(cols)) + " |"
    body = "\n".join("| " + " | ".join(f"Cell{i+1}{j+1}" for j in range(cols)) + " |" for i in range(rows))
    return "\n".join([header, separator, body])


def create_task_list():
    # Generate and copy a sample task list
    task_list = "- [x] Write the press release\n- [ ] Update the website\n- [ ] Contact the media"
    print("\nGenerated Task List:\n")
    print(task_list)
    pyperclip.copy(task_list)
    print("Task list copied to clipboard!\n")


def create_mermaid():
    # Display the Mermaid diagram options
    print("Select a Mermaid diagram type:")
    print("1. FlowChart")
    print("2. Sequence Diagram")
    print("3. Gantt Diagram")
    print("4. Class Diagram")
    diagram_choice = input("Enter your choice (1/2/3/4): ")

    # Define Mermaid diagrams
    mermaid_diagrams = {
        '1': """```mermaid
graph TD;
    A-->B;
    A-->C;
    B-->D;
    C-->D;
```""",
        '2': """```mermaid
sequenceDiagram
    participant Alice
    participant Bob
    Alice->>John: Hello John, how are you?
    loop HealthCheck
        John->>John: Fight against hypochondria
    end
    Note right of John: Rational thoughts <br/>prevail!
    John-->>Alice: Great!
    John->>Bob: How about you?
    Bob-->>John: Jolly good!
```""",
        '3': """```mermaid
gantt
dateFormat  YYYY-MM-DD
title Adding GANTT diagram to mermaid
excludes weekdays 2014-01-10

section A section
Completed task            :done,    des1, 2014-01-06,2014-01-08
Active task               :active,  des2, 2014-01-09, 3d
Future task               :         des3, after des2, 5d
Future task2               :         des4, after des3, 5d
```""",
        '4': """```mermaid
classDiagram
Class01 <|-- AveryLongClass : Cool
Class03 *-- Class04
Class05 o-- Class06
Class07 .. Class08
Class09 --> C2 : Where am i?
Class09 --* C3
Class09 --|> Class07
Class07 : equals()
Class07 : Object[] elementData
Class01 : size()
Class01 : int chimp
Class01 : int gorilla
Class08 <--> C2: Cool label
```"""
    }

    # Output the selected Mermaid diagram
    if diagram_choice in mermaid_diagrams:
        diagram = mermaid_diagrams[diagram_choice]
        print("\nGenerated Mermaid Diagram:\n")
        print(diagram)
        pyperclip.copy(diagram)
        print("Mermaid diagram copied to clipboard!")
        print("Documentation link: https://mermaid.js.org/intro/\n")
    else:
        print("Invalid choice. Please try again.\n")


if __name__ == "__main__":
    main()
