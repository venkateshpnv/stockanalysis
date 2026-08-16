from polygon import RESTClient

client = RESTClient("2AucpFF4dCC31HNXfUKanrHGilcwp4Qy")

contracts = []
for c in client.list_options_contracts(
	underlying_ticker="AAPL",
	contract_type="call",
	order="asc",
	sort="expiration_date",
	):
    contracts.append(c)

print(contracts)

