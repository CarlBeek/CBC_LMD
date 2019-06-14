import math
from blist import sortedset
from typing import (
    List,
    Optional,
    Set,
    Dict,
)


SKIP_LENGTH = 32


class Block:
    height = 0
    skip_list = []  # type: List[Optional[Block]]
    parent_block = None  # type: Block

    def __init__(self, parent_block: Optional['Block']=None) -> None:
        if parent_block is not None:
            self.parent_block = parent_block
            self.height = self.parent_block.height + 1
        else:
            self.height = 0

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
            raise Exception("Block {} at height {} has no prev block at height {}".format(self, self.height, height))
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
                raise Exception("Skip list error")


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
    
    @property
    def is_leaf(self) -> bool:
        return not any(self.children)

    def nodes_in_subtree(self) -> Set['Node']:
        nodes = {self}
        for child in self.children:
            nodes.update(child.nodes_in_subtree())
        return nodes


class CompressedTree:
    def __init__(self, genesis: Block):
        self.latest_block_nodes = dict() # type: Dict[int, Node]
        self.blocks_at_height = dict() # type: Dict[int, Set[Node]]
        self.node_with_block = dict() # type: Dict[Block, Node]
        self.heights = sortedset(key = lambda x: -x) # store from largest -> smallest
        self.path_block_to_child_node = dict() # type: Dict[Block, Node]
        self.root = self.add_tree_node(genesis, None, True)

    # TODO: can this function be in a subclass? I'm thinking that we have an LMD tree...
    # and then we can also do an IMD tree, or something... but we might not get
    # efficiency gains here 
    def add_new_latest_block(self, block: Block, validator: int) -> Node:
        # remove the validators last message, if they have one
        if validator in self.latest_block_nodes and self.latest_block_nodes[validator]:
            old_node = self.latest_block_nodes[validator]
            self.remove_node(old_node)
        # add the validators new message, and save it
        new_node = self.add_block_with_weight(block)
        self.latest_block_nodes[validator] = new_node
        return new_node

    def add_block_with_weight(self, block: Block) -> Node:
        # node in tree that is the most recent ancestor of block
        prev_node_in_tree = self.find_prev_node_in_tree(block)
        if prev_node_in_tree is None:
            # the block being added is not built on top the current root, so we don't need to add it
            return None

        # the child of prev_node_in_tree.block that is on the path to block
        path_block = block.prev_at_height(prev_node_in_tree.block.height + 1)

        # if this path_block points to a child, then the block has path overlap 
        # with some child of prev_node_in_tree
        if path_block in self.path_block_to_child_node:
            path_overlap_child = self.path_block_to_child_node[path_block]
            block_and_child_lca = self.find_lca_block(block, path_overlap_child.block)

            assert block_and_child_lca != prev_node_in_tree.block # if this was true, there would be no path overlap!

            anc_node = self.add_tree_node(
                block=block_and_child_lca,
                parent=prev_node_in_tree,
                children={path_overlap_child}, # missing node with new block, as not created yet
                has_weight=False
            )

            node = self.add_tree_node(block=block, parent=anc_node, has_weight=True)

            # update the path_overlap_child to have correct parent and path pointers
            path_overlap_child.parent = anc_node
            child_path_block = path_overlap_child.block.prev_at_height(block_and_child_lca.height + 1)
            self.path_block_to_child_node[child_path_block] = path_overlap_child

            # children of the prev_node_in_tree should not have old child anymore (it is a child of anc_node)
            prev_node_in_tree.children.remove(path_overlap_child)

            return node
        else:
            # there is no path overlap between the the block and any child of prev_node_in tree
            # (which might be because the prev_node_in_tree is a leaf and so has no children)
            node = self.add_tree_node(
                block=block, 
                parent=prev_node_in_tree, 
                has_weight=True
            )
            return node

    def add_tree_node(self, block: Block, parent: Node, has_weight: bool, children:Set[Node]=None) -> Node:
        node = Node(block, parent, has_weight, children=children)
        self.node_with_block[block] = node

        if parent is not None:
            # add it as a child of its parent
            parent.children.add(node)
            # point to it with a path_block
            path_block = block.prev_at_height(parent.block.height + 1)
            self.path_block_to_child_node[path_block] = node

        # save it as a node at that height
        height = node.block.height
        if height not in self.blocks_at_height:
            self.blocks_at_height[height] = set()
            self.heights.add(height)
        self.blocks_at_height[height].add(block)
        # return the new node
        return node

    def find_prev_node_in_tree(self, block: Block) -> Optional[Node]:
        for height in self.heights:
            # self.heights is in decreasing order
            if height <= block.height:
                prev_at_height = block.prev_at_height(height)
                if prev_at_height in self.blocks_at_height[height]:
                    # have to get block at that height
                    return self.node_with_block[prev_at_height]
        # The block has no previous block in the tree
        return None

    """
    # NOTE: this method is broken. It assumes that if some block has a previous^n node in the 
    # tree at height h, then it has a node in the tree at all heights less than h that are in
    # in the tree. But this is not the case... so the method does not work!
    def find_prev_in_tree_with_heights(self, block: Block, heights: List[int], lo: int, hi: int) -> Optional[Node]:
        if hi <= lo:
            # TODO: figure out if this should just be less than...
            return None

        mid_idx = int((lo + hi) / 2)
        mid_height = heights[mid_idx]
        block_at_mid = block.prev_at_height(mid_height)
        #node_at_mid = self.node_with_block(block_at_mid, self.nodes_at_height[mid_height])
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
    """

    def remove_node(self, node: Node) -> None:
        def del_node_no_child(node: Node) -> None:
            assert node.is_leaf

            node.parent.children.remove(node)
            self.blocks_at_height[node.block.height].remove(node.block)
            # only keep heights that have nodes in them
            if not any(self.blocks_at_height[node.block.height]):
                del self.blocks_at_height[node.block.height]
                self.heights.remove(node.block.height)

            # update the path_block_to_child_node map
            # which will only exist, if a node's block points to itself...
            if node.block in self.path_block_to_child_node:
                assert self.path_block_to_child_node[node.block] == node
                del self.path_block_to_child_node[node.block]

            # delete the node
            del(self.node_with_block[node.block])
            del(node)

        def del_node_with_child(node: Node) -> None:
            # connects the single child to the parent
            assert len(node.children) == 1

            # connect child to new parent
            child = node.children.pop()
            child.parent = node.parent
            node.parent.children.add(child)

            # update the path_block_to_child_node map
            next_block = node.block.prev_at_height(node.parent.block.height + 1)
            assert self.path_block_to_child_node[next_block] == node
            self.path_block_to_child_node[next_block] = child

            # cleanup
            node.parent.children.remove(node)
            self.blocks_at_height[node.block.height].remove(node.block)
            # only keep heights that have nodes in them
            if not any(self.blocks_at_height[node.block.height]):
                del self.blocks_at_height[node.block.height]
                self.heights.remove(node.block.height)

            del(self.node_with_block[node.block])
            del(node)

        num_children = len(node.children)

        if num_children > 1:
            # internal node
            node.has_weight = False
        elif num_children == 1:
            # node has a single child
            del_node_with_child(node)
        else:
            # node is a leaf, so it can be removed
            parent = node.parent
            del_node_no_child(node)
            # if it's parent has no weight, and has only one child, it can be deleted too
            if not parent.has_weight and len(parent.children) == 1:
                del_node_with_child(parent)

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

    @property
    def size(self) -> int:
        return self.root.size

    def all_nodes(self) -> Set[Node]:
        return self.root.nodes_in_subtree()

    def delete_non_subtree(self, new_finalised: Node, node: Node) -> None:
        if node != new_finalised:
            for child in node.children:
                self.delete_non_subtree(new_finalised, child)
                # TODO: actually delete the node, updating the cached things properly!

    def prune(self, new_finalised: Node) -> None:
        new_finalised.parent = None
        self.delete_non_subtree(new_finalised, self.root)
        self.root = new_finalised

    def calculate_scores(self, node: Node, weight: Dict[Block, int], score: Dict[Node, int]) -> Dict[Block, int]:
        if not any(node.children):
            score[node] = weight.get(node.block, 0)
        else:
            score[node] = weight.get(node.block, 0)
            for child in node.children:
                self.calculate_scores(child, weight, score)
                score[node] += score[child]
        return score

    def find_head(self, weight: Dict[Block, int]) -> Node:
        # calculate the score for each block
        scores = self.calculate_scores(self.root, weight, dict())

        # run GHOST
        node = self.root
        while len(node.children) > 0:
            node = sorted(node.children, key=lambda n: scores.get(n, 0), reverse=True)[0]
        return node

