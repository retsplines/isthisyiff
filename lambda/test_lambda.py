import lambda_function
print(lambda_function.lambda_handler({
    'resource': '/challenge',
    'httpMethod': 'GET'
}, None))
