

## API Login sequence

The annotation server 


Send Access Token to `auth0.endpoints.login`

The `login` configuration parameter is the absolute path of that will accept an Auth0 Access Token


    curl https://example.com/login  -H Authorization=Bearer <AccessToken>

The service will verify the access token with Auth0; this include receiving some identity information; which is further confirmed/elaborated with Mozzila IAM. 

The body of the response is a Session Token. The neccesary parameter is the `value` which is the secret, the other parameters are for the browser to make a cookie for subequent requests:

    {
        "name": "cookie name"
        "value": "the secret session token"
        "domain": "example.com",
        "path": "/",
        "secure": true,
        "httponly": true,
        "expires": "Oct 31, 2019",
        "inactive_lifetime": "30minute"
    }

The session token can be used until it expires. It can be added to the header, as a cookie

    curl https://example.com/query -H Cookie=the secret session token  -d "..."

The Session Token lifetime is variable, depending on how much it is used: To keep the Session Token alive you can call a `auth0.endpoints.keep_alive` 

    curl https://example.com/ping  -H Cookie=the secret session token 

Once the session expires, a new Access Token must be used to `login`.
