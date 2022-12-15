# Release instructions for WEBPROJ

1. Checkout maintenance branch

If issueing a patch release a maintenance branch should already exists. Check it out:

```
git checkout 1.1
```

and ensure sure that all relevant commits have been backported to the maintenance branch in question.

If a major or minor version release is being prepared, a new maintenance branch based on the
master branch needs to be created:

```
git checkout -b 1.1
```

2. Tag the latest commit on the the maintenance branch with the new version number

On the maintenance branch the latest commit can now be tagged with the version number, e.g.:

```
git tag 1.1.1
git push --tags
```

3. Close the GitHub milestone for the version to be released

4. Write release notes on GitHub based on the tag created in step 2

5. Bump version number

We update the version number right away in preparation for the next release. This way we can distinguish
between released versions and to-be-released versions easily. If we see an unrelease version number we know
that we are using a development version of WEBPROJ.

`version` in `webproj\api.py` needs to be updated. After a patch release the version number is only updated
on the maintenance branch. After a major or minor release it should be updated on the master branch and subsequently
cherry-picked to the maintenance branch.

6. Deploy in production

After a release WEBPROJ needs to be deployed in Jenkins.

### Update docs on docs.dataforsyningen.dk
WEBPROJ generates Swagger documentation through flask_restx, and Dataforsyningen uses the newer OpenAPI spec, so for now we manually convert to OpenAPI and tweak the result.

1. Export the Swagger spec by accessing `{webproj path}/swagger.json`
2. Copy it into the 'official' Swagger/OpenAPI editor at https://editor.swagger.io/ and accept converting to YAML
3. Fix semantic errors ('Operations must have unique operationIds.') by altering the 1.1 paths' `operationId` values, e.g. by adding `v1_1`.
4. Go to the Edit menu and select "Convert to OpenAPI 3".
5. Click Convert.
6. Now it's time for some mad cosmetic operations in order to make up for the inability of flask_restx to supply the OpenAPI 3 fields.
   1. Replace the `info` block with this, replacing the version number with the new one:
   ```
   info:
    title: WEBPROJ
    description: "## API til koordinattransformationer\n\nAPIet __webproj__ giver adgang\
    \ til at transformere multidimensionelle koordinatsæt. \n\nTil adgang benyttes Dataforsyningens\
    \ brugeradgang som ved andre tjenester.\n\n[Versionshistorik](/webproj.txt)"
    version: "1.1.0"
    contact:
      name: SDFI Support
      url: https://dataforsyningen.dk/
      email: support@sdfi.dk
   license:
     name: Vilkår for brug
     url: https://dataforsyningen.dk/Vilkaar
    ```

   2. Replace the `servers` block with the following:
   ```
   servers:
   - url: https://api.dataforsyningen.dk/rest/webproj/
   ```
   3. Replace the `tags` single default item with tags corresponding to major versions of the API, e.g.
   ```
    tags:
   - name: "webproj 1.0"
     description: API for coordinate transformation, version 1.0
   - name: "webproj 1.1"
     description: API for coordinate transformation, version 1.1
      ```
   4. Now replace the `tags` sections single default item with the tags for the versions that support them. For example, since GET / is the same for all versions, add all tags to that - and for version-specific methods just that version tag.
7. This should now give a useful OpenAPI spec which must be pushed to the `SDFIdk/SwaggerUI-docker` repo under `/openapi-webproj.yaml`
8. Update the version history in the same repo - under webproj.txt
9. Ask your friendly neighborhood admin to deploy to production.
