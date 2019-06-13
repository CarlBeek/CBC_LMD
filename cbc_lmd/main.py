import math
from blist import sortedset
from typing import (
    Dict,
    List,
    Optional,
    Set,
)


SKIP_LENGTH = 32


class Block:
    height = 0
    skip_list = []  # type: List[Optional[Block]]
    parent_block = None  # type: Block
    weight = 0

    def __init__(self, parent_block: Optional['Block']=None, weight: int=0) -> None:
        if parent_block is not None:
            self.parent_block = parent_block
            self.height = self.parent_block.height + 1
        else:
            self.height = 0

        self.weight = weight
        
        self.skip_list = [None] * SKIP_LENGTH
        # build the skip list
        for i in range(SKIP_LENGTH):
            if i == 0:
                self.skip_list[0] = parent_block
            else:
                block = self.skip_list[i - 1]
                if block is not None:
                    self.skip_list[i] = block.skip_list[i - 1]

    def prev_at_height(self, height: int) -> 'Block':
        if height > self.height:
            raise AssertionError("Fuuuuuck 3.0")
        elif height == self.height:
            return self
        else:
            # find the block with the lowest height above that height
            # that is also in the skip list
            diff = self.height - height
            # find the exponent of the smallest power of two
            pow_of_two = int(math.log(diff, 2))
            block = self.skip_list[pow_of_two]
            if block is not None:
                return block.prev_at_height(height)
            else:
                raise AssertionError("Fuuuuuck 4.0")


class Node:
    parent = None  # type: Optional[Node]

    def __init__(self,
                 block: Block,
                 parent: Optional['Node'],
                 is_latest: bool,
                 score: int=0,
                 children: Set['Node']=None) -> None:
        if children is None:
            self.children = set()  # type: Set[Node]
        else:
            self.children = children
        self.block = block
        if parent is not None:
            self.parent = parent
        self.is_latest = is_latest
        self.score = score

    @property
    def size(self) -> int:
        size = 1
        for child in self.children:
            size += child.size
        return size


