import math
from blist import sortedset
from typing import (
    List,
    Optional,
    Set,
)
import random

SKIP_LENGTH = 32


class Block:
    height = 0
    skip_list = []  # type: List[Optional[Block]]
    parent_block = None  # type: Block

    def __init__(self, parent_block: Optional['Block']=None, name: Optional[int]=None) -> None:
        if parent_block is not None:
            self.parent_block = parent_block
            self.height = self.parent_block.height + 1
        else:
            self.height = 0

        self.name = -1 if name is None else name

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
    parent = None  # type: Node

    def __init__(self,
                 block: Block,
                 parent: Optional['Node'],
                 has_weight: bool,
                 children: Set['Node']=None) -> None:
        if children is None:
            self.children = set()  # type: Set[Node]
        else:
            self.children = children
        self.block = block
        if parent is not None:
            self.parent = parent
        self.has_weight = has_weight

    @property
    def size(self) -> int:
        size = 1
        for child in self.children:
            size += child.size
        return size


class CompressedTree:
    def __init__(self, genesis: Block):
        self.latest_block_nodes = dict()
        self.nodes_at_height = dict()
        self.heights = sortedset()
        self.next_block_to_child_node = dict()
        self.node_counter = 0
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
            if block.height < mid_height_next:
                return node_at_mid

            block_at_mid_next = block.prev_at_height(mid_height_next)
            if self.node_with_block(block_at_mid_next, self.nodes_at_height[mid_height_next]) is None:
                return node_at_mid
            else:
                return self.find_prev_in_tree_with_heights(block, heights, mid_idx + 1, hi)
        else:
            return self.find_prev_in_tree_with_heights(block, heights, lo, mid_idx)

    def find_prev_in_tree(self, block):
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
        if validator in self.latest_block_nodes:
            old_node = self.latest_block_nodes[validator]
            self.remove_node(old_node)
        new_node = self.add_block(block)
        self.latest_block_nodes[validator] = new_node
        return new_node

    def add_block(self, block: Block) -> Node:
        block.name = self.node_counter
        self.node_counter += 1
        prev_in_tree = self.find_prev_in_tree(block)
        # above prev in tree
        above_prev_in_tree = block.prev_at_height(prev_in_tree.block.height + 1)

        if prev_in_tree is None:
            raise Exception("Really shouldn't be")

        # check if there is path overlap with any children currently in the tree
        if len(prev_in_tree.children) == 0:
            return self.add_tree_node(block=block, parent=prev_in_tree, has_weight=True)

        if above_prev_in_tree in self.next_block_to_child_node:
            child = self.next_block_to_child_node[above_prev_in_tree]
            ancestor = self.find_lca_block(block, child.block)
            if ancestor != prev_in_tree.block:

                anc_node = self.add_tree_node(
                    block=ancestor,
                    parent=prev_in_tree,
                    children={child},
                    has_weight=False
                )

                child.parent = anc_node

                node = self.add_tree_node(block=block, parent=anc_node, has_weight=True)
                # add node as a child to ancestor node
                anc_node.children.add(node)
                # the child is now a child of anc_node, rather than prev_in_tree
                prev_in_tree.children.remove(child)
                # have to point the node below the child, but above anc, to the child
                above_anc = child.block.prev_at_height(ancestor.height + 1)
                self.next_block_to_child_node[above_anc] = child
                return node
        # insert on the prev_in_tree
        return self.add_tree_node(block=block, parent=prev_in_tree, has_weight=True)

    def add_tree_node(self, block, parent, has_weight, children=None):
        # create the node
        node = Node(block, parent, has_weight, children=children)
        # make it a child
        if parent is not None:
            parent.children.add(node)
            # save the next block in the next_block_to_child_node map
            next_block = block.prev_at_height(parent.block.height + 1)
            self.next_block_to_child_node[next_block] = node

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

    def all_nodes(self):
        all_nodes = set()
        for s in self.nodes_at_height.values():
            all_nodes.update(s)
        return all_nodes

    def remove_node(self, node: Node) -> None:
        def del_node_no_child(node):
            assert not any(node.children)

            node.parent.children.remove(node)
            self.nodes_at_height[node.block.height].remove(node)
            # only keep heights that have nodes in them
            if not any(self.nodes_at_height[node.block.height]):
                del self.nodes_at_height[node.block.height]
                self.heights.remove(node.block.height)

            # update the next_block_to_child_node map
            # which will only exist, if a node's block points to itself...
            if node.block in self.next_block_to_child_node:
                assert self.next_block_to_child_node[node.block] == node
                del self.next_block_to_child_node[node.block]

            # delete the node
            del(node)

        def del_node_with_child(node):
            # connects the single child to the parent
            assert len(node.children) == 1

            # connect child to new parent
            child = node.children.pop()
            child.parent = node.parent
            node.parent.children.add(child)

            # # update the next_block_to_child_node map
            next_block = node.block.prev_at_height(node.parent.block.height + 1)
            assert self.next_block_to_child_node[next_block] == node
            self.next_block_to_child_node[next_block] = child

            # cleanup
            node.parent.children.remove(node)
            self.nodes_at_height[node.block.height].remove(node)
            # only keep heights that have nodes in them
            if not any(self.nodes_at_height[node.block.height]):
                del self.nodes_at_height[node.block.height]
                self.heights.remove(node.block.height)

            del(node)

        num_children = len(node.children)

        if num_children > 1:
            node.has_weight = False
        elif num_children == 1:
            del_node_with_child(node)
        else:
            parent = node.parent
            del_node_no_child(node)
            if not parent.has_weight and len(parent.children) == 1:
                del_node_with_child(parent)

    def delete_non_subtree(self, new_finalised, node):
        if node != new_finalised:
            for child in node.children:
                self.delete_non_subtree(new_finalised, child)
                # TODO: actually delete the node

    def prune(self, new_finalised):
        new_finalised.parent = None
        self.delete_non_subtree(new_finalised, self.root)
        self.root = new_finalised

    def calculate_scores(self, node, weight, score):
        if not any(node.children):
            score[node] = weight.get(node.block, 0)
        else:
            score[node] = weight.get(node.block, 0)
            for child in node.children:
                self.calculate_scores(child, weight, score)
                score[node] += score[child]
        return score

    def find_head(self, weight) -> Node:
        # calculate the score for each block
        scores = self.calculate_scores(self.root, weight, dict())

        # run GHOST
        node = self.root
        while len(node.children) > 0:
            node = sorted(node.children, key=lambda n: scores.get(n, 0), reverse=True)[0]
        return node
