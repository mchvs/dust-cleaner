dust-cleaner
==========

Joins "dust" payments created by p2pool into bigger transactions with minimal fee

Requirements:
-------------------------
Generic:
* Myriadcoin >=0.9.2.7
* Python >=2.6

Linux:
* sudo apt-get install python-pip -y
* sudo pip install requests

Running dust-cleaner.py:
-------------------------
* Install your local myriadcoind
* Import the private keys with the 'dust' payments into the local wallet
* Run dust-cleaner.py in test mode first, to confirm that your wallet is properly
set and that you are using the correct parameters.

`./dust-cleaner.py <destination-address>`

Replace `<destination-address>` with the Myriadcoin address to receive the new
created transaction.

For additional options:

`./dust-cleaner.py --help`

Donations are welcome to support this project:
* MKJxatRKSw9gTN1VJfVcHPDAbSKxWq97L5 (Myriadcoin)
* 1JffmEok4VbN3ZfGnHx84q9PEcHfH4Qfyw (Bitcoin)
