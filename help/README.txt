MyData will download its help content from a remote server, e.g.

https://raw.github.com/monash-merc/mydata/master/help/helpfiles.zip

so that the content can be updated without having to release a new version.

If MyData fails to download up-to-date help content, then it will
display content bundled with the MyData distribution which was
up-to-date at the time of that MyData release.


After updating the help content, rebuild the zip archive with:

rm helpfiles.zip
zip -r helpfiles.zip helpfiles/

and then commit the changes and push them to GitHub:
git commit helpfiles.zip helpfiles/*
git push
