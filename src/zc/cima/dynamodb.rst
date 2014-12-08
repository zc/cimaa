Storing monitoring data in DynamoDB
===================================

You can store your monitoring data in dynamodb using the
``zc.cima.dynamodb`` implementation in your agent configuration::

  [database]
  class = zc.cima.dynamodb
  region = us-east-1

Additional configuration options:

prefix
  A table name prefix, defaulting to ``cima``.  The tables used will
  have names prefixes with this string and a
  dot. (e.g. ``cima.agents``).

aws_access_key_id and aws_secret_access_key
  Use these to specify keys in the configuration. If not specified,
  then credentials will be searched for in environment variables,
  ~/.boto and instance credentials.

