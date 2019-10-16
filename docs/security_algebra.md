# Security 



## Background - Permissions

Security is about permissions, so first we will review a permission model.

In a trusted environment, a lot can be taken for granted.  We can assume the database is a trusted and ultimate authority, and trust our application to properly alter the database to ensure access is granted as needed, and no more.

### The Grant

```python
{
    user,
    resource
}
```

The Grant is a user/resource pair that says `user` can use `resource`.  Both the user and the resource are abstract concepts that 


### Roles, and Groups

Roles and Groups are common concepts that make managing Grant pairs easier for humans. Humans excel at remembering many disparate details and processing information in parallel; labeling common patterns helps with human conceptualiztion and manipulation.

Roles and Groups are a level-of-indirection that reduce redundancy; but this indirection can also be acheived with the correct resource; one that can assume the permissions of another


```python
{
    user,
    assume_all_permissions_of_group
}
```

```python
{
    group
    resource
}
```

For every `user`, there is a `assume_all_permissions_of_user` resource that we can use in our permission system.  Groups are effectively these Assumes, Roles are effectively the same as Groups.






This seems a bit like a cheat.  And the same cheat can be used for file permisions on a linux file system

```python
{user, file::read}
{user, file::write}
{user, file::execute}
```

Rather than seeing a resource (a file), with a variety of accsess methods, we simply define three "resources" for every file.









## Security Primitive - A Grant

All security communication and storage is done on "grants", which have the form:

```python
{
    user, 
    resource,
    authority,
}
```

* **user** - the entity that requires the resource
* **resource** - the resource to be consumed
* **authority** - the authority that provides this grant, and can revoke it 

### Authority

Authorities confirm that `user` may access `resource`  

```json
{
    key,
    signature,
    expiry
}
```




* **signature** - an object that details the signature on this grant 



### Authority

Authorities are services that can revoke grants. This is not just confirming the key is valid, but if the user is still allowed to use the resource.

* **Timestamp** - Only intended for short lived grants. The grant expires at the given time.  The signature must still be verified, but only time can revoke the grant. 
* **URL** - It is assumed the authority can be found at the given url. Each time the grant is used, the authority must be contacted to verify it is still valid.
* **key** - The grant is only valid if the private key is known 



## Senarios


A resource must trust a service to confirm claims, if claim is signed, then the signature must be confirmed

* verify human
* verify machine
human implicitly trusts machine


let existing user delegate to another user?
{other, table, {kyle, expiry}}
request for access

{other, table?, kyle} -> annotation server
annotation server must verify {other} and if {kyle} provides the grant (in database already) or...
kyle must login, and have interface to delegate
what is moz/auth0 doing to auto-assign?  no only confirming already knowing knowledge
how does annotation server confirm kyle can still delegate (authorizeSilently?)
annotation server asks for refresh tokens for each delegated privilege.


why is code-challenge and code verify needed for PKCE but not for device?





Admin that can assign W/R to table, but not use it, nor assign to self
things that need two keys to open 
Resources are injunctive sets of resources, (or sets of rules).

{and: [programmer, table]}


if you have a right then you can delegate the right

```


{admin, {table::read, table::write}, boss}
{kyle, programmer, hr}
{kyle, [table::read, table::write], admin}  (delegation)

```




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