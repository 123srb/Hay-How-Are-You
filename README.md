# Hay-How-Are-You
## A journaling and self analysis program

I wanted a program I could use from a Dropbox of Drive that I could do journalling in securely, still be able to customize, and relatively easily access the date for data science analysis.  

But most importantly, I wanted it to be fast to fill out
* The application lets you set any variable to have a default value to load, load the previously submitted value, or have no default.  If you already have data for that day, it will load that data
* You won't need to take you hands off the keyboard, type in your selection or choose it with your arrow keys then tab to the next value.

It currently uses Fernet encryption for stored values, but I may change that later, I haven't done too much research on Python encryption but it seems suggested..


# Basic Use
When first run, it will create a key file to encrypt and decrypt your data in your Documents folder (at some point I'll add the ability to specify location)

From there you need to create the fields you want in your form.

You can order those fields,and choose which fields show up on the form.
If you put two or three checkboxes next to each other, they we fall into the same row to save space.


# Next Steps
This is V1, you can journal to your hearts content, and there are some very basic analysis function.  I'm going to add more predictive abilities in the future.
