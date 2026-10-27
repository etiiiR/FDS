package ch.unibas.dmi.dbis.fds.p2p.chord.impl;

import ch.unibas.dmi.dbis.fds.p2p.chord.api.*;
import ch.unibas.dmi.dbis.fds.p2p.chord.api.ChordNetwork;
import ch.unibas.dmi.dbis.fds.p2p.chord.api.data.Identifier;
import ch.unibas.dmi.dbis.fds.p2p.chord.api.data.IdentifierCircularInterval;

import java.util.*;

import static ch.unibas.dmi.dbis.fds.p2p.chord.api.data.IdentifierCircularInterval.createOpen;

/**
 * TODO: write JavaDoc
 *
 * @author loris.sauter
 */
public class ChordPeer extends AbstractChordPeer {
  /** Index of the finger to refresh on the next dynamic fix_fingers call. */
  private int nextFinger;

  /**
   *
   * @param identifier
   * @param network
   */
  protected ChordPeer(Identifier identifier, ChordNetwork network) {
    super(identifier, network);
  }

  /**
   * Asks this {@link ChordNode} to find {@code id}'s successor {@link ChordNode}.
   *
   * Defined in [1], Figure 4
   *
   * @param caller The calling {@link ChordNode}. Used for simulation - not part of the actual chord definition.
   * @param id The {@link Identifier} for which to lookup the successor. Does not need to be the ID of an actual {@link ChordNode}!
   * @return The successor of the node {@code id} from this {@link ChordNode}'s point of view
   */
  @Override
  public ChordNode findSuccessor(ChordNode caller, Identifier id) {
    // The successor is the node immediately after the identifier's predecessor.
    ChordNode predecessor = findPredecessor(caller, id);
    return predecessor.getFingerTable().successor();
  }

  /**
   * Asks this {@link ChordNode} to find {@code id}'s predecessor {@link ChordNode}
   *
   * Defined in [1], Figure 4
   *
   * @param caller The calling {@link ChordNode}. Used for simulation - not part of the actual chord definition.
   * @param id The {@link Identifier} for which to lookup the predecessor. Does not need to be the ID of an actual {@link ChordNode}!
   * @return The predecessor of or the node {@code of} from this {@link ChordNode}'s point of view
   */
  @Override
  public ChordNode findPredecessor(ChordNode caller, Identifier id) {
    ChordNode current = this;

    // Keep the search bounded in case a stale finger table forms a loop.
    for (int hops = 0; hops < getNetwork().getIdentifierCircle().size(); hops++) {
      ChordNode successor = current.getFingerTable().successor();
      if (successor == null) {
        throw new IllegalStateException("Node " + current.getIdentifier() + " has no successor");
      }

      // Current precedes id when id lies in (current, successor].
      if (successor == current || IdentifierCircularInterval
          .createLeftOpen(current.getIdentifier(), successor.getIdentifier()).contains(id)) {
        return current;
      }

      // Skip toward id using the closest usable finger.
      ChordNode next = current.closestPrecedingFinger(caller, id);
      if (next == current) {
        // A stale or incomplete finger table can still make progress by one hop.
        next = successor;
      }
      current = next;
    }
    throw new IllegalStateException("Chord lookup did not converge");
  }

  /**
   * Return the closest finger preceding the  {@code id}
   *
   * Defined in [1], Figure 4
   *
   * @param caller The calling {@link ChordNode}. Used for simulation - not part of the actual chord definition.
   * @param id The {@link Identifier} for which the closest preceding finger is looked up.
   * @return The closest preceding finger of the node {@code of} from this node's point of view
   */
  @Override
  public ChordNode closestPrecedingFinger(ChordNode caller, Identifier id) {
    // Check longest jumps first to reduce the number of hops.
    for (int i = getNetwork().getNbits(); i >= 1; i--) {
      ChordNode finger = getFingerTable().node(i).orElse(null);
      if (finger != null && finger.status() == NodeStatus.ONLINE
          && createOpen(getIdentifier(), id).contains(finger.getIdentifier())) {
        return finger;
      }
    }
    return this;
  }

