import beans
import logging
import config


def main():
    if err := config.check():
        print(err)
        exit(1)

    # tx = beans.create_tx(
    #     "narration", "Expenses:Viaje", "Assets:EUR:Leo:Cash", 2498, "EUR"
    # )
    # beans.append_tx(tx, c.bean_append_file)

    beans.get_expense_accounts(config.bean_file)
    exit(0)


if __name__ == "__main__":
    main()
