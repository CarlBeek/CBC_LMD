from visualisations.tree_visualiser import hierarchy_pos
import matplotlib.pyplot as plt
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
        connections.append(((name, p_name)))
    print(connections)
    G.add_edges_from(connections)
    return G


def draw_tree(G: nx.Graph):
    pos = hierarchy_pos(G, 1)
    nx.draw(G, pos=pos, with_labels=True)
    plt.savefig('tree.png')


if __name__ == '__main__':
    genesis = Block(None)
    tree = CompressedTree(genesis)

    for i in range(16):
        block = Block(genesis)
        _ = tree.add_new_latest_block(block, i)

    on_inter_block = Block(block_1)
    on_inter_node = tree.add_new_latest_block(on_inter_block, 1)
    G = extract_tree(tree)
    draw_tree(G)
