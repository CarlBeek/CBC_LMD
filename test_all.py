import pytest


from cbc_lmd.main import (
    Block,
    CompressedTree,
)


def test_inserting_on_genesis():
    genesis = Block(None)
    tree = CompressedTree(genesis)

    block = Block(genesis)
    node = tree.add_new_latest_block(block, 0)

    assert tree.size == 2
    assert tree.root.block == genesis
    assert tree.root.children.pop() == node


def test_inserting_on_leaf():
    genesis = Block(None)
    tree = CompressedTree(genesis)

    block_1 = Block(genesis)
    _ = tree.add_new_latest_block(block_1, 0)

    block_2 = Block(block_1)
    node_2 = tree.add_new_latest_block(block_2, 0)

    assert tree.size == 2
    assert tree.root.block == genesis
    assert tree.root.children.pop() == node_2


def test_inserting_on_intermediate():
    genesis = Block(None)
    tree = CompressedTree(genesis)

    block_1 = Block(genesis)
    _ = tree.add_new_latest_block(block_1, 0)

    block_2 = Block(block_1)
    _ = tree.add_new_latest_block(block_2, 0)

    on_inter_block = Block(block_1)
    on_inter_node = tree.add_new_latest_block(on_inter_block, 1)

    assert tree.size == 4
    assert tree.root == on_inter_node.parent.parent


def test_vals_add_on_other_blocks():
    genesis = Block(None)
    tree = CompressedTree(genesis)

    for i in range(3):
        block = Block(genesis)
        _ = tree.add_new_latest_block(block, i)

    val_0_block = tree.latest_block_nodes[0].block
    for i in range(3):
        block = Block(val_0_block)
        _ = tree.add_new_latest_block(block, i)

    assert tree.size == 5


def test_height():
    genesis = Block(None)
    assert genesis.height == 0

    prev_block = genesis
    for _ in range(1024):
        block = Block(prev_block)
        assert block.height == prev_block.height + 1
        prev_block = block


def test_skip_list():
    blocks = []
    genesis = Block(None)
    blocks.append(genesis)

    prev_block = genesis
    for _ in range(1024):
        block = Block(prev_block)
        blocks.append(block)
        prev_block = block

    for block in blocks:
        height = block.height
        assert block == blocks[height]

        for idx, skip_block in enumerate(block.skip_list):
            if skip_block is None:
                assert height - 2**idx < 0
            else:
                assert skip_block.height == height - 2**idx


def test_prev_at_height():
    blocks = []
    genesis = Block(None)
    blocks.append(genesis)

    prev_block = genesis
    for i in range(256):
        block = Block(prev_block)
        blocks.append(block)
        prev_block = block

    for block in blocks:
        for i in range(block.height):
            at_height = block.prev_at_height(i)
            assert at_height == blocks[i]


def test_new_finalised_node_pruning():
    # Setup
    genesis = Block(None)
    tree = CompressedTree(genesis)

    for i in range(3):
        block = Block(genesis)
        _ = tree.add_new_latest_block(block, i)

    val_0_block = tree.latest_block_nodes[0].block
    for i in range(3):
        block = Block(val_0_block)
        _ = tree.add_new_latest_block(block, i)

    assert tree.size == 5

    # Test Pruning
    new_root = tree.node_with_block(val_0_block, tree.all_nodes())
    tree.prune(new_root)
    assert tree.size == 4


def test_ghost():
    # Setup
    genesis = Block(None)
    tree = CompressedTree(genesis)

    for i in range(3):
        block = Block(genesis, 1)
        _ = tree.add_new_latest_block(block, i)

    val_0_block = tree.latest_block_nodes[0].block
    for i in range(3):
        block = Block(val_0_block, 1)
        _ = tree.add_new_latest_block(block, i)

    val_0_block = tree.latest_block_nodes[0].block
    # Giving this block more weight, gives GHOST determanism
    head_node = tree.add_new_latest_block(Block(val_0_block, weight=2), 1)
    assert head_node == tree.find_head()


def test_next_block_to_child_node():
    genesis = Block(None)
    tree = CompressedTree(genesis)

    block_1 = Block(genesis)
    node_1 = tree.add_new_latest_block(block_1, 0)

    assert tree.next_block_to_child_node[block_1] == node_1
    assert len(tree.next_block_to_child_node) == 1

    block_2 = Block(block_1)
    node_2 = tree.add_new_latest_block(block_2, 0)

    assert tree.next_block_to_child_node[block_1] == node_2
    assert len(tree.next_block_to_child_node) == 1

    on_inter_block = Block(block_1)
    on_inter_node = tree.add_new_latest_block(on_inter_block, 1)

    assert tree.next_block_to_child_node[block_1].block == block_1 # node_1 was deleted, so it's a dif node
    assert tree.next_block_to_child_node[block_2] == node_2
    assert tree.next_block_to_child_node[on_inter_block] == on_inter_node
    assert len(tree.next_block_to_child_node) == 3
