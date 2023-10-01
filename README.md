# Hay-How-Are-You
## A journaling and self analysis program

I wanted a program I could use from a Dropbox of Drive that I could do journalling in securely, still be able to customize, and relatively easily access the date for data science analysis.  Please take a moment to marvel at how beautiful my front end coding is /s

But most importantly, I wanted it to be fast to fill out
* The application lets you set any variable to have a default value to load, load the previously submitted value, or have no default.  If you already have data for that day, it will load that data
* You won't need to take you hands off the keyboard, type in your selection or choose it with your arrow keys then tab to the next value.

It currently uses Fernet encryption for stored values, but I may change that later, I haven't done too much research on Python encryption but it seems suggested..


# Basic Use
When first run, it will create a key file to encrypt and decrypt your data in your Documents folder (at some point I'll add the ability to specify location)

From there you need to create the fields you want in your form by clicking on "Edit Fields" in the upper right.  At first this will be empty, but when you click on add, you can add an entry like these examples:

![Add](https://github.com/123srb/Hay-How-Are-You/assets/17171696/cc14344e-ff03-4a1f-8fbe-0b4857a785a4)

![Add 2](https://github.com/123srb/Hay-How-Are-You/assets/17171696/bef27e07-ab9a-47f0-a79a-330c59d12094)

You also have the option to Edit fields.  I don't recomended using this too much.  Changing a field name or variable type will not change the data that is saved in your journal entries.  You can delete a field from here

![Edit](https://github.com/123srb/Hay-How-Are-You/assets/17171696/ae756faf-8164-44d3-9159-8cdac3ab481d)

After saving all your entries, you have a few options.  You can order where those fields show up in your form, and choose which fields show up.  You'll notice I gave some variable very large numbers that way they will always show up at the bottom even if I add more later.

![Journal Entries](https://github.com/123srb/Hay-How-Are-You/assets/17171696/50032a39-3df2-4656-9e30-b9d15d3beee6)

If you put two or three checkboxes next to each other, they we fall into the same row to save space.

With all that we can now utilize our journal by filling it out and clicking submit.  If you want to edit an entry or enter for a missed day, change the Selected Date.  If you are editing an entry, only the entries that existed on that day will be there.
![image](https://github.com/123srb/Hay-How-Are-You/assets/17171696/15043ce9-9ae5-4465-82b9-f0ed01e3e05a)
The number to the right of each entry is a two week trend to see if numeric values are increasing or decreasing on average (Just using the slope of a linear regression)
To the right of your values is a graph that you can switch between your values to visualize your trends over time.

# Next Steps
This is V1, you can journal to your hearts content, and there are some very basic analysis function.  I'm going to add more predictive abilities in the future.
