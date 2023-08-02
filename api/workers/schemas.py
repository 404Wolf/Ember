from marshmallow import Schema, fields


class deleteQueue(Schema):
    """
    schema for DELETE /queue endpoint

    headers:
        target: target to remove from queue (string)
    """

    target = fields.String(description="Target to remove from the queue", required=True)
    delay = fields.Int(
        description="Wait an extra duration before removing from queue", required=False
    )


class postQueue(Schema):
    """
    schema for POST /queue endpoint

    body:
        target: target to add to queue (string)
        offsets: Offsets for target being added to queue. Use format [min-offset, max-offset]
        droptime: Droptime of target. If not included, droptime is automatically scraped from NameMC
    """

    target = fields.String(description="Target to add to the queue", required=True)
    offsets = fields.Tuple(
        (
            fields.Float(description="Minimum offset"),
            fields.Float(description="Maximum offset"),
        ),
        description="Offsets for target being added to queue. Use format [min-offset, max-offset]",
        required=True,
    )
    droptime = fields.Int(
        description="Droptime of target. If not included, droptime is automatically scraped from NameMC",
        required=False,
    )


class getLogTimes(Schema):
    """
    schema for GET /logging/times/{target} endpoint

    match_info:
        target: target to lookup times for
    """

    target = fields.String(
        description='Target to lookup times for, or "*" for all', required=True
    )


class logTimes(Schema):
    """
    schema for PUT /logging/times endpoint

    body:
        target: Target which is having it's offsets logged
        vpsNum: Which VPS is sending logs
        sends: List of send times and bearer counters
        receives: List of receives times, bearer counters, and response codes
    """

    target = fields.String(
        description="Target which is having its offsets logged", required=True
    )
    vpsNum = fields.Int(description="Which VPS is sending logs", required=True)

    class sends(Schema):
        time = fields.Float(description="UNIX time of request send", required=True)
        bearer = fields.Integer(
            description="Bearer counter (the bearer # on the vps sent the req)",
            required=True,
        )
        offset = fields.Float(description="Offset used for snipe", required=True)

    class receives(Schema):
        time = fields.Float(description="UNIX time of request send", required=True)
        bearer = fields.Integer(
            description="Bearer counter (the bearer # on the vps that received the req)",
            required=True,
        )
        offset = fields.Float(description="Offset used for snipe", required=True)
        code = fields.Integer(
            description="Status code sent back from microsoft", required=True
        )

    sends = fields.List(
        fields.Nested(sends), description="Request send-data", required=True
    )
    receives = fields.List(
        fields.Nested(receives), description="Request receive-data", required=True
    )


class getNameMC(Schema):
    """
    schema for GET /namemc endpoint

    match_info:
        target: Target to gather NameMC data of
    """

    target = fields.String(description="Target to gather NameMC data of", required=True)


class accountGen(Schema):
    """
    schema for GET /accountGen endpoint

    headers:
        count: how many accounts to generate
    """

    count = fields.Int(description="How many accounts to generate", required=False)


class sendToDiscord(Schema):
    """
    schema for GET /discord/send endpoint

    headers:
        message: Message to forward to the discord logging chat, or a json to forward as an embed
    """

    message = fields.Raw(
        description="Message to forward to the discord logging chat, or a json to forward as an embed",
        required=True,
    )

    webhook = fields.String(
        description="Webhook url to send to (defaults to the bot-status webhook)",
        required=False,
    )

    vps = fields.String(description="VPS number/name", required=False)
