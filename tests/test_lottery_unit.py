from logging import exception
from aiohttp import request
from brownie import network, exceptions
from scripts.deploy_lottery import deploy_lottery
from scripts.helpful_scripts import (
    LOCAL_BLOCKCHAIN_ENVIRONEMNTS,
    get_account,
    fund_with_link,
    get_contract,
)
from web3 import Web3
import pytest


def test_get_entrance_fee():
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONEMNTS:
        pytest.skip()
    lottery = deploy_lottery()
    # if 1eth=2000usd then 0.025eth=50usd
    expected_entrance_fee = Web3.toWei(0.025, "ether")
    entrance_fee = lottery.getEntranceFee()
    assert entrance_fee == expected_entrance_fee


def test_cant_enter_unless_started():
    # Arrange
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONEMNTS:
        pytest.skip()
    lottery = deploy_lottery()

    # Act/Assert
    with pytest.raises(exceptions.VirtualMachineError):
        lottery.enter({"from": get_account(), "value": lottery.getEntranceFee()})


def test_can_start_and_enter_lottery():
    # Arrange
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONEMNTS:
        pytest.skip()
    lottery = deploy_lottery()
    account = get_account()
    lottery.startLottery({"from": account})
    # Act
    lottery.enter({"from": account, "value": lottery.getEntranceFee()})
    # Asssert
    assert lottery.players(0) == account


def test_can_end_lottery():
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONEMNTS:
        pytest.skip()
    lottery = deploy_lottery()
    account = get_account()
    lottery.startLottery({"from": account})
    lottery.enter({"from": account, "value": lottery.getEntranceFee()})
    fund_with_link(lottery)
    lottery.endLottery({"from": account})
    assert lottery.lottery_state() == 2


def test_can_pick_winner_correctly():
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONEMNTS:
        pytest.skip()
    lottery = deploy_lottery()
    account = get_account()
    lottery.startLottery({"from": account})
    lottery.enter({"from": account, "value": lottery.getEntranceFee()})
    lottery.enter({"from": get_account(index=1), "value": lottery.getEntranceFee()})
    lottery.enter({"from": get_account(index=2), "value": lottery.getEntranceFee()})
    fund_with_link(lottery)
    tx = lottery.endLottery({"from": account})
    request_id = tx.events["RequestedRandomness"]["requestId"]
    STATIC_RNG = 777
    get_contract("vrf_coordinator").callBackWithRandomness(
        request_id, STATIC_RNG, lottery.address, {"from": account}
    )

    starting_balance_of_account = account.balance()
    balance_of_lottery = lottery.balance()
    # 777 % 3 is gonna be the winner
    assert lottery.lotteryWinner() == account
    assert lottery.balance() == 0
    assert account.balance() == starting_balance_of_account + balance_of_lottery
