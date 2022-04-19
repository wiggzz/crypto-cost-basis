# bitcoin cost basis calculator

## install

    pipenv install

## run

Create a CSV with all your transactions (good luck). It should have columns

    Date,Amount,Currency,Description,USD Amount,Type,Source

The date should be in `mm/dd/yyyy HH:MM:SS` format.

Then run

    pipenv run python go.py -f <filename>

To calculate the cost basis of your transactions.

Supported transaction types are `Trade`, `Income`, `Gift`, `Fee`, and `Loss Adjustment`.
