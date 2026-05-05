from dotenv import load_dotenv

load_dotenv()  # must run before app imports so env vars are visible to all modules

from app.agent import SmartAgent  # noqa: E402
from app.dashboard import show_dashboard  # noqa: E402
from app.logging import setup_logging  # noqa: E402

setup_logging()


def main() -> None:
    show_dashboard()

    agent = SmartAgent()

    while True:
        try:
            user_input = input("\nВы: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit", "выход"]:
                print("Завершение работы...")
                break

            if user_input.lower() == "/clear":
                agent.clear_memory()
                print("🧹 Память агента успешно очищена! Начинаем с чистого листа.")
                continue

            agent.process_input(user_input)

        except KeyboardInterrupt:
            print("\nПринудительное завершение...")
            break


if __name__ == "__main__":
    main()
