#!/usr/bin/python3

testkey = {
    'public':
        'mQENBFx8O8UBCAC5B3lzw26qaDq6ySF4xx16pCt5BQX+9fixVMA7z8YcGjv1mxmsjF2z1BJgG5V/' \
        '4wXw9RAzUExwZIwn3FPMQIbBNVaxNb5y0Th1sg3nENkYKFm1cKjItZrqM90OMt7BWGsggP6ah20g' \
        'jpPUAZKffavfCVieM/avK7tkerqCjXjq9LkenPjAGo5hODk0siR9Qxaj+vW1//GPd0Q/FX29Jv/l' \
        'yR5cqK06sfNN12MWZxTgLwXezioyTozd1on/z6AmHHdwLHaAIQboeOruna37F875HwxGe0UaM2nE' \
        '6xb8PZI4BkNmkSBHMqohc52Cgy6xw6Uw1ZLLHISHDd45ZkxyU2I1ABEBAAG0XXB3bWFuYWdlciB0' \
        'ZXN0IChEdW1teSBrZXkgdXNlZCBmb3IgdGVzdGluZyB0aGUgcHdtYW5hZ2VyIHBhc3N3b3JkIHV0' \
        'aWxpdHkpIDx0ZXN0QGV4YW1wbGUuY29tPokBTgQTAQoAOBYhBDE5gIAbJZWQJpTqrLzZvmREQmOP' \
        'BQJcfDvFAhsDBQsJCAcCBhUKCQgLAgQWAgMBAh4BAheAAAoJELzZvmREQmOPP58H/Rh6rBxG+jiA' \
        'ojbOrCwke2vIeV5R7GvT4anFzNM9Y6P1ppln+DWScBdA3AOds15HgmHeudodf7fTBaCL486rSwIb' \
        'QwsvrqMpkkjA4rBpJ/WDEEtvYFEGbVpipArHgMx94A+vij2lo+CLn5gUj9YpA2bWz7yzfGXH/mvT' \
        'IZm+MAh4Ch015US+Jli9f9PlLIlvB4AP0bxa9di1YW4V9jZPQM84TbzbKOiQeBptYJRlLCpgpn4q' \
        'o1anUxlQeP5dyCGGFwU/xJ9V6EnIcEf057SxcOlNvl9R4DunCXrcZ7AQejrXtQWSJAcB9PV4Lf+w' \
        '/HWfUHKQbBx2BWEPUg9l5nM3Gge5AQ0EXHw7xQEIAMbA/Pul3Zf6hp4ewF6fSOoCrzTDjOTSgH+F' \
        'X9Jp8K5ZYMI9RRt4W+jyuwx9nzNbmTOC2/vhAxuySvzzx+im9a+ukyxYqbj1mIo9cP8Rhv0+gj5E' \
        'zfzEThr7N68p4vOMmnw6i6nuGKWCeNioaVhz9a07m9LYBaNgmiibY0RROnRWej9WpvpW3802dUIH' \
        'SRhcjTy3QBc5kfWRhjBqRWRCwDkCkueWtT3FbUDt5EENVj2/Jk4N6QIS6JjUZe2ufMXpgghY2ak+' \
        '63cuATEgKd4kCIIrVZGWVl0J8bCZLUJZY6SzuRQj1Lu/mcFFkG7zDdtroeJNJPPyzZHRBx6Di0qM' \
        'ZQMAEQEAAYkBNgQYAQoAIBYhBDE5gIAbJZWQJpTqrLzZvmREQmOPBQJcfDvFAhsMAAoJELzZvmRE' \
        'QmOPzj8H/2+h6nBS7WtTkR7B3MB50kfFFmrrwQhpDel0MbOWZAgL1X3CzC+BCsjnJUi+uzpZ6LiQ' \
        'V9B7vJyI8whjncqiOOZoav/CD3MZbLis9CCdRZaooSDsL/RR1omT1JxPP+jtL+a8w34jf1xkZU07' \
        'skY0fSZ43nsvfo64SsOAHTiNh7v6UpYVsAiKtnAg7AdR4DHfq/NmAUWqv5XQYgZHn3PviXmHlilO' \
        'QVCAMlGWqKGGoSW/aZ6k0zlYQUCrvdgfBJcw2begACkWdd8hW5F4JIukhG5lyOz0BHjUkCyJ5Vzu' \
        'Jb8fFlZgTf+ZWu1o26Pi29i+lNqSmld8RkpBYD2ibW9tY3M=',
    'private': \
        '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' \
        'b21jcw==',
    'passphrase': 'testpass',
}
