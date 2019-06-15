import random
from cbc_lmd.main import (
    Block,
    CompressedTree,
)
from cbc_lmd.message import (
    BoundryStore,
    ValidatorSet
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
    new_root = tree.node_with_block[val_0_block]
    tree.prune(new_root)
    assert tree.size == 4


def test_ghost():
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

    val_0_block = tree.latest_block_nodes[0].block
    # Giving this block more weight, gives GHOST determanism
    b = Block(val_0_block)
    head_node = tree.add_new_latest_block(b, 0)
    weight = {b: 2}
    assert head_node == tree.find_head(weight)


def test_path_block_to_child_node():
    genesis = Block(None)
    tree = CompressedTree(genesis)

    block_1 = Block(genesis)
    node_1 = tree.add_new_latest_block(block_1, 0)

    assert tree.path_block_to_child_node[block_1] == node_1
    assert len(tree.path_block_to_child_node) == 1

    block_2 = Block(block_1)
    node_2 = tree.add_new_latest_block(block_2, 0)

    assert tree.path_block_to_child_node[block_1] == node_2
    assert len(tree.path_block_to_child_node) == 1

    on_inter_block = Block(block_1)
    on_inter_node = tree.add_new_latest_block(on_inter_block, 1)

    assert tree.path_block_to_child_node[block_1].block == block_1  # node_1 was deleted, so it's a dif node
    assert tree.path_block_to_child_node[block_2] == node_2
    assert tree.path_block_to_child_node[on_inter_block] == on_inter_node
    assert len(tree.path_block_to_child_node) == 3


def test_delete_with_child():
    genesis = Block(None)
    tree = CompressedTree(genesis)

    block_1_val_0 = Block(genesis)
    _ = tree.add_new_latest_block(block_1_val_0, 0)

    block_2_val_0 = Block(block_1_val_0)
    _ = tree.add_new_latest_block(block_2_val_0, 0)

    block_1_val_1 = Block(block_1_val_0)
    _ = tree.add_new_latest_block(block_1_val_1, 1)

    block_1_val_2 = Block(genesis)
    _ = tree.add_new_latest_block(block_1_val_2, 2)

    block_3_val_0 = Block(block_1_val_2)
    _ = tree.add_new_latest_block(block_3_val_0, 0)

    assert tree.size == 4
    assert len(tree.root.children) == 2
    assert tree.latest_block_nodes[1] in tree.root.children
    assert tree.latest_block_nodes[2] in tree.root.children
    assert tree.latest_block_nodes[0] not in tree.root.children

def test_add_not_on_root():
    genesis = Block(None)
    tree = CompressedTree(genesis)

    block = Block(None)
    node = tree.add_new_latest_block(block, 0)

    assert node is None

    block = Block(genesis)
    node = tree.add_new_latest_block(block, 0)
    
    assert tree.root.children.pop() == node
    assert node.block == block


def test_find_prev_in_tree():
    genesis = Block(None)
    tree = CompressedTree(genesis)

    block = Block(None)
    assert None is tree.find_prev_node_in_tree(block)

    block = Block(genesis)
    assert tree.root is tree.find_prev_node_in_tree(block)

    for i in range(3):
        block = Block(genesis)
        _ = tree.add_new_latest_block(block, i)

    block_1 = Block(tree.latest_block_nodes[2].block)
    assert block_1.parent_block == tree.find_prev_node_in_tree(block_1).block
    tree.add_new_latest_block(block_1, 2)
    assert block_1 == tree.latest_block_nodes[2].block

    block_2 = Block(tree.latest_block_nodes[2].block)
    assert block_2.parent_block == tree.find_prev_node_in_tree(block_2).block

def test_random():

    genesis = Block(None)
    tree = CompressedTree(genesis)

    for i in range(3):
        block = Block(genesis)
        _ = tree.add_new_latest_block(block, i)

    new_block = Block(tree.latest_block_nodes[1].block)
    tree.add_new_latest_block(new_block, 1)

    new_block = Block(tree.latest_block_nodes[1].block)
    tree.add_new_latest_block(new_block, 1)

def test_massive_tree():
    genesis = Block(None)
    tree = CompressedTree(genesis)

    for i in range(3):
        block = Block(genesis)
        _ = tree.add_new_latest_block(block, i)

    for i in range(1000):
        print(i)
        prev_val = random.randint(0, 2)
        new_block = Block(tree.latest_block_nodes[prev_val].block)
        new_val = random.randint(0, 2)
        tree.add_new_latest_block(new_block, new_val)
        assert tree.size <= 6

    block = tree.latest_block_nodes[2].block 
    assert tree.find_head({block: 1}).block.prev_at_height(block.height) == block


def test_make_val_set():
    val_set = ValidatorSet(3)
    assert len(val_set.validators) == 3
    for val in val_set:
        assert val.tree.root.block == val_set.genesis


def test_make_new_message():
    val_set = ValidatorSet(3)
    message = val_set.make_new_message(0)
    assert message.block.parent_block == val_set.genesis
    assert val_set.validators[0].latest_messages[0] == message

def test_make_new_messages():
    val_set = ValidatorSet(3)
    
    last_message = None
    for i in range(100):
        last_message = val_set.make_new_message(0)

    for val in val_set:
        val.see_message(last_message)
        assert val.latest_messages[0] == last_message
        assert len(val.justification) == 100

def test_make_new_messages_on_eachothers():
    val_set = ValidatorSet(3)
    
    for i in range(100):
        latest = set()
        for val in val_set:
            latest.add(val.make_new_message())
        for val in val_set:
            for m in latest:
                val.see_message(m)
        
        for val in val_set:
            for i in range(3):
                assert val.latest_messages[i] in latest

def test_build_graph_basic():
    val_set = ValidatorSet(3)

    latest = set()
    for val in val_set:
        latest.add(val.make_new_message())
    
    for m in latest:
        for val in val_set:
            val.see_message(m)

    boundry_store = BoundryStore(val_set, val_set.genesis, 1)
    for val in boundry_store.layers[0]:
        assert boundry_store.layers[0][val] in latest

def test_build_graph_two_layers():
    val_set = ValidatorSet(3)

    zero = set()
    for val in val_set:
        zero.add(val.make_new_message())

    for val in val_set:
        for m in zero:
            val.see_message(m)

    one = set()
    for val in val_set:
        one.add(val.make_new_message())

    boundry_store = BoundryStore(val_set, val_set.genesis, 1)
    for val in boundry_store.layers[1]:
        assert boundry_store.layers[1][val] in one
    for val in boundry_store.layers[0]:
        assert boundry_store.layers[0][val] in zero