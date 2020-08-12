![NetDice logo](netdice-logo.png)

# NetDice: Probabilistic Verification of Network Configurations

A scalable and accurate probabilistic network configuration analyzer verifying network properties in the face of random failures.

This is an implementation of the approach presented in the following [research paper](https://www.sri.inf.ethz.ch/publications/steffen2020netdice):

> Samuel Steffen, Timon Gehr, Petar Tsankov, Laurent Vanbever, and Martin Vechev. 2020. Probabilistic Verification of Network Configurations. In Proceedings of SIGCOMM ’20.

## Quick Start
Run NetDice for given input configuration (JSON format described [below](#json-input-format)):
```shell
python -m netdice.app <input.json>
```

For instance, try our running example from the publication (Figure 3) with target precision 0.0001:
```shell
python -m netdice.app tests/inputs/paper_example.json --precision 0.0001
```

List available command line arguments:
```shell
python -m netdice.app --help
```

## Setup

We recommend running NetDice on Ubuntu. However, NetDice is platform-independent and has been successfully tested also on Windows.

We provide an `environment.yml` file specifying the necessary Python dependencies. The easiest way to setup NetDice is installing a conda environment including all necessary dependencies using the following command (requires [installing conda](https://conda.io/projects/conda/en/latest/user-guide/install/index.html) first):

```shell
# installs environment 'netdice' with all necessary dependencies
conda env create -f environment.yml
```

Then, simply activate the environment before executing any NetDice code:
```shell
conda activate netdice
```

To verify successful installation, you can run NetDice's unit tests as follows:
```shell
python -m unittest discover -s tests
```

## JSON Input Format

Example input files can be found in `tests/inputs/`. The JSON input has the following structure.

```
{
  "version": "0.1",         // input format version for compatibility reasons
  "topology": {...},        // network topology, static routes, BGP configuration
  "announcements": {...},   // eBGP announcements sent by external peers
  "failures": {...},        // probabilistic failure model
  "properties": [...]       // list of properties to be analyzed
}
```

### Example

A minimal example demonstrating the individual components (`tests/inputs/example.json`) is provided below.

```
{
  "version": "0.1",
  "topology": {
    "nodes": ["node_A", "node_B", "node_C"],                    // three nodes with string identifiers
    "links": [
      { "u": "node_A", "v": "node_B", "w_uv": 2, "w_vu": 2 },   // link A<->B with directed weights
      { "u": "node_B", "v": "node_C", "w_uv": 1, "w_vu": 3 }    // weight B->C is 1, but C->B is 3
    ],
    "static_routes": [
      // static route at B towards C for given destination identifier (string)      
      { "u": "node_B", "v": "node_C", "dst": "192.168.0.0/16" }
    ],
    "bgp": {
      "as": 1000,                              // AS number of the network
      "internal_routers": [                    // list of internal BGP routers
        { "node": "node_B", "peer_id": 11 },   // node B runs BGP and has peer ID 11
        { "node": "node_C", "peer_id": 12 },
        { "node": "node_A", "peer_id": 10 }
      ],
      "external_routers": [                    // list of BGP routers in neighboring ASes
        {
          "name": "ext_A",                     // string identifier
          "peers_with": "node_A",              // node A is connected to ext_A via eBGP
          "peer_id": 90,                       // ext_A has peer ID 90
          "as": 9001                           // ext_A is in AS number 9001
        },
        {
          "name": "ext_C",
          "peers_with": "node_C",
          "peer_id": 91,
          "as": 9002
        }
      ],
      "internal_sessions": [                                  // list of iBGP sessions
        { "route_reflector": "node_B", "client": "node_A" },  // B is a route reflector with client A
        { "peer_1": "node_B", "peer_2": "node_C" }            // B and C are regular iBGP peers
      ]
    }
  },
  "announcements": {          // dictionary of announcements for potentially multiple destinations
    "10.0.0.0/8": {           // destination identifier (string)
      "ext_A": { "lp": 5, "aspl": 2, "origin": 0, "med": 0 },   // ext_A sends the given attributes
      "ext_C": { "lp": 10, "aspl": 3, "origin": 0, "med": 50 }  // origin: 0=IGP, 1=EGP, 2=INCOMPLETE
    }
  },
  "failures": {
    "type": "NodeFailureModel",     // models node and link failures, can also use "LinkFailureModel"
    "p_link_failure": 0.001,        // probability of a link failure
    "p_node_failure": 0.002         // probability of a node failure
  },
  "properties": [{                                        // list of properties to analyze
    "type": "Waypoint",                                   // waypoint property
    "flow": { "src": "node_A", "dst": "10.0.0.0/8" },     // flow from ingress A to given destination
    "waypoint": "node_B"                                  // waypoint B
  }]
}
```

### Alternative: Separating Topology from Query

For easy re-use of the topology and BGP configuration across multiple queries, the input can be split into two files as indicated below (see `tests/inputs/example_topology_only.json` and `tests/inputs/example_query_only.json` for an example).

```
// topology.json
{
  "version": "0.1",
  "topology": {...}
}


// query.json
{
  "version": "0.1",
  "announcements": {...},
  "failures": {...},
  "properties": [...]
}
```
When running NetDice, use the `--query` flag in this case:
```shell
python -m netdice.app <topology.json> --query <query.json>
```

### Alternative: Whitespace-separated Topology File

Nodes and links can also be provided as a compact whitespace-separated text file, see `tests/inputs/paper_example.json` for an example.

### Alternative: Auto iBGP Full Mesh

For iBGP full mesh configurations, the `internal_routers` and `internal_sessions` nodes can be replaced by an "auto" flag telling NetDice to automatically construct a full mesh (see `tests/inputs/paper_example_full_mesh.json` for an example).
```
"bgp": {
    "as": ...,
    "auto": "full_mesh",
    "external_routers": [ ... ],
}
```

### Predefined Properties

The predefined properties natively supported by NetDice are exemplified below (see also `tests/inputs/different_properties.json`).

**Egress:** Flow from A to the prefix 10.0.0.0/8 leaves the network at B.
```
{
  "type": "Egress",
  "flow": { "src": "node_A", "dst": "10.0.0.0/8" },
  "egress": "node_B"
}
```

**Loop:** Flow from A to the prefix 10.0.0.0/8 is forwarded along a loop.
```
{
  "type": "Loop",
  "flow": { "src": "node_A", "dst": "10.0.0.0/8" }
}
```

**Reachability:** Node A reaches the prefix 10.0.0.0/8.
```
{
  "type": "Reachable",
  "flow": { "src": "node_A", "dst": "10.0.0.0/8" }
}
```

**Path Length:** Flow from A to the prefix 10.0.0.0/8 traverses exactly 3 links.
```
{
  "type": "PathLength",
  "flow": { "src": "node_A", "dst": "10.0.0.0/8" },
  "length": 3
}
```

**Waypointing:** Flow from A to the prefix 10.0.0.0/8 traverses waypoint B.
```
{
  "type": "Waypoint",
  "flow": { "src": "node_A", "dst": "10.0.0.0/8" },
  "waypoint": "node_B"
}
```

**Congestion:** Flows A->10.0.0.0/8 and B->10.0.0.0/8 with volumes 10 and 25 together do not exceed volume threshold 30 for link C->D.
```
{
  "type": "Congestion",
  "flows": [
      { "src": "node_A", "dst": "10.0.0.0/8", "volume": 10 },
      { "src": "node_B", "dst": "10.0.0.0/8", "volume": 25 }
    ],
  "link": { "u": "node_C", "v": "node_D" },
  "threshold": 30
}
```

**Load-balancing:** The load on links C->D and C->E induced by flows A->10.0.0.0/8 and B->10.0.0.0/8 with volumes 10 and 25 differs by at most 5.
```
{
  "type": "Balanced",
  "flows": [
      { "src": "node_A", "dst": "10.0.0.0/8", "volume": 20 },
      { "src": "node_B", "dst": "10.0.0.0/8", "volume": 25 }
    ],
  "links": [
      { "u": "node_C", "v": "node_D" },
      { "u": "node_C", "v": "node_E" }
    ]
  "delta": 5
}
```

**Isolation:** Flows A->10.0.0.0/8 and B->10.0.0.0/8 do not share any links.
```
{
  "type": "Isolation",
  "flows": [
      { "src": "node_A", "dst": "10.0.0.0/8" },
      { "src": "node_B", "dst": "10.0.0.0/8" }
    ]
}
```

### Adding Custom Properties

Custom properties can be added using NetDice's Python interface. Specifically,
add a class extending `netdice.properties.BaseProperty` to
`netdice/properties.py`. The class name must end with `Property` and implement
the `from_data`, `get_human_readable` and `check` methods of `BaseProperty` (see
the Python docstrings for details). NetDice uses reflection to select and
construct properties based on the `type` name specified in the JSON input.

For example, we can implement a "dummy" property always returning `true` as follows.

```python
class AlwaysTrueProperty(BaseProperty):
    def __init__(self, flow: Flow):
        # always call BaseProperty.__init__
        super().__init__([flow])

    @staticmethod
    def from_data(data: dict, name_resolver):
        flow = BaseProperty._parse_flow(data, name_resolver)
        # additional configuration can be parsed from the JSON input (data dictionary) here
        return AlwaysTrueProperty(flow)

    def get_human_readable(self, name_resolver):
        return "AlwaysTrue"

    def check(self, fw_graphs: dict) -> bool:
        # perform the actual property check here, we simply return true
        return True
```

To use this property for a query, use the following JSON snippet:
```
{
  "type": "AlwaysTrue",
  "flow": { "src": "node_A", "dst": "10.0.0.0/8" }
}
```

## SIGCOMM 2020 Evaluation

You can find instructions on how to reproduce the evaluation results of our SIGCOMM 2020 paper in the folder `eval_sigcomm2020/`.

## Team

NetDice is a project at the [ICE Center](http://ice.ethz.ch/) at [ETH Zurich](https://ethz.ch), comprising researchers from the [Networked Systems Group](https://nsg.ee.ethz.ch/) and the [Secure, Reliable, and Intelligent Systems Lab](https://www.sri.inf.ethz.ch/):

- [Samuel Steffen](https://www.sri.inf.ethz.ch/people/samuel)
- [Timon Gehr](https://www.sri.inf.ethz.ch/people/timon)
- [Petar Tsankov](https://www.sri.inf.ethz.ch/people/petar)
- [Laurent Vanbever](https://nsg.ee.ethz.ch/people/laurent-vanbever/)
- [Martin Vechev](https://www.sri.inf.ethz.ch/people/martin)

## Citing this Work

You are encouraged to cite the following [research paper](https://www.sri.inf.ethz.ch/publications/steffen2020netdice) if you use NetDice for academic research.

```
@inproceedings{steffen2020netdice,
    author = {Steffen, Samuel and Gehr, Timon and Tsankov, Petar and Vanbever, Laurent and Vechev, Martin},
    title = {Probabilistic Verification of Network Configurations},
    year = {2020},
    isbn = {9781450379557},
    publisher = {Association for Computing Machinery},
    address = {New York, NY, USA},
    url = {https://doi.org/10.1145/3387514.3405900},
    doi = {10.1145/3387514.3405900},
    booktitle = {Proceedings of the Annual Conference of the ACM Special Interest Group on Data Communication on the Applications, Technologies, Architectures, and Protocols for Computer Communication},
    pages = {750–764},
    numpages = {15},
    location = {Virtual Event, USA},
    series = {SIGCOMM ’20}
}
```

## License

MIT license, see [LICENSE](LICENSE).