  /**
   * Called on this {@link ChordNode} if it wishes to join the {@link ChordNetwork}. {@code nprime} references another {@link ChordNode}
   * that is already member of the {@link ChordNetwork}.
   *
   * Required for static {@link ChordNetwork} mode. Since no stabilization takes place in this mode, the joining node must make all
   * the necessary setup.
   *
   * Defined in [1], Figure 6
   *
   * @param nprime Arbitrary {@link ChordNode} that is part of the {@link ChordNetwork} this {@link ChordNode} wishes to join.
   */
  @Override
  public void joinAndUpdate(ChordNode nprime) {
    if (nprime != null) {
      // Initialize this node, then update existing nodes whose fingers now point here.
      initFingerTable(nprime);
      Map<String, String> movedKeys = takeKeysFromSuccessor(fingerTable.successor());
      updateOthers(nprime);

      // Store the moved keys after routing tables point them to their new owner.
      movedKeys.forEach((key, value) -> store(this, key, value));
    } else {
      // The first node owns the whole ring, so all fingers point to itself.
      for (int i = 1; i <= getNetwork().getNbits(); i++) {
        fingerTable.setNode(i, this);
      }
      setPredecessor(this);
    }
  }

  /**
   * Called on this {@link ChordNode} if it wishes to join the {@link ChordNetwork}. {@code nprime} references
   * another {@link ChordNode} that is already member of the {@link ChordNetwork}.
   *
   * Required for dynamic {@link ChordNetwork} mode. Since in that mode {@link ChordNode}s stabilize the network
   * periodically, this method simply sets its successor and waits for stabilization to do the rest.
   *
   * Defined in [1], Figure 7
   *
   * @param nprime Arbitrary {@link ChordNode} that is part of the {@link ChordNetwork} this {@link ChordNode} wishes to join.
   */
  @Override
  public void joinOnly(ChordNode nprime) {
    // Stabilization will discover the predecessor after this node joins.
    setPredecessor(null);
    if (nprime == null) {
      fingerTable.setNode(1, this);
    } else {
      fingerTable.setNode(1, nprime.findSuccessor(this, this));
    }
  }

  /**
   * Initializes this {@link ChordNode}'s {@link FingerTable} based on information derived from {@code nprime}.
   *
   * Defined in [1], Figure 6
   *
   * @param nprime Arbitrary {@link ChordNode} that is part of the network.
   */
  private void initFingerTable(ChordNode nprime) {
    // Find the successor for this node's first finger start.
    Identifier firstStart = getNetwork().getIdentifierCircle().getIdentifierAt(fingerTable.start(1));
    ChordNode successor = nprime.findSuccessor(this, firstStart);
    fingerTable.setNode(1, successor);
    setPredecessor(successor.predecessor());
    successor.setPredecessor(this);

    // Each later finger either shares the previous finger or needs a lookup.
    for (int i = 1; i < getNetwork().getNbits(); i++) {
      ChordNode previousFinger = fingerTable.node(i).orElseThrow();
      Identifier nextStart = getNetwork().getIdentifierCircle()
          .getIdentifierAt(fingerTable.start(i + 1));
      int previousFingerId = previousFinger.getIdentifier().getIndex();

      if (isInClockwiseRange(fingerTable.start(i), previousFingerId, nextStart.getIndex())) {
        fingerTable.setNode(i + 1, previousFinger);
      } else {
        fingerTable.setNode(i + 1, nprime.findSuccessor(this, nextStart));
      }
    }
  }

