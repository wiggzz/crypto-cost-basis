import argparse
import csv
from dataclasses import dataclass
from datetime import datetime
from functools import reduce
from re import A
from typing import Iterable
from tabulate import tabulate


parser = argparse.ArgumentParser(description='cost basis')
parser.add_argument('-f', '--file', help='input file',
                    type=argparse.FileType('r'))
args = parser.parse_args()

DATE = 'Date'
AMOUNT = 'Amount'
CURRENCY = 'Currency'
DESCRIPTION = 'Description'
USD_AMOUNT = 'USD Amount'
TYPE = 'Type'
SOURCE = 'Source'

DATE_FORMAT = '%m/%d/%Y'
TIME_FORMAT = '%m/%d/%Y %H:%M:%S'


@dataclass
class CostBasis:
    btc_amount: float
    dollar_amount: float
    date: str
    source: str


@dataclass
class CapitalGain:
    type: str
    btc_amount: float
    proceeds: float
    cost_basis: float
    gain: float
    cost_basis_detail: Iterable[CostBasis]
    date: str
    source: str


def from_dollar_string(string: str) -> float:
    if not string:
        return 0
    if string.startswith('-'):
        return -from_dollar_string(string.strip('-'))
    return float(string.strip('$').replace(',', ''))


def from_btc_string(string: str) -> float:
    if not string:
        return 0
    return float(string)


def from_date_string(string: str) -> datetime:
    return datetime.strptime(string, TIME_FORMAT)


def format_cost_basis(m):
    return f'{m.btc_amount:0.8f} BTC for ${m.dollar_amount:0.2f} on {datetime.strftime(m.date, DATE_FORMAT)} at {m.source}'


def cost_basis_detail(cost_basis, proceeds=None) -> str:
    total = sum([m.btc_amount for m in cost_basis])
    if proceeds:
        proceeds_with_basis = [(proceeds * m.btc_amount / total, m)
                               for m in cost_basis]
        return '\n'.join([f'${p:0.2f} from {format_cost_basis(cb)}' for (p, cb) in proceeds_with_basis])
    else:
        return '\n'.join([format_cost_basis(m) for m in cost_basis])


reader = csv.DictReader(args.file)
rows = sorted([r for r in reader if r[DATE]],
              key=lambda r: from_date_string(r[DATE]))

cost_basis = []
capital_gain = []
for row in rows:
    btc_amount = from_btc_string(row[AMOUNT])
    dollar_amount = abs(from_dollar_string(row[USD_AMOUNT]))
    date = from_date_string(row[DATE])
    if row[TYPE] in ('Trade', 'Income', 'Gift') and row[CURRENCY] == 'BTC' and btc_amount > 0:
        if dollar_amount == 0:
            raise Exception(
                'Dollar amount of transaction must not be zero:' + str(row))
        basis = CostBasis(btc_amount=btc_amount,
                          dollar_amount=dollar_amount, date=date, source=row[SOURCE])
        cost_basis.append(basis)
    if row[TYPE] in ('Trade', 'Gift', 'Fee', 'Loss Adjustment') and row[CURRENCY] == 'BTC' and btc_amount < 0:
        if dollar_amount == 0:
            raise Exception(
                'Dollar amount of transaction must not be zero:' + str(row))
        btc_left = abs(btc_amount)
        matches = []
        new_basis = []
        for basis in cost_basis:
            if btc_left <= 0:
                new_basis.append(basis)
            elif btc_left <= basis.btc_amount:
                matched_btc = btc_left
                matched_dollar_amount = (
                    basis.dollar_amount / basis.btc_amount) * matched_btc
                match = CostBasis(
                    btc_amount=matched_btc, dollar_amount=matched_dollar_amount, date=basis.date, source=basis.source)
                matches.append(match)
                new_basis.append(CostBasis(btc_amount=basis.btc_amount - matched_btc,
                                 dollar_amount=basis.dollar_amount - matched_dollar_amount, date=basis.date, source=basis.source))
                btc_left -= matched_btc
            else:
                matched_btc = basis.btc_amount
                matched_dollar_amount = basis.dollar_amount
                matches.append(basis)
                btc_left -= matched_btc
        if btc_left > 0:
            raise Exception('Missing cost basis for ' +
                            str(btc_left) + 'BTC at ' + str(row))
        cost_basis = new_basis
        cost_basis_amount = sum([match.dollar_amount for match in matches])
        gain = dollar_amount - cost_basis_amount
        if row[TYPE] not in ('Fee', 'Loss Adjustment', 'Gift'):
            cg = CapitalGain(type=row[TYPE], btc_amount=abs(btc_amount), proceeds=dollar_amount, cost_basis=cost_basis_amount,
                             cost_basis_detail=matches, gain=gain, date=date, source=row[SOURCE])
            capital_gain.append(cg)

sales = []
years = {}
for gain in capital_gain:
    row = {}
    row['Date'] = datetime.strftime(gain.date, TIME_FORMAT)
    year_name = datetime.strftime(gain.date, '%Y')
    year = years.setdefault(year_name, {'Year': year_name, 'Total': 0})
    row['Note'] = f'{gain.type} of {gain.btc_amount:0.8f} BTC for ${gain.proceeds:0.2f} on {gain.source}'
    row['Proceeds'] = f'{gain.proceeds:0.2f}'
    row['Cost Basis'] = f'{gain.cost_basis:0.2f}'
    row['Capital Gain'] = f'{gain.gain:0.2f}'
    row['Cost Basis Detail'] = cost_basis_detail(
        gain.cost_basis_detail, gain.proceeds)
    year['Total'] += gain.gain
    sales.append(row)

print(tabulate(sales, headers="keys", tablefmt="fancy_grid"))
print('\n')

print('Remaining cost basis')
print(cost_basis_detail(cost_basis))
print('\n')

year = str(datetime.now().year - 1)
total = years[year]['Total']
print(f'Total for {year}: ${total:0.2f}')
