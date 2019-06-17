from visualisations.tree_visualiser import hierarchy_pos
import matplotlib.pyplot as plt
import random
import time
import networkx as nx
from cbc_lmd.main import (
    Block,
    CompressedTree,
)


def extract_tree(c_tree: CompressedTree) -> nx.Graph:
    G = nx.Graph()
    connections = list()
    nodes = c_tree.all_nodes()

    for node in nodes:
        name = node.block.name
        p_name = node.parent.block.name if node.parent is not None and node.parent != '' else 0
        if node.parent is None:
            continue
        if node.block.name == node.parent.block.name:
            continue

        connections.append(((name, p_name)))
    print(connections)
    G.add_edges_from(connections)
    return G


def draw_tree(G: nx.Graph, name: str='tree.png'):
    pos = hierarchy_pos(G, 1)
    nx.draw(G, pos=pos, with_labels=True)
    plt.savefig(name)
    plt.clf()


def build_full_tree(blocks):
    G = nx.Graph()
    connections = list()
    for name, block in enumerate(blocks):
        block.name = name  
        if block.parent_block is None:
            continue
        if block.parent_block.name == block.name:
            continue
        adding = (block.name, block.parent_block.name)
        connections.append((block.name, block.parent_block.name))
    print(connections)
    G.add_edges_from(connections)
    return G


if __name__ == '__main__':
    genesis = Block(None)
    genesis.name = 1
    tree = CompressedTree(genesis)
    blocks = []

    for i in range(5):
        block = Block(genesis)
        blocks.append(block)
        _ = tree.add_new_latest_block(block, i)

    for i in range(25):
        prev_val = random.randint(0, 4)
        new_block = Block(tree.latest_block_nodes[prev_val].block)
        new_val = random.randint(0, 4)
        blocks.append(new_block)
        tree.add_new_latest_block(new_block, new_val)
        assert tree.size <= 10
        print("RUNNING {}".format(i))

        G_compressed = extract_tree(tree)
        draw_tree(G_compressed, 'temp/compresssed_tree' + str(i) + '.png')

        G_full = build_full_tree(blocks)
        draw_tree(G_full, 'temp/full_tree' + str(i) + '.png')

    