  /**
   * Updates all {@link ChordNode} whose {@link FingerTable} should refer to this {@link ChordNode}.
   *
   * Defined in [1], Figure 6
   */
  private void updateOthers(ChordNode nprime) {
    for (int i = 1; i <= getNetwork().getNbits(); i++) {
      // Ask the predecessor of n - 2^(i - 1) to update its i-th finger.
      int offset = 1 << (i - 1);
      int predecessorIndex = getIdentifier().getIndex() - offset;
      Identifier predecessorSearchId = getNetwork().getIdentifierCircle()
          .getIdentifierAt(predecessorIndex);
      ChordNode predecessor = nprime.findPredecessor(this, predecessorSearchId);
      predecessor.updateFingerTable(this, i);
    }
  }

  /**
   * If node {@code s} is the i-th finger of this node, update this node's finger table with {@code s}
   *
   * Defined in [1], Figure 6
   *
   * @param s The should-be i-th finger of this node
   * @param i The index of {@code s} in this node's finger table
   */
  @Override
  public void updateFingerTable(ChordNode s, int i) {
    if (s == this || i < 1 || i > getNetwork().getNbits()) return;

    int fingerStart = fingerTable.start(i);
    int oldSuccessorId = fingerTable.node(i).orElseThrow().getIdentifier().getIndex();

    /*
     * Update this finger only if the joining node is now the successor of
     * this finger's start. This also handles a one-node ring, where the old
     * finger points back to this node and the paper's interval is ambiguous.
     */
    if (!isInClockwiseRange(fingerStart, oldSuccessorId, s.getIdentifier().getIndex())) return;

    fingerTable.setNode(i, s);

    // Continue toward earlier predecessors while they also need this update.
    ChordNode predecessor = predecessor();
    if (predecessor == s) {
      // Joining sets its successor's predecessor to itself. Skip the joiner
      // and continue with the old predecessor so that no existing node is missed.
      predecessor = s.predecessor();
    }
    if (predecessor != null && predecessor != this) {
      predecessor.updateFingerTable(s, i);
    }
  }

  /** Returns true when value is in the clockwise range [start, end). */
  private boolean isInClockwiseRange(int start, int end, int value) {
    if (start < end) {
      return value >= start && value < end;
    }
    if (start > end) {
      return value >= start || value < end;
    }
    return false;
  }

  /** Returns whether this peer is responsible for the key in the updated ring. */
  private boolean ownsKey(String key) {
    ChordNode currentPredecessor = predecessor();
    if (currentPredecessor == null) return false;

    int keyIndex = getNetwork().getHashFunction().hash(key);
    Identifier keyId = getNetwork().getIdentifierCircle().getIdentifierAt(keyIndex);
    return IdentifierCircularInterval.createLeftOpen(
        currentPredecessor.getIdentifier(), getIdentifier()).contains(keyId);
  }

  /** Removes from the old successor the keys this node takes responsibility for. */
  private Map<String, String> takeKeysFromSuccessor(ChordNode successor) {
    if (!(successor instanceof AbstractChordPeer)) {
      throw new IllegalStateException("Chord successor cannot provide stored data");
    }

    AbstractChordPeer source = (AbstractChordPeer) successor;
    Map<String, String> movedKeys = new HashMap<>();

    // Delete while the old routing tables still direct these keys to the successor.
    for (String key : new ArrayList<>(source.keys())) {
      if (ownsKey(key)) {
        source.delete(this, key).ifPresent(value -> movedKeys.put(key, value));
      }
    }
    return movedKeys;
  }

  /**
   * Called by {@code nprime} if it thinks it might be this {@link ChordNode}'s predecessor. Updates predecessor
   * pointers accordingly, if required.
   *
   * Defined in [1], Figure 7
   *
   * @param nprime The alleged predecessor of this {@link ChordNode}
   */
  @Override
  public void notify(ChordNode nprime) {
    if (this.status() == NodeStatus.OFFLINE || this.status() == NodeStatus.JOINING) return;
    ChordNode currentPredecessor = predecessor();

    // Accept nprime only if it is closer to this node than the current predecessor.
    if (currentPredecessor == null || currentPredecessor == this
        || IdentifierCircularInterval.createOpen(currentPredecessor.getIdentifier(), getIdentifier())
            .contains(nprime.getIdentifier())) {
      setPredecessor(nprime);
    }
  }

