from dotenv import load_dotenv

# Загружаем ключи до импорта остальных модулей
load_dotenv()

from app.dashboard import show_dashboard
from app.agent import SmartAgent

def main() -> None:
    show_dashboard()

    agent = SmartAgent()

    print("💡 Hint: Ask 'How much is 200 dollars in rubles?' or 'Read report.txt'")

    while True:
        try:
            user_input = input("\nВы: ").strip()
            if not user_input:
                continue
            if user_input.lower() in["exit", "quit", "выход"]:
                print("Завершение работы...")
                break

            # --- НОВАЯ КОМАНДА ОЧИСТКИ ---
            if user_input.lower() == "/clear":
                agent.clear_memory()
                print("🧹 Память агента успешно очищена! Начинаем с чистого листа.")
                continue
            # -----------------------------

            agent.process_input(user_input)

        except KeyboardInterrupt:
            print("\nПринудительное завершение...")
            break
if __name__ == "__main__":
    main()
