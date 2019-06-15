from cbc_lmd.main import CompressedTree, Block

class Message:

    def __init__(self, sender, block: Block, latest_messages, prev_message: 'Message'=None):
        self.sender = sender
        self.block = block
        self.prev_message = prev_message
        self.latest_messages = dict()
        for val in latest_messages:
            self.latest_messages[val] = latest_messages[val]

        if prev_message is not None:
            self.message_height = prev_message.message_height + 1
        else:
            self.message_height = 0


class Validator:

    def __init__(self, name, genesis: Block, weight):
        self.name = name
        self.weight = weight
        self.tree = CompressedTree(genesis)
        self.justification = set()
        self.latest_messages = dict()
        self.own_message_at_height = dict()

    def see_message(self, message: Message) -> None:
        for val in message.latest_messages:
            prev_message = message.latest_messages[val]
            if prev_message not in self.justification:
                self.see_message(prev_message)
        self.justification.add(message)
        new_latest = False
        if message.sender not in self.latest_messages:
            self.latest_messages[message.sender] = message
            new_latest = True
        else:
            if message.message_height > self.latest_messages[message.sender].message_height:
                self.latest_messages[message.sender] = message
                new_latest = True
        
        # only add the message to the reduced tree if it is a new later message
        if new_latest:
            self.tree.add_new_latest_block(message.block, message.sender)

    def forkchoice(self) -> Block:
        return self.tree.find_head(self.weight).block

    def make_new_message(self) -> Message:
        block = Block(self.forkchoice())
        prev_message = self.latest_messages.get(self.name, None)
        message = Message(self.name, block, self.latest_messages, prev_message=prev_message)
        self.latest_messages[self.name] = message
        self.own_message_at_height[message.message_height] = message
        return message


class ValidatorSet:

    def __init__(self, num_validators, weight=None):
        # give all validators weight 1, by default
        if weight is None:
            weight = {v : 1 for v in range(num_validators)}
        self.weight = weight
        self.genesis = Block(None)
        self.validators = dict()
        for name in range(num_validators):
            val = Validator(name, self.genesis, weight)
            self.validators[name] = val

    def make_new_message(self, name):
        return self.validators[name].make_new_message()

    def send_message(self, message, name):
        self.validators[name].see_message(message)

    def __iter__(self):
        self.n = 0
        return self

    def __next__(self):
        if self.n < len(self.validators):
            val = self.validators[self.n]
            self.n += 1
            return val
        else:
            raise StopIteration


class BoundryStore:

    def __init__(self, validator_set, block, q): 
        self.validator_set = validator_set
        self.block = block
        self.q = q
        self.layers = self.build_all_layers()

    def build_first_layer(self):
        layer = dict()

        for val in self.validator_set:
            prev_agreeing_message = None

            for i in range(len(val.own_message_at_height) - 1, -1, -1):
                message_at_height = val.own_message_at_height[i]
                if message_at_height.block.on_top(self.block):
                    prev_agreeing_message = message_at_height
                else:
                    break
            
            if prev_agreeing_message is not None:
                layer[val] = message_at_height

        return layer

    def build_next_layer(self, prev_layer):
        layer = dict()

        for val in prev_layer:
            prev_layer_boundry_height = prev_layer[val].message_height
            for i in range(prev_layer_boundry_height, len(val.own_message_at_height)):
                # see how many messages it acknowledges in the previous layer!
                total_weight = 0
                message_at_height = val.own_message_at_height[i]
                for other_val in prev_layer:
                    prev_layer_boundry = prev_layer[other_val] # must be defined, as is in V
                    if other_val.name not in message_at_height.latest_messages:
                        continue
                    if message_at_height.latest_messages[other_val.name].message_height >= prev_layer_boundry.message_height:
                        total_weight += self.validator_set.weight[other_val.name]
                if total_weight >= self.q:
                    layer[val] = message_at_height
                    break
                    
        return layer


    def build_all_layers(self):
        layer = dict()
        layer[0] = self.build_first_layer()

        prev_layer_height = 0
        while any(layer[prev_layer_height]):
            layer[prev_layer_height + 1] = self.build_next_layer(layer[prev_layer_height])
            prev_layer_height += 1

        return layer
        

