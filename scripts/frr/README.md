# Vyatta JSON to FRR CLI format translator  

## How it works  

1. Parse the Vyatta JSON config file to a Python dictionary using the [JSONDecoder](https://docs.python.org/2/library/json.html#json.JSONDecoder).
2. Order critical nodes in the tree to allow specific 'priority' commands to come before others (optional).
3. Visit every node in the dict in a depth first manner, building its path along the way in a Linux FS like format (i.e. /protocols/ospf/...). List members have no names so an *@element* tag is appended to the path. Note that the index of the element is not appended, so the path /a/b/@element refers to **every** element of the list `{a: {b: [...]}}`
4. When each node is reached, its path is used to retrieve the corresponding command(s) from the syntax file. The command itself can make relative references to other nodes in the tree, either in lower or upper levels from the current node but these references can't pass by a list.
5. Sanitize the command to allow Python's string.Formatter to parse it: Dots are not allowed in identifier name so replace up traversal '..' with a different sign.
6. Resolve these references and replace them with their values using python's advanced string formatting features.
7. Append the finalized command into the output list if all required references were resolved, otherwise discard the command to avoid producing invalid commands.
8. Create the FRR config by joining the output list elements (commands) with newlines.

## Accompanying config files

* **config/syntax files**: Flat JSON files dictating what parts of the Vyatta json map to what FRR CLI commands. At most one entry for each path. Should all be stored under \<configDir>/commands directory. The format is as follows:

```json
{
    '/path/to/nodeA': 'single command to include with {/references/@text}',  
    '/path/to/nodeB': ['can', 'include', 'multiple', 'commands'],
    '/path/to/nodeC': 'single command [with a {/set/@text}, of {/options/@text}]',
    '/path/to/nodeD': 'single command [with an optional {/set/@text}, ]',
    '/path/to/node/@enter': 'enter command',
    '/path/to/node/@exit': 'exit command',
}
```

* **priority file**: Flat JSON file dictating nodes that have ordering requirements. Should be stored under \<configDir> directory. The format is as follows:

```json
{
    '/path/to/parent/of/critical/node': {
        'first': ['child1', 'child2'],
        'last': ['child3', 'child4']
    }
}
```

## JSON Decoding

The [JSONDecoder](https://docs.python.org/2/library/json.html#json.JSONDecoder) is used to parse the json string into a Python dict. **The only change from the default types is that and OrderedDict is using instead of a dict**. Note the following:

* **null values** are decoded as None type in Python. If a key with a None value is referenced, then parser will use the string 'None'

## Usage instructions

Usually you only need to edit / create a commands json file to add support for a new translation.

1. Identify the path in the json where the key element of the command lives in.
2. Add a new entry in the appropriate commands json file (or create a new one) with key being the path above and value being the command string template.
3. Add a priority entry in the priorities json file, if the command needs to appear before/after others.

## References

All keywords inside a path start with an @, to avoid conflicts:

* **@text**: value of a text leaf
* **@dict**: value of a json dictionary
* **@element**: an element of a list
* **@enter**: enter command of node
* **@exit**: exit command of node

All references that live inside a command:

* are relative to the current node (the node on the path indicated by the key)
* should start with a `/`  
* need to be enclosed in `{}`  
* should finish with a @text keyword, to specify the target value

Examples:  
`dict = {a: {b: 'value'}, key: 'text', c: [1,2,3]}`  
To reference b's value from the root: {/a/b/@text}  
To reference key's value from inside b: {/../key/@text}  
To reference c's every element from inside b: {/../c/@element/@text}  

## Value formatting

References are resolved by a child class of Python's [string Formatter](https://docs.python.org/3.4/library/string.html#string.Formatter). Hence, you can format reference's values using python's [format specification mini-language](https://docs.python.org/3.4/library/string.html#formatspec). A few examples:

* **{/number/@text:x}**: print the number as a lowercase hexadecimal digit
* **{/number/@text:+05}**: include the + sign if positive, print in 5 spaces and left pad with 0s.

## Custom formatting

The Formatter class format_field method is extended to add some custom formatting.

### Loops

Used to print an array inline. The syntax is as follows:
>`{/name/@text:for:template with {{element}}}`

Note the use of double curly brackets and the keyword *element* when referring to list elements.

Example:

* **{/name/@text}:for:{{element}} }** will print "a b c " if /name has a value of ['a', 'b', 'c']

## Command string processing

The command string processing procedure follows these steps:

1. Replace all references with their values or with the **unresolved reference template** (constant in the command python script) if no value was found.
2. Evaluate functions and replace their patterns with the resulting value.
3. Resolve sets.
4. If the unresolved reference template exists then discard the command otherwise add it in the output list.

## Required and optional references

All references in a command are considered required, i.e. if an unresolved reference exists in step 4, then that command will not be included in the output to avoid invalid commands. If a part of a command is optional then it should be included in an optional set.

## Sets

Sets are indicated by square brackets (`[]`) in commands and their members are comma separated.  
The first member of the set that has no unresolved references (i.e. doesn't include the unresolved reference template) will replace the whole set.  
For example, the command  
>`neighbor 3.3.3.3 [remote-as {/remote-as/@text}, peer-group {/peer-group/@text}]
`

will become:

* `neighbor 3.3.3.3 remote-as #` if there is a string value under *remote-as*
* `neighbor 3.3.3.3 peer-group #` if there is no string value under *remote-as* but there is under *peer-group*
* None otherwise

### Optional Sets

Optional sets are regular sets with an empty member at the end, e.g.
>`[remote-as {/remote-as/@text}, peer-group {/peer-group/@text},]`

If none of the members can be satisfied, the empty string is always satisfied (has no unresolved references) and it will replace the set, creating the command `neighbor 3.3.3.3` in the above scenario

## Functions

Functions allow you to manipulate the value of a reference before printing it. They are evaluated after resolving references so you can have references anywhere in them. The general format is as follows:
>`$name_of_function|pipe_separated_parameters$`

These are the functions currently supported:  

### Conditionals

Conditionals allow you to adjust the output according to the value of the reference. The syntax is as follows:
>`$if|value1,value2,...valueN,|condition1,condition2,...conditionN,$`

Condition currently supports:

* equality checking (==)
* inequality checking (!=)
* greater than or equal (>=)
* less than or equal (<=)
* greater than (>)
* less than (<)
* dictionary presence (in)

Only conditions that have a matching value will be evaluated, if there are 4 conditions and 2 values only the first two of each section will be parsed.
If an else clause is required then use a comma with no condition as the last element. In the code a tautology will be inserted to act as the else.

Examples:

* **$if|message-digest,plaintext|{/@text}==md5,$** will print message-digest if the value /@text is equal to md5 else it will print plaintext.
* **$if|message-digest,|{/@text}==md5$** will print message-digest if the value /@text is equal to md5 else it won't print anything.
* **$if|:message-digest,{/other/@text}|{/@text}==md5,$** will print message-digest if the value /@text is equal to md5 else it will print the value of another node.
* **[$if|message-digest,???|{/@text}==md5$, ...]** assuming that the *unresolved reference template* is equal to '???', then this is how you can include conditionals in a set if you want other set members to take priority in the else case.
* **$if|host {/source/host/@text},network {/source/network} {/source/mask}, any|host in {/source}, network in {source},$** will print host and the ip address if host exists in the dictionary, network and the network address and mask if network is in the dictionary, and any if neither of the other two conditions match.

### Code execution

Python code can be included in the commands and it will be evaluated using the eval function. Due to safety reasons, no functions can be called but this can be adjusted. The syntax is as following:
>`$ex|python_code$`

For example a conditional can be formed as follows:  
>$ex|'message-digest' if '{/@text}'=='md5' else ''$

## Enter and exit commands

You can specify a command to include in the output config before including the translations of a node and all its children, and/or an exit command after that.  
Enter and exit commands are tagged with an `@enter` and `@exit` appropriately and currently can have no references in them.  
They are useful when in need to enter a submode.

E.g.  

```json
{
    '/protocols/rip/@enter': 'router rip',  
    '/protocols/rip/@exit': 'exit-router-rip',  
}
```

This will enter the 'router rip' command before converting /protocols/rip and its children to commands, and then enter the command 'exit-router-rip'.  

## Ordering

There are some cases where some commands need to come before others, e.g.
> neighbor x.x.x.x remote-as #

needs to come before any other configuration for that specific neighbor, under router bgp mode.
You can ensure this by ordering the configuration tree before parsing it. To do this:

1. Identify the path of the parent node whose children need to be prioritized.
2. Add a new string key in the priorities json file, with the string being the **path to the parent node**.
3. The key's value should be an object which optionally includes keys **first** and / or **last**, containing the names of the child nodes that should appear first or last correspondingly, in the defined order.

e.g.

```json
{
    '/protocols/ospf': {
        'first': ['a', 'b'],
        'last': ['y', 'z']
    }
}
```

Specifies that when visiting children of /protocols/ospf, child 'a' will be retrieved first (if exists), then b, then any other children in random order and finally 'y' and then 'z'.
