class CLS:
    def __init__(self):
        # item -> (add_count, remove_count)
        self._entries = {}

    def add(self, item):
        add_count, remove_count = self._entries.get(item, (0, 0))
        self._entries[item] = (add_count + 1, remove_count)

    def remove(self, item):
        add_count, remove_count = self._entries.get(item, (0, 0))
        if add_count > remove_count:
            # remove by setting remove_count = add_count (causal length)
            self._entries[item] = (add_count, add_count)

    def contains(self, item):
        add_count, remove_count = self._entries.get(item, (0, 0))
        return add_count > remove_count

    def _merge(self, other_entries):
        for item, (other_add, other_remove) in other_entries.items():
            add_count, remove_count = self._entries.get(item, (0, 0))
            self._entries[item] = (max(add_count, other_add), max(remove_count, other_remove))

    def mutual_sync(self, peers):
        for peer in peers:
            merged = {}
            for item in set(self._entries) | set(peer._entries):
                add_count, remove_count = self._entries.get(item, (0, 0))
                peer_add, peer_remove = peer._entries.get(item, (0, 0))
                merged[item] = (max(add_count, peer_add), max(remove_count, peer_remove))
            self._entries = merged
            peer._entries = dict(merged)


if __name__ == '__main__':
    alice_list = CLS()
    bob_list = CLS()

    alice_list.add('Milk')
    alice_list.add('Potato')
    alice_list.add('Eggs')

    bob_list.add('Sausage')
    bob_list.add('Mustard')
    bob_list.add('Coke')
    bob_list.add('Potato')
    bob_list.mutual_sync([alice_list])

    alice_list.remove('Sausage')
    alice_list.add('Tofu')
    alice_list.remove('Potato')
    alice_list.mutual_sync([bob_list])

    print("Bob's list contains 'Potato' ?", bob_list.contains('Potato'))

    # assert expected results
    assert not bob_list.contains('Potato'), "Potato should be removed"
    assert bob_list.contains('Milk')
    assert bob_list.contains('Eggs')
    assert not bob_list.contains('Sausage'), "Sausage should be removed"
    assert bob_list.contains('Tofu')
    assert bob_list.contains('Mustard')
    assert bob_list.contains('Coke')
    print("All assertions passed.")
