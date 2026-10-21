
class CLS():

    def __init__(self):
        self.ledger = {}
    
    def add(self, article: str):
        value = self.ledger.get(article, 0)
        if value % 2 == 0:
            self.ledger[article] = value + 1
    
    def remove(self, article: str):
        value = self.ledger.get(article, 0)
        if value % 2 == 1:
            self.ledger[article] = value + 1
    
    def contains(self, article: str):
        return self.ledger.get(article, 0) % 2 == 1
    
    def mutual_sync(self, others):
        replicas = [self] + others

        for article in set().union(*(r.ledger.keys() for r in replicas)):
            value = max(r.ledger.get(article, 0) for r in replicas)

            for r in replicas:
                r.ledger[article] = value


if __name__ == "__main__":
    alice_list = CLS()
    bob_list = CLS()
    alice_list.add("Milk")
    alice_list.add("Potato")
    alice_list.add("Eggs")
    bob_list.add("Sausage")
    bob_list.add("Mustard")
    bob_list.add("Coke")
    bob_list.add("Potato")
    bob_list.mutual_sync([alice_list])
    alice_list.remove("Sausage")
    alice_list.add("Tofu")
    alice_list.remove("Potato")
    alice_list.mutual_sync([bob_list])
    print("Bob's list contains Potato?", bob_list.contains("Potato"))
