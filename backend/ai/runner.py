from dotenv import load_dotenv
from agents import Runner
from .agents import operator_agent

load_dotenv()


def main():
    print("Mini-IA do gêmeo digital (digite 'sair' para encerrar)\n")
    while True:
        q = input("Você: ").strip()
        if not q or q.lower() in {"sair", "exit", "quit"}:
            break
        result = Runner.run_sync(operator_agent, q)
        print("\nIA:", result.final_output, "\n")


if __name__ == "__main__":
    main()