class CompressedTree:
    def __init__(self, genesis: Block):
        self.latest_block_nodes = dict()  # type: Dict[int, Node]
        self.nodes_at_height = dict()  # type: Dict[int, Set[Node]]
        self.heights = sortedset()
        self.root = self.add_tree_node(genesis, None, True)

    def node_with_block(self, block: Block, nodes: Set[Node]) -> Optional[Node]:
        for node in nodes:
            if block == node.block:
                return node
        return None

    def find_prev_in_tree_with_heights(self, block: Block, heights: List[int], lo: int, hi: int) -> Optional[Node]:
        if hi <= lo:
            raise Exception("Fuuuuuck 4.0")

        mid_idx = int((lo + hi) / 2)
        mid_height = heights[mid_idx]
        block_at_mid = block.prev_at_height(mid_height)
        node_at_mid = self.node_with_block(block_at_mid, self.nodes_at_height[mid_height])
        if node_at_mid is not None:
            if mid_idx + 1 >= len(heights):
                return node_at_mid

            mid_height_next = heights[mid_idx + 1]
            if self.node_with_block(block_at_mid, self.nodes_at_height[mid_height_next]) is None:
                return node_at_mid
            else:
                return self.find_prev_in_tree_with_heights(block, heights, mid_idx + 1, hi)
        else:
            return self.find_prev_in_tree_with_heights(block, heights, lo, mid_idx)

    def find_prev_in_tree(self, block: Block) -> Optional[Node]:
        return self.find_prev_in_tree_with_heights(block, self.heights, 0, len(self.heights))

    def find_lca_block(self, block_1: Block, block_2: Block) -> Block:
        min_height = min(block_1.height, block_2.height)
        block_1 = block_1.prev_at_height(min_height)
        block_2 = block_2.prev_at_height(min_height)

        if block_1 == block_2:
            return block_1

        for i in range(SKIP_LENGTH):
            if block_1.skip_list[i] == block_2.skip_list[i]:
                # i - 1 is the last height that these blocks have different ancestor
                # that are in the skip list
                if i == 0:
                    return block_1.parent_block
                else:
                    block_a = block_1.skip_list[i - 1]
                    block_b = block_2.skip_list[i - 1]
                    if block_a is not None and block_b is not None:
                        return self.find_lca_block(block_a, block_b)

        raise Exception("Fuuuuuck 5.0: No LCA")

    def add_new_latest_block(self, block: Block, validator: int) -> Node:
        new_node = self.add_block(block)

        if validator in self.latest_block_nodes:
            old_node = self.latest_block_nodes[validator]
            self.remove_node(old_node)

        self.latest_block_nodes[validator] = new_node
        return new_node

    def add_block(self, block: Block) -> Node:
        prev_in_tree = self.find_prev_in_tree(block)
        # above prev in tree
        # above_prev_in_tree = block.prev_at_height(prev_in_tree + 1) -- vlad's optimization

        if prev_in_tree is None:
            raise Exception("Really shouldn't be")
        # check if there is path overlap with any children currently in the tree
        for child in prev_in_tree.children:
            ancestor = self.find_lca_block(block, child.block)
            if ancestor != prev_in_tree.block:
                # haven't made the ancestor node, so parent node is not defined tet
                node = self.add_tree_node(block=block, parent=None, is_latest=True)
                anc_node = self.add_tree_node(
                    block=ancestor,
                    parent=prev_in_tree,
                    children={node, child},
                    is_latest=False)
                # update the node's parent pointer
                node.parent = anc_node
                prev_in_tree.children.remove(child)
                return node
        # insert on the prev_in_tree
        return self.add_tree_node(block=block, parent=prev_in_tree, is_latest=True)

    def add_tree_node(self, block: Block, parent: Optional[Node], is_latest: bool, children: Set[Node]=None) -> Node:
        # create the node
        node = Node(block, parent, is_latest, children=children)
        # make it a child
        if parent is not None:
            parent.children.add(node)
        # save it as a node at that height
        height = node.block.height
        if height not in self.nodes_at_height:
            self.nodes_at_height[height] = set()
            self.heights.add(height)
        self.nodes_at_height[height].add(node)
        # return the new node
        return node

    @property
    def size(self) -> int:
        return self.root.size

    def all_nodes(self) -> Set[Node]:
        all_nodes = set()  # type: Set[Node]
        for s in self.nodes_at_height.values():
            all_nodes.update(s)
        return all_nodes

    def remove_node(self, node: Node) -> None:
        def del_node(node: Node) -> None:
            assert len(node.children) <= 1  # cannot remove a node with more than one child
            child = node.children.pop()
            child.parent = node.parent

            if node.parent is not None:
                node.parent.children.remove(node)
                node.parent.children.add(child)
                self.nodes_at_height[node.block.height].remove(node)
                # only keep heights that have nodes in them
                if not any(self.nodes_at_height[node.block.height]):
                    del self.nodes_at_height[node.block.height]
                    self.heights.remove(node.block.height)
                del(node)

        num_children = len(node.children)
        if num_children > 1:
            node.is_latest = False
        elif num_children == 1:
            del_node(node)
        else:
            parent = node.parent
            if parent is not None:
                parent.children.remove(node)
                del(node)
                if not parent.is_latest and len(parent.children) == 1:
                    del_node(parent)

    def delete_non_subtree(self, new_finalised: Node, node: Node) -> None:
        if node == new_finalised:
            return
        else:
            children = node.children
            for child in children:
                self.delete_non_subtree(new_finalised, child)

    def prune(self, new_finalised: Node) -> None:
        new_finalised.parent = None
        self.delete_non_subtree(new_finalised, self.root)
        self.root = new_finalised

    def find_head(self) -> Optional[Node]:
        # calculate the scores of every node starting at the leaves
        for height in sorted(self.nodes_at_height, reverse=True):
            for node in self.nodes_at_height[height]:
                node.score = sum(child.score for child in node.children)
                node.score += node.block.weight if node.is_latest else 0
        # run GHOST
        node = self.root
        while len(node.children) > 0:
            node = sorted(node.children, key=lambda x: x.score, reverse=True)[0]
        return node
