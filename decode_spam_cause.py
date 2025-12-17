def decode1(msg):
    text = ""
    for i in range(0, len(msg), 2):
        text += unrot(msg[i : i + 2], i // 2)  # add position as extra parameter
    return text


def unrot(pair, pos, key=ord("x")):
    if pos % 2 == 0:  # "even" position => 2nd char is offset
        pair = pair[1] + pair[0]  # swap letters in pair
    offset = (ord("g") - ord(pair[0])) * 16  # treat 1st char as offset
    return chr(sum(ord(c) for c in pair) - key - offset)  # map to original character


def decode(msg):
    return "".join(
        [
            chr(
                ord(msg[i * 2])
                + ord(msg[i * 2 + 1])
                - 1768
                + ord(msg[i * 2 + 1 - (i & 1)]) * 16
            )
            for i in range(len(msg) // 2)
        ]
    )


if __name__ == "__main__":
    import sys

    cause = "dmFkZTFPmOj9u8ehPsDBid9RXL1TlT62Sar2mWIuo28xj9uLRBYaRg8rmsGqC1yIZOHveUsS3t"
    x = "/xjr4Trs8fAY0tXv8lFJ3vaa90IPEMeAiha5otoegpN4LYPqEtJtgbzFjIt0YAqOmKnb2tcBVhPjFVH0O07ParKIdr1ivsaq3I2I/zO0sS3G8fiFadIEGby1KaZAkANqgLnEaRTT0K/C5s08fONOWVmgk4mvMCohMDWVZPpIkT6IIMyQS4XjeNhLj2ewZnYPS/cjWtsx9Z5AYlWSi6L3v8E9f6a5UI6XIvoQORYIqbH/Kp8Lsuj0zAwpsL9yDT6fHfCVOr1h49m1anEctIeBLu7AqK8s0oVwg+JFbH3mc8pfdsbk7kCRt/0EnZKpWrGqu1KLuhPwpwTvJzk4lvFZHOOPznQ3UEY4zuS+Mcx8unihIpst22GEAUbtJ7XUtlczmgNa4fJo/zWOylfVs/6DRLKvD/ZL7sh/LSdGzGeqnvS1WV6eatDHklnUuPWg8M3cRD/f81Vu+6V/mT/h9nXq+TvJiR5ifC1UehcjOfI4X5UVfz+yRv6c89KS+h6xi9zw5eZPnSkuSG1OPNJMz4OXz7A0d9EwWYRejkThrfVeCZ8zDfxNdcgpiEIVdWmng/4amY0ZZZqu8f10aSMgJqHSDCfeTaVFmUkaJ/AhTMnw"

    print(decode1(cause))
    # print(decode(sys.argv[1]))
