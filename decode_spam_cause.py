def decode(msg):
    text = ""
    for i in range(0, len(msg), 2):
        text += unrot(msg[i : i + 2], i // 2)  # add position as extra parameter
    return text


def unrot(pair, pos, key=ord("x")):
    if pos % 2 == 0:  # "even" position => 2nd char is offset
        pair = pair[1] + pair[0]  # swap letters in pair
    offset = (ord("g") - ord(pair[0])) * 16  # treat 1st char as offset
    return chr(sum(ord(c) for c in pair) - key - offset)  # map to original character


if __name__ == "__main__":
    import sys

    cause = "gggruggvucftvghtrhhoucdtuddrgeeftddrudejjedgieeiucetufdoteggodetrfdotffvucfrrhhofhhilhgvmecuqfggjfdpvefjgfevmfevgfenuceurghilhhouhhtmecuhedttdenucfgmhhpthihuchsuhgsjhgvtghtucdluddtmdenogetfedtuddqtdduucdludehmdenucfjughrpegtggfuhffvfffkihesmhdtreertddtjeenucfhrhhomhepldguohcunhhothcurhgvphhlhidmucforghilhhinhhgucetrhhtshcuvehrohhishorshcurghssghluceomhgrihhlihhnghesrghrthhstghrohhishgvshdrsggvqeenucggtffrrghtthgvrhhnpeeugeehveetvdeflefhkedvjeekffelveehudeugeduleeggeduudfgtddutedtjeenucfkphepuddvjedrtddrtddruddpuddtledrudefjedrvddvhedrudeivdenucevlhhushhtvghrufhiiigvpedtnecurfgrrhgrmhepihhnvghtpeduvdejrddtrddtrddupdhmrghilhhfrhhomhepmhgrihhlihhnghesrghrthhstghrohhishgvshdrsggvpdhnsggprhgtphhtthhopeefpdhrtghpthhtohepgigrvhhivghrrdhmrgihvghurhesghhmrghilhdrtghomhdprhgtphhtthhopeigrghvihgvrhdrmhgrhigvuhhrsehitghlohhuugdrtghomhdprhgtphhtthhopeigrghvihgvrhesmhgrhigvuhhrrdgsvgdpoffvtefjohhsthepmhhoheeivddpmhhouggvpehsmhhtphhouhht"
    print(decode(cause))
    # print(decode(sys.argv[1]))