  /**
   * Called periodically in order to refresh entries in this {@link ChordNode}'s {@link FingerTable}.
   *
   * Defined in [1], Figure 7
   */
  @Override
  public void fixFingers() {
    if (this.status() == NodeStatus.OFFLINE || this.status() == NodeStatus.JOINING) return;

    // Figure 7 refreshes one finger per call, cycling through the table.
    nextFinger = (nextFinger % getNetwork().getNbits()) + 1;
    Identifier start = getNetwork().getIdentifierCircle().getIdentifierAt(fingerTable.start(nextFinger));
    fingerTable.setNode(nextFinger, findSuccessor(this, start));
  }

  /**
   * Called periodically in order to verify this node's immediate successor and inform it about this
   * {@link ChordNode}'s presence,
   *
   * Defined in [1], Figure 7
   */
  @Override
  public void stabilize() {
    if (this.status() == NodeStatus.OFFLINE || this.status() == NodeStatus.JOINING) return;
    ChordNode successor = fingerTable.successor();
    if (successor == null) return;

    // If the successor knows a closer predecessor, make it the new successor.
    ChordNode successorPredecessor = successor.predecessor();
    if (successorPredecessor != null && successorPredecessor != this
        && successorPredecessor.status() == NodeStatus.ONLINE
        && IdentifierCircularInterval.createOpen(getIdentifier(), successor.getIdentifier())
            .contains(successorPredecessor.getIdentifier())) {
      fingerTable.setNode(1, successorPredecessor);
      successor = successorPredecessor;
    }

    // Let the successor consider this node as its predecessor.
    successor.notify(this);
  }

  /**
   * Called periodically in order to check activity of this {@link ChordNode}'s predecessor.
   *
   * Not part of [1]. Required for dynamic network to handle node failure.
   */
  @Override
  public void checkPredecessor() {
    if (this.status() == NodeStatus.OFFLINE || this.status() == NodeStatus.JOINING) return;
    ChordNode currentPredecessor = predecessor();

    // Forget a failed predecessor so stabilization can accept a replacement.
    if (currentPredecessor != null && currentPredecessor.status() == NodeStatus.OFFLINE) {
      setPredecessor(null);
    }
  }

  /**
   * Called periodically in order to check activity of this {@link ChordNode}'s successor.
   *
   * Not part of [1]. Required for dynamic network to handle node failure.
   */
  @Override
  public void checkSuccessor() {
    if (this.status() == NodeStatus.OFFLINE || this.status() == NodeStatus.JOINING) return;
    ChordNode successor = fingerTable.successor();
    if (successor == null || successor.status() == NodeStatus.OFFLINE) {
      // Bypass the departed successor by following its successor pointers.
      ChordNode replacement = findNextOnline(successor);
      fingerTable.setNode(1, replacement);
      if (replacement == this) setPredecessor(this);
    }
  }

  /** Follows successor pointers until it finds a live node or returns to this node. */
  private ChordNode findNextOnline(ChordNode candidate) {
    Set<ChordNode> visited = Collections.newSetFromMap(new IdentityHashMap<>());
    while (candidate != null && visited.add(candidate)) {
      if (candidate.status() == NodeStatus.ONLINE) return candidate;
      candidate = candidate.getFingerTable().successor();
    }
    return this;
  }

  /**
   * Performs a lookup for where the data with the provided key should be stored.
   *
   * @return Node in which to store the data with the provided key.
   */
  @Override
  protected ChordNode lookupNodeForItem(String key) {
    // Hash the key into the ring, then store it at that identifier's successor.
    int keyIndex = getNetwork().getHashFunction().hash(key);
    Identifier keyId = getNetwork().getIdentifierCircle().getIdentifierAt(keyIndex);
    return findSuccessor(this, keyId);
  }

  @Override
  public String toString() {
    return String.format("ChordPeer{id=%d}", this.id().getIndex());
  }
}
