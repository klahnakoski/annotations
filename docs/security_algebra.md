# Security 

## Security Primitve - A Grant

All security communication and storage is done on "grants", which have the form:

```python
{
    user, 
    resource,
    signature
}
```

* **user** - the ID of the entity that requires the resource
* **resource** - the id of the resource
* **authority** - the authority that can revoke this grant 
* **signature** - an object that details the signature on this grant 

### Signature

Signatures confirm that `user` may access `resource`  

```json
{
    key,
    signature,
    authority
}
```

### Authority

Authorities are services that can revoke grants. This is not just confirming the key is valid, but if the user is still allowed to use the resource.

* **Timestamp** - Only intended for short lived grants. The grant expires at the given time.  The signature must still be verified, but only time can revoke the grant. 
* **URL** - It is assumed the authority can be found at the given url. Each time the grant is used, the authority must be contacted to verify it is still valid.
* **key** - The grant is only valid if the private key is known 

## Senarios

Private Key - `{ ___, key, key+, key}` 

Top claim - `{ user, resource, self+, self}`  if the authority has signed a grant, and you are that authority, then you will allow `user` to access `resource`.

Requirement - `{___, resource, sig?, ___}` - access to resource will be granted if it is signed by `sig`.
  
Request for access - `{user, resource, ___}`




Kyle thinks he can do employee things `{kyle, emp, moz+, moz}`

Mozilla allows kyle to do employee things: `{kyle, emp, moz+, moz}`
 
Auth0 knows Mozilla can assign employees: `{___, emp, moz?, moz}`

ActiveData only allows Mozilla employess to access API:  `{___, AD, emp?, AD}`

1) Process requests access to AD `{proc, AD, emp?}`  -> Auth0

2) Auth0 asks kyle to sign request `{proc, AD, kyle?}`

3) kyle returns signed request `{proc, AD, kyle+, timestamp}`

4) auth0 returns grant to process

5) process asks Auth0 to sign `{proc, AD, emp?}`  given `{proc, AD, kyle, timestamp}` and `{kyle, emp, moz?}`

6) Auth0 confirms `{kyle, emp, moz+, moz}` with mozilla

7) Auth0 returns `{proc, AD, emp, auth0}` -> Auth0

8) API does not trust `proc`, so the grant can not be used by proc

9) Proc asks Auth0 `{token, AD, proc`} to be signed by emp

10) Auth0 can sign `{token, AD, emp, timestamp}`, and it is returned