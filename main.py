import math


class Block:
    def __init__(self, parent_block):
        self.parent_block = parent_block
        if self.parent_block is None:
            self.height = 0
        else:
            self.height = self.parent_block.height + 1
        self.skip_list = [None] * 32

        # build the skip list
        for i in range(32):
            if i == 0:
                self.skip_list[0] = parent_block
            else:
                if self.skip_list[i - 1] is not None:
                    self.skip_list[i] = self.skip_list[i - 1].skip_list[i - 1]

    def prev_at_height(self, height):
        if height > self.height:
            print("Height: {}; Self height: {}".format(height, self.height))
            raise AssertionError("Fuuuuuck 3.0")
        elif height == self.height:
            return self
        else:
            # find the block with the lowest height above that height
            # that is also in the skip list
            diff = self.height - height
            # find the exponent of the smallest power of two
            pow_of_two = int(math.log(diff, 2))
            return self.skip_list[pow_of_two].prev_at_height(height)


class Node:
    def __init__(self, block, parent, is_latest, score=0, children=None):
        if children is None:
            self.children = set()
        else:
            self.children = children
        self.block = block
        self.parent = parent
        self.is_latest = is_latest
        self.score = score

    def size(self):
        size = 1
        for child in self.children:
            size += child.size()
        return size


class CompressedTree:
    def __init__(self, genesis):
        node = Node(genesis, None, True)
        self.root = node
        self.latest_block_nodes = dict()

    def block_in_tree(self, block):
        def block_below_node(block, node):
            if node.block == block:
                return True
            for child in node.children:
                if block_below_node(block, child):
                    return True
            return False
        return block_below_node(block, self.root)

    def node_with_block(self, block, node):
        if node.block == block:
            return node
        for child in node.children:
            node = self.node_with_block(block, child)
            if node is not None:
                return node
        return None

    def find_prev_in_tree(self, block):
        curr = block
        while not self.block_in_tree(curr):
            curr = curr.parent_block
        return self.node_with_block(curr, self.root)

    def find_lca_block(self, block_1, block_2):
        min_height = min(block_1.height, block_2.height)
        block_1 = block_1.prev_at_height(min_height)
        block_2 = block_2.prev_at_height(min_height)

        if block_1 == block_2:
            return block_1

        for i in range(32):
            if block_1.skip_list[i] == block_2.skip_list[i]:
                # i - 1 is the last height that these blocks have different ancestor
                # that are in the skip list
                if i == 0:
                    return block_1.parent_block
                else:
                    return self.find_lca_block(block_1.skip_list[i - 1], block_2.skip_list[i - 1])

    def add_new_latest_block(self, block, validator):
        new_node = self.add_block(block)

        if validator in self.latest_block_nodes:
            old_node = self.latest_block_nodes[validator]
            self.remove_node(old_node)

        self.latest_block_nodes[validator] = new_node
        return new_node

    def add_block(self, block):
        prev_in_tree = self.find_prev_in_tree(block)
        if len(prev_in_tree.children) == 0:
            node = Node(block, prev_in_tree, is_latest=True)
            prev_in_tree.children.add(node)
            return node
        for child in prev_in_tree.children:
            ancestor = self.find_lca_block(block, child.block)
            if ancestor != prev_in_tree.block:
                # haven't made the ancestor node, yet
                node = Node(block, None, is_latest=True)
                anc_node = Node(ancestor, prev_in_tree, children={node, child}, is_latest=False)
                # update the node's parent pointer
                node.parent = anc_node
                prev_in_tree.children.add(anc_node)
                prev_in_tree.children.remove(child)
                return node
        # insert on the prev_in_tree
        node = Node(block, prev_in_tree, True)
        prev_in_tree.children.add(node)
        return node

    def size(self):
        return self.root.size()

    def remove_node(self, node):
        num_children = len(node.children)
        if num_children > 1:
            node.is_latest = False
        elif num_children == 1:
            child = node.children.pop()
            child.parent = node.parent
            node.parent.children.remove(node)
            node.parent.children.add(child)
            del(node)
        else:
            parent = node.parent
            parent.children.remove(node)
            del(node)
            if not parent.is_latest and len(parent.children) == 1:
                par_child = parent.children.pop()
                par_child.parent = parent.parent
                parent.parent.children.remove(parent)
                parent.parent.children.add(par_child)
                del(parent)

    def delete_non_subtree(self, new_finalised, node):
        if node == new_finalised:
            return
        else:
            children = node.children
            for child in children:
                self.delete_non_subtree(new_finalised, child)

    def prune(self, new_finalised):
        new_finalised.parent = None
        self.delete_non_subtree(new_finalised, self.root)
        self.root = new_finalised


# Some light tests

def test_inserting_on_genesis():
    genesis = Block(None)
    tree = CompressedTree(genesis)

    block = Block(genesis)
    node = tree.add_new_latest_block(block, 0)

    assert tree.size() == 2
    assert tree.root.block == genesis
    assert tree.root.children.pop() == node


def test_inserting_on_leaf():
    genesis = Block(None)
    tree = CompressedTree(genesis)

    block_1 = Block(genesis)
    _ = tree.add_new_latest_block(block_1, 0)

    block_2 = Block(block_1)
    node_2 = tree.add_new_latest_block(block_2, 0)

    assert tree.size() == 2
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

    assert tree.size() == 4
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

    assert tree.size() == 5


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
    # SETUP
    genesis = Block(None)
    tree = CompressedTree(genesis)

    for i in range(3):
        block = Block(genesis)
        _ = tree.add_new_latest_block(block, i)

    val_0_block = tree.latest_block_nodes[0].block
    for i in range(3):
        block = Block(val_0_block)
        _ = tree.add_new_latest_block(block, i)

    assert tree.size() == 5

    # Test Pruning
    new_root = tree.node_with_block(val_0_block, tree.root)
    tree.prune(new_root)
    assert tree.size() == 4


if __name__ == "__main__":
    print("Running tests...")
    test_inserting_on_genesis()
    test_inserting_on_leaf()
    test_inserting_on_intermediate()
    test_vals_add_on_other_blocks()
    test_new_finalised_node_pruning()
    test_height()
    test_skip_list()
    test_prev_at_height()
    print("All tests passed!")
